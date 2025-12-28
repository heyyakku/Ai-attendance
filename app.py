#!/usr/bin/env python3
"""
Clean, single-file backend for AI Attendance.
Features included:
- Web login (/login) and mobile API login (/api/login)
- Admin (plain) + Employee (CSV hashed passwords)
- Optional Firebase (defensive)
- Camera start/stop + video stream
- Assign tasks (Firestore if available else local CSV)
- Task history, notifications
- Attendance CSV + Export to Excel
- Add user (admin) with password hashing
"""
import os
import io
import hashlib
import socket
import logging
from datetime import datetime, timedelta
from functools import wraps

import pandas as pd
import cv2
from flask import (
    Flask, request, jsonify, render_template, redirect, url_for, session,
    flash, Response, send_file
)

# -------------------
# App init
# -------------------
app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "AmanUltraSecretKey")
app.permanent_session_lifetime = timedelta(minutes=25)

# -------------------
# Config / Files
# -------------------
ATTENDANCE_FILE = "attendance.csv"
USERS_FILE = "users.csv"
TASKS_LOCAL = "tasks_local.csv"

ADMIN_USER = "admin"
ADMIN_PASS = "1234"

camera = None
USE_FIREBASE = False
db = None
FIREBASE_ERROR = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai-attendance")

# -------------------
# Optional Firebase init (defensive)
# -------------------
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    possible_keys = ["firebase_key.json", "firebase_key.json", "firebase_key.json"]
    found_key = next((k for k in possible_keys if os.path.exists(k)), None)
    if found_key:
        cred = credentials.Certificate(found_key)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        USE_FIREBASE = True
        FIREBASE_ERROR = None
    else:
        FIREBASE_ERROR = "No firebase_key.json found"
        USE_FIREBASE = False
except Exception as e:
    FIREBASE_ERROR = str(e)
    USE_FIREBASE = False
    db = None

# -------------------
# Utilities
# -------------------
def get_ip():
    try:
        return socket.gethostbyname(socket.gethostname())
    except:
        return "Unknown"

def hash_password(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()

def ensure_files():
    if not os.path.exists(ATTENDANCE_FILE):
        pd.DataFrame(columns=["Name", "Date", "Time"]).to_csv(ATTENDANCE_FILE, index=False)
    if not os.path.exists(USERS_FILE):
        pd.DataFrame(columns=["Username", "FullName", "Password", "Created"]).to_csv(USERS_FILE, index=False)
    if not os.path.exists(TASKS_LOCAL):
        pd.DataFrame(columns=["user", "task", "status", "date", "time", "created"]).to_csv(TASKS_LOCAL, index=False)

ensure_files()

def safe_read_users():
    try:
        if not os.path.exists(USERS_FILE):
             return pd.DataFrame(columns=["Username", "FullName", "Password", "Created"])
        df = pd.read_csv(USERS_FILE)
        # Drop empty or corrupted rows
        df = df.dropna(subset=["Username"])
        # Ensure we only have the latest record for each user if duplicates exist
        df = df.drop_duplicates(subset=["Username"], keep="last")
        
        expected = ["Username", "FullName", "Password", "Created"]
        for c in expected:
            if c not in df.columns:
                df[c] = ""
        return df[expected]
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=["Username","FullName","Password","Created"])
    except Exception:
        logger.exception("Failed reading users file")
        return pd.DataFrame(columns=["Username","FullName","Password","Created"])

def add_attendance(name: str):
    try:
        df = pd.read_csv(ATTENDANCE_FILE)
    except Exception:
        df = pd.DataFrame(columns=["Name","Date","Time"])
    df.loc[len(df)] = [
        name,
        datetime.now().strftime("%d-%m-%Y"),
        datetime.now().strftime("%I:%M %p")
    ]
    df.to_csv(ATTENDANCE_FILE, index=False)

