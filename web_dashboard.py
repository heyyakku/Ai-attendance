# web_dashboard.py
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, send_file, flash, Response, jsonify
)
import pandas as pd
from datetime import datetime
import logging
import io
import os
import cv2
from functools import wraps
import threading
import time

app = Flask(__name__, static_folder="static", template_folder="templates")

# -----------------------
# BASIC CONFIG
# -----------------------
app.secret_key = "Aman_SuperStrongSecretKey_ChangeThis"
ATTENDANCE_FILE = "attendance.csv"
ADMIN_USER = "admin"
ADMIN_PASS = "1234"

# Disable console logs
log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

# Global camera instance + lock
camera = None
camera_lock = threading.Lock()
camera_active = False


# -----------------------
# CAMERA HELPERS
# -----------------------
def get_camera():
    global camera, camera_active
    with camera_lock:
        if camera is None:
            camera = cv2.VideoCapture(0)
            # set smaller resolution for streaming stability
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
        camera_active = True
    return camera


def stop_camera_instance():
    global camera, camera_active
    with camera_lock:
        if camera is not None:
            try:
                camera.release()
            except Exception:
                pass
            camera = None
        camera_active = False


@app.route("/start_camera", methods=["POST"])
def start_camera():
    """Start the camera (called from JS)."""
    get_camera()
    return {"status": "started"}


@app.route("/stop_camera", methods=["POST"])
def stop_camera():
    """Stop the camera (called from JS)."""
    stop_camera_instance()
    return {"status": "stopped"}


def gen_frames():
    """Yield camera frames for MJPEG stream. Exit cleanly when camera stopped."""
    global camera, camera_active
    cam = get_camera()
    while True:
        with camera_lock:
            if not camera_active or cam is None:
                break
            ok, frame = cam.read()
        if not ok or frame is None:
            time.sleep(0.05)
            continue
        frame = cv2.resize(frame, (640, 360))
        ret, buffer = cv2.imencode(".jpg", frame)
        if not ret:
            continue
        frame_bytes = buffer.tobytes()
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")


@app.route("/video_feed")
def video_feed():
    # stream does not require login for dev; wrap if you want login-protected stream
    return Response(gen_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


# -----------------------
# FILE / DATA HELPERS
# -----------------------
def ensure_attendance_file():
    if not os.path.exists(ATTENDANCE_FILE):
        df = pd.DataFrame(columns=["Name", "Date", "Time"])
        df.to_csv(ATTENDANCE_FILE, index=False)


def load_attendance(filters=None):
    ensure_attendance_file()
    df = pd.read_csv(ATTENDANCE_FILE)
    df["Name"] = df["Name"].fillna("")
    df["DateObj"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")

    if filters:
        name = filters.get("name", "").strip()
        date_from = filters.get("date_from", "").strip()
        date_to = filters.get("date_to", "").strip()

        if name:
            df = df[df["Name"].str.contains(name, case=False, na=False)]

        if date_from:
            try:
                df = df[df["DateObj"] >= pd.to_datetime(date_from)]
            except:
                pass

        if date_to:
            try:
                df = df[df["DateObj"] <= pd.to_datetime(date_to)]
            except:
                pass

    df = df.sort_values(by=["DateObj", "Time"], ascending=[False, False])
    return df.drop(columns=["DateObj"])


# -----------------------
# AUTH HELPERS
# -----------------------
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


# -----------------------
# ROUTES: AUTH
# -----------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "").strip()
        if u == ADMIN_USER and p == ADMIN_PASS:
            session["logged_in"] = True
            session["username"] = u
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    stop_camera_instance()
    return redirect(url_for("login"))


# -----------------------
# ROUTES: DASHBOARD
# -----------------------
@app.route("/")
@login_required
def dashboard():
    filters = {
        "name": request.args.get("name", ""),
        "date_from": request.args.get("date_from", ""),
        "date_to": request.args.get("date_to", "")
    }
    df = load_attendance(filters)
    return render_template(
        "dashboard.html",
        data=df.to_dict(orient="records"),
        total_records=len(df),
        filter_name=filters["name"],
        filter_date_from=filters["date_from"],
        filter_date_to=filters["date_to"],
        now=datetime.now,
        user=session.get("username", "Admin")
    )


# -----------------------
# EXPORT: EXCEL
# -----------------------
@app.route("/export/excel")
@login_required
def export_excel():
    filters = {
        "name": request.args.get("name", ""),
        "date_from": request.args.get("date_from", ""),
        "date_to": request.args.get("date_to", "")
    }
    df = load_attendance(filters)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Attendance")
    output.seek(0)
    fname = f"attendance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(output, as_attachment=True, download_name=fname,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# -----------------------
# BULK UPLOAD
# -----------------------
@app.route("/upload", methods=["POST"])
@login_required
def upload_attendance():
    file = request.files.get("file")
    if not file or file.filename == "":
        flash("Please select a file", "error")
        return redirect(url_for("dashboard"))
    try:
        fname = file.filename.lower()
        if fname.endswith(".xlsx") or fname.endswith(".xls"):
            new_df = pd.read_excel(file)
        else:
            new_df = pd.read_csv(file)
        if not {"Name", "Date", "Time"}.issubset(set(new_df.columns)):
            flash("File must contain Name, Date, Time", "error")
            return redirect(url_for("dashboard"))
        ensure_attendance_file()
        old = pd.read_csv(ATTENDANCE_FILE)
        merged = pd.concat([old, new_df[["Name", "Date", "Time"]]], ignore_index=True)
        merged.to_csv(ATTENDANCE_FILE, index=False)
        flash(f"Uploaded {len(new_df)} records", "success")
    except Exception as e:
        flash(f"Upload error: {e}", "error")
    return redirect(url_for("dashboard"))


# -----------------------
# API: attendance JSON for charts
# -----------------------
@app.route("/api/attendance")
@login_required
def api_attendance():
    df = load_attendance()
    # return aggregated counts per date and top names
    by_date = df.groupby("Date").size().reset_index(name="count").to_dict(orient="records")
    top_names = df["Name"].value_counts().head(10).reset_index().rename(columns={"index":"Name", "Name":"count"}).to_dict(orient="records")
    return jsonify({"by_date": by_date, "top_names": top_names})


# -----------------------
# START SERVER
# -----------------------
if __name__ == "__main__":
    ensure_attendance_file()
    app.run(host="0.0.0.0", port=5000, debug=False)