def load_attendance(filters=None):
    all_records = []
    
    # 1. Load from Local CSV
    try:
        if os.path.exists(ATTENDANCE_FILE):
            df_local = pd.read_csv(ATTENDANCE_FILE)
            all_records = df_local.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Local attendance read failed: {e}")

    # 2. Add from Firebase if available
    if USE_FIREBASE:
        try:
            # We fetch recent 50 records from Firestore to avoid heavy load
            docs = db.collection("attendance").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(50).stream()
            for doc in docs:
                data = doc.to_dict()
                # Mapping Firebase fields to expected keys
                rec = {
                    "Name": data.get("name"),
                    "Date": data.get("date"),
                    "Time": data.get("time")
                }
                # Avoid simple duplicates if local already has it (naive check)
                if not any(r['Name'] == rec['Name'] and r['Date'] == rec['Date'] and r['Time'] == rec['Time'] for r in all_records):
                    all_records.append(rec)
        except Exception as e:
            logger.error(f"Firebase attendance read failed: {e}")

    df = pd.DataFrame(all_records)
    if df.empty:
        return pd.DataFrame(columns=["Name","Date","Time"])

    if "Date" in df.columns:
        df["DateObj"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)
    else:
        df["DateObj"] = pd.NaT

    if filters:
        name = filters.get("name","").strip()
        d_from = filters.get("date_from","").strip()
        d_to = filters.get("date_to","").strip()
        if name and "Name" in df.columns:
            df = df[df["Name"].str.contains(name, case=False, na=False)]
        if d_from:
            try:
                df = df[df["DateObj"] >= pd.to_datetime(d_from)]
            except:
                pass
        if d_to:
            try:
                df = df[df["DateObj"] <= pd.to_datetime(d_to)]
            except:
                pass

    if "DateObj" in df.columns and "Time" in df.columns:
        df = df.sort_values(by=["DateObj","Time"], ascending=[False, False])
        return df.drop(columns=["DateObj"])
    return df

# -------------------
# Decorators
# -------------------
from flask import redirect as _redirect, url_for as _url_for
def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **k):
        if not session.get("logged_in"):
            return _redirect(_url_for("login"))
        return fn(*a, **k)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*a, **k):
        if session.get("role") != "admin":
            if session.get("logged_in") and session.get("role") == "employee":
                return _redirect(_url_for("employee_dashboard"))
            return _redirect(_url_for("login"))
        return fn(*a, **k)
    return wrapper

@app.route("/debug-files")
def debug_files():
    files = []
    for root, dirs, filenames in os.walk("."):
        for f in filenames:
            files.append(os.path.join(root, f))
    return jsonify({"current_dir": os.getcwd(), "files": files})

# -------------------
# Camera helpers
# -------------------
def get_camera():
    global camera
    if camera is None:
        camera = cv2.VideoCapture(0)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return camera

def release_camera():
    global camera
    try:
        if camera:
            camera.release()
    except Exception:
        pass
    camera = None

def gen_frames():
    cam = get_camera()
    while True:
        ok, frame = cam.read()
        if not ok:
            logger.debug("Camera read failed")
            break
        frame = cv2.resize(frame, (640,360))
        _, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

# -------------------
# Routes: Login / API
# -------------------
@app.before_request
def refresh_session():
    session.permanent = True

@app.route("/login", methods=["GET","POST"])
def login():
    try:
        if request.method == "POST":
            u = request.form.get("username","").strip()
            p = request.form.get("password","").strip()
            
            # 1. Admin Check
            if u == ADMIN_USER and p == ADMIN_PASS:
                session["logged_in"] = True
                session["username"] = u
                session["role"] = "admin"
                flash("Logged in as admin","success")
                return redirect(url_for("main_dashboard"))
            
            # 2. Local CSV Check
            users = safe_read_users()
            if not users.empty and u in users["Username"].values:
                row = users[users["Username"] == u].iloc[0]
                stored = str(row.get("Password",""))
                if stored and hash_password(p) == stored:
                    session["logged_in"] = True
                    session["username"] = u
                    session["role"] = "employee"
                    flash("Logged in as employee","success")
                    return redirect(url_for("employee_dashboard"))
            
            # 3. Cloud (Firestore) Check - For Cloud Persistance
            if USE_FIREBASE:
                try:
                    user_doc = db.collection("users").document(u).get()
                    if user_doc.exists:
                        data = user_doc.to_dict()
                        if data.get("password") == hash_password(p):
                            session["logged_in"] = True
                            session["username"] = u
                            session["role"] = data.get("role", "employee")
                            flash(f"Logged in as {session['role']} (Cloud)","success")
                            return redirect(url_for("main_dashboard" if session["role"]=="admin" else "employee_dashboard"))
                except Exception as e:
                    logger.error(f"Cloud login check failed: {e}")

            flash("Invalid username or password","error")
        return render_template("login.html", firebase_ok=USE_FIREBASE, firebase_error=FIREBASE_ERROR)
    except Exception:
        logger.exception("Error in login route")
        flash("Internal server error during login","error")
        return render_template("login.html", firebase_ok=USE_FIREBASE, firebase_error=FIREBASE_ERROR)

@app.route("/api/login", methods=["POST"])
def api_login():
    try:
        # support both form and json
        username = request.form.get("username") or (request.json or {}).get("username")
        password = request.form.get("password") or (request.json or {}).get("password")
        username = (username or "").strip()
        password = (password or "").strip()
        if username == ADMIN_USER and password == ADMIN_PASS:
            return jsonify({"success": True, "role": "admin"})
        users = safe_read_users()
        if not users.empty and username in users["Username"].values:
            row = users[users["Username"] == username].iloc[0]
            stored_hash = str(row.get("Password",""))
            if stored_hash and hash_password(password) == stored_hash:
                return jsonify({"success": True, "role": "employee"})
        return jsonify({"success": False, "message": "Invalid username or password"})
    except Exception as e:
        logger.exception("API login error")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"})

# -------------------
# Logout
# -------------------
@app.route("/logout")
def logout():
    release_camera()
    session.clear()
    flash("Logged out","info")
    return redirect(url_for("login"))

# -------------------
# Dashboards
# -------------------
@app.route("/")
@admin_required
def main_dashboard():
    df = load_attendance()
    present = "Present" if len(df) > 0 else "Absent"
    records = df.to_dict(orient="records")
    return render_template("main_dashboard.html",
                           today=datetime.now().strftime("%d %B %Y"),
                           status=present,
                           count=len(df),
                           user=session.get("username"),
                           today_date=datetime.now().strftime("%d-%m-%Y"),
                           current_time=datetime.now().strftime("%I:%M %p"),
                           attendance_logs=records[:10]) # Show last 10 logs

@app.route("/employee-dashboard")
def employee_dashboard():
    if session.get("role") != "employee":
        return redirect(url_for("login"))
    latest = None
    if USE_FIREBASE:
        try:
            docs = db.collection("tasks").where("user","==",session["username"]).order_by("created", direction=None).limit(1).stream()
            for d in docs:
                latest = d.to_dict()
        except Exception:
            logger.debug("Firestore tasks not available")
    return render_template("employee_dashboard.html", user=session.get("username"), task=latest, tasks=[])

# -------------------
# Tasks
# -------------------
@app.route("/assign-task", methods=["GET","POST"])
@admin_required
def assign_task():
    users = safe_read_users()["Username"].tolist()
    if request.method == "POST":
        user = request.form.get("user")
        task = request.form.get("task")
        status = request.form.get("status","Pending")
        task_data = {
            "user": user,
            "task": task,
            "status": status,
            "date": datetime.now().strftime("%d-%m-%Y"),
            "time": datetime.now().strftime("%I:%M %p"),
            "created": datetime.now(),
            "admin_seen": True,
            "employee_seen": False
        }
        if USE_FIREBASE:
            try:
                ref = db.collection("tasks").document()
                task_data["id"] = ref.id
                ref.set(task_data)
                flash("Task assigned and saved to Firestore","success")
            except Exception:
                logger.exception("Failed saving task to Firestore")
                flash("Task assigned but Firestore save failed","warning")
        else:
            try:
                df = pd.read_csv(TASKS_LOCAL)
                df.loc[len(df)] = [user, task, status, task_data["date"], task_data["time"], datetime.now().isoformat()]
                df.to_csv(TASKS_LOCAL, index=False)
                flash("Task assigned (local)","success")
            except Exception:
                logger.exception("Failed writing local task file")
                flash("Task assigned but local save failed","warning")
        return redirect(url_for("assign_task"))
    return render_template("assign_task.html", users=users)

@app.route("/update-task", methods=["POST"])
def update_task():
    if session.get("role") != "employee":
        return redirect(url_for("login"))
    new_status = request.form.get("status")
    user = session.get("username")
    updated = False
    if USE_FIREBASE:
        try:
            docs = db.collection("tasks").where("user","==",user).order_by("created", direction=None).limit(1).stream()
            for d in docs:
                db.collection("tasks").document(d.id).update({"status": new_status, "admin_seen": False})
                updated = True
        except Exception:
            logger.exception("Failed updating task in Firestore")
    if not USE_FIREBASE or not updated:
        try:
            if os.path.exists(TASKS_LOCAL):
                df = pd.read_csv(TASKS_LOCAL)
                idx = df[df["user"] == user].index
                if len(idx) > 0:
                    i = idx[-1]
                    df.at[i, "status"] = new_status
                    df.to_csv(TASKS_LOCAL, index=False)
                    updated = True
        except Exception:
            logger.exception("Failed updating local tasks file")
    flash("Task updated" if updated else "No task found to update", "success" if updated else "error")
    return redirect(url_for("employee_dashboard"))

@app.route("/task-history")
@login_required
def task_history():
    role = session.get("role")
    user = session.get("username")
    tasks_out = []
    if USE_FIREBASE:
        try:
            if role == "admin":
                docs = db.collection("tasks").order_by("created", direction=None).stream()
            else:
                docs = db.collection("tasks").where("user","==",user).order_by("created", direction=None).stream()
            for d in docs:
                data = d.to_dict()
                tasks_out.append({"User": data.get("user",""), "Task": data.get("task",""), "Status": data.get("status",""), "Date": data.get("date",""), "Time": data.get("time","")})
        except Exception:
            logger.exception("Failed reading tasks from Firestore")
            flash("Could not fetch tasks from Firestore","warning")
    else:
        try:
            if os.path.exists(TASKS_LOCAL):
                df = pd.read_csv(TASKS_LOCAL).sort_values(by="created", ascending=False)
                for _, r in df.iterrows():
                    if role == "admin" or r.get("user") == user:
                        tasks_out.append({"User": r.get("user",""), "Task": r.get("task",""), "Status": r.get("status",""), "Date": r.get("date",""), "Time": r.get("time","")})
        except Exception:
            logger.exception("Failed reading local tasks")
    return render_template("task_history.html", tasks=tasks_out)

# -------------------
# Attendance mark + export
# -------------------
@app.route("/mark-attendance", methods=["GET","POST"])
def mark_attendance():
    if session.get("role") != "employee":
        return redirect(url_for("login"))
    if request.method == "POST":
        add_attendance(session.get("username"))
        flash("Attendance Marked Successfully!","success")
        return redirect(url_for("employee_dashboard"))
    return render_template("mark_attendance.html")

@app.route("/export/excel")
@admin_required
def export_excel():
    df = load_attendance()
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(output, as_attachment=True,
                     download_name=f"attendance_{datetime.now().strftime('%Y%m%d')}.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# -------------------
# Add user
# -------------------
@app.route("/add-user", methods=["GET","POST"])
@admin_required
def add_user():
    if request.method == "POST":
        uname = request.form.get("username","").strip()
        fname = request.form.get("fullname","").strip()
        pwd = request.form.get("password","").strip()
        role = request.form.get("role", "employee") # Added role support

        if not uname or not pwd:
            flash("Username and password required","error")
            return redirect(url_for("add_user"))
        
        # Check Local
        df = safe_read_users()
        if uname in df["Username"].values:
            flash("User already exists (Local)","error")
            return redirect(url_for("add_user"))
        
        hashed = hash_password(pwd)
        
        # 1. Save Local CSV
        df.loc[len(df)] = [uname, fname, hashed, datetime.now().strftime("%d-%m-%Y")]
        try:
            df.to_csv(USERS_FILE, index=False)
            
            # 2. Save to Firebase (Cloud Persistence)
            if USE_FIREBASE:
                try:
                    # Sync to 'users' collection for authentication
                    db.collection("users").document(uname).set({
                        "fullname": fname,
                        "password": hashed,
                        "role": role,
                        "created": datetime.now()
                    })
                    # Keep existing 'employees' collection compatibility if needed
                    db.collection("employees").document(uname).set({"fullname": fname, "created": datetime.now()})
                    flash("User synced to Cloud and Local","success")
                except Exception as e:
                    logger.error(f"Firestore sync failed: {e}")
                    flash("User added locally but Cloud sync failed","warning")
            else:
                flash("User added successfully (Local only)","success")
                
        except Exception:
            logger.exception("Failed to save user")
            flash("Failed to add user (server)","error")
        return redirect(url_for("add_user"))
    return render_template("add_user.html")

# -------------------
# Camera endpoints
# -------------------
@app.route("/start_camera", methods=["POST"])
@login_required
def start_camera():
    try:
        get_camera()
        return "OK", 200
    except Exception:
        logger.exception("Failed to start camera")
        return "ERROR", 500

@app.route("/stop_camera", methods=["POST"])
@login_required
def stop_camera():
    try:
        release_camera()
        return "OK", 200
    except Exception:
        logger.exception("Failed to stop camera")
        return "ERROR", 500

@app.route("/video_feed")
@login_required
def video_feed():
    return Response(gen_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

# -------------------
# Notifications & report
# -------------------
@app.route("/check-notifications")
@login_required
def check_notifications():
    try:
        role = session.get("role")
        user = session.get("username")
        result = {"popup": False, "message": "", "red_dot": False}
        if USE_FIREBASE:
            try:
                if role == "admin":
                    unread = list(db.collection("tasks").where("admin_seen","==",False).limit(5).stream())
                    if len(unread) > 0:
                        result.update({"popup": True, "message": "Employee updated a task", "red_dot": True})
                elif role == "employee":
                    unread = list(db.collection("tasks").where("user","==",user).where("employee_seen","==",False).limit(5).stream())
                    if len(unread) > 0:
                        for t in unread:
                            try:
                                db.collection("tasks").document(t.id).update({"employee_seen": True})
                            except Exception:
                                pass
                        result.update({"popup": True, "message": "New Task Assigned!", "red_dot": True})
            except Exception:
                logger.debug("Error while checking tasks in Firestore")
        else:
            try:
                if os.path.exists(TASKS_LOCAL):
                    df = pd.read_csv(TASKS_LOCAL).sort_values(by="created", ascending=False)
                    if not df[df["user"] == user].empty:
                        result.update({"popup": False, "message": "", "red_dot": False})
            except Exception:
                pass
        return jsonify(result)
    except Exception:
        logger.exception("check-notifications failed")
        return jsonify({"popup": False, "message": "", "red_dot": False})

@app.route("/report")
@admin_required
def report():
    filters = {"name": request.args.get("name",""), "date_from": request.args.get("date_from",""), "date_to": request.args.get("date_to","")}
    df = load_attendance(filters)
    return render_template("report.html", data=df.to_dict(orient="records"), total=len(df))

# -------------------
# Error handlers
# -------------------
@app.errorhandler(500)
def internal_error(e):
    logger.exception("Internal Server Error")
    return render_template("500.html", error=str(e)), 500

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

# -------------------
# Run
# -------------------
if __name__ == "__main__":
    # For local development
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
else:
    # For production (gunicorn)
    # The 'app' object is already defined globally as 'app'
    pass
