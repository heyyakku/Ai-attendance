import tkinter as tk
from tkinter import messagebox
import subprocess
import sys
import os
import threading
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------- Helper: Run script in background thread ----------

def run_script(script_name, status_label, btn_capture, btn_train):
    script_path = os.path.join(BASE_DIR, script_name)
    if not os.path.exists(script_path):
        messagebox.showerror("Error", f"{script_name} not found in:\n{BASE_DIR}")
        return

    def worker():
        try:
            btn_capture.config(state="disabled")
            btn_train.config(state="disabled")
            status_label.config(text=f"🚀 Running {script_name} ...", fg="#00ffc6")

            subprocess.run([sys.executable, script_path], check=True)

            if script_name == "capture_faces.py":
                status_label.config(text="📸 Face capture completed! Now train the model.", fg="#00ffc6")
            else:
                status_label.config(text="🤖 Model trained successfully! Ready to run attendance.", fg="#00ff88")

        except subprocess.CalledProcessError as e:
            status_label.config(text="❌ Script crashed — check terminal!", fg="#ff4d6d")
            messagebox.showerror("Script Error", str(e))
        finally:
            btn_capture.config(state="normal")
            btn_train.config(state="normal")

    threading.Thread(target=worker, daemon=True).start()

# ---------- GUI ----------

root = tk.Tk()
root.title("AI Attendance – Training Control Panel")

# Window size + center
root.geometry("520x360")
root.configure(bg="#050816")
root.resizable(False, False)

root.update_idletasks()
x = (root.winfo_screenwidth() // 2) - (520 // 2)
y = (root.winfo_screenheight() // 2) - (360 // 2)
root.geometry(f"520x360+{x}+{y}")

# ---------- Main Glass Panel ----------

glass = tk.Frame(root, bg="#0b1020", bd=0, highlightthickness=1, highlightbackground="#1e293b")
glass.place(relx=0.5, rely=0.5, anchor="center", width=480, height=320)

# Neon Border (fixed)
shadow = tk.Canvas(root, bg="#050816", bd=0, highlightthickness=0)
shadow.place(relx=0.5, rely=0.5, anchor="center", width=488, height=328)
shadow.create_rectangle(5, 5, 483, 323, outline="#00ffc6", width=2)

# ---------- Header ----------

title_label = tk.Label(glass, text="🤖 AI Face Attendance Trainer", bg="#0b1020", fg="#00ffc6",
                       font=("Poppins", 16, "bold"))
title_label.pack(pady=(18, 4))

subtitle_label = tk.Label(glass, text="Capture • Train • Deploy", bg="#0b1020", fg="#9db7ff",
                          font=("Poppins", 10))
subtitle_label.pack(pady=(0, 12))

# ---------- Typing Assistant ----------

assistant_label = tk.Label(glass, text="", bg="#0b1020", fg="#ffdd57", font=("Consolas", 10))
assistant_label.pack(pady=(0, 10))

assistant_messages = [
    "Hi, I'm your AI training assistant ⚡",
    "Step 1: Capture faces → Click Capture",
    "Step 2: Train / Re-Train the model",
    "Step 3: Run attendance_system_pro.py 🎯"
]
assistant_index = 0
char_index = 0

def animate_assistant():
    global assistant_index, char_index
    msg = assistant_messages[assistant_index]
    if char_index <= len(msg):
        assistant_label.config(text=msg[:char_index])
        char_index += 1
    else:
        time.sleep(1)
        assistant_index = (assistant_index + 1) % len(assistant_messages)
        char_index = 0
    root.after(80, animate_assistant)

# ---------- Buttons ----------

btn_style = {"font": ("Poppins", 11, "bold"), "bd": 0, "relief": "flat", "width": 22, "height": 2, "cursor": "hand2"}

btn_capture = tk.Button(glass, text="📸 Capture New Faces", bg="#111827", fg="#00ffc6",
                        activebackground="#00ffc6", activeforeground="#020617", **btn_style,
                        command=lambda: run_script("capture_faces.py", status_label, btn_capture, btn_train))
btn_capture.pack(pady=(4, 10))

btn_train = tk.Button(glass, text="🧠 Train / Re-Train Model", bg="#111827", fg="#38bdf8",
                      activebackground="#38bdf8", activeforeground="#020617", **btn_style,
                      command=lambda: run_script("train_model.py", status_label, btn_capture, btn_train))
btn_train.pack(pady=(0, 8))

# ---------- Status ----------

status_label = tk.Label(glass, text="Ready — Capture faces, then Train the model.",
                        bg="#0b1020", fg="#9ca3af", font=("Poppins", 9))
status_label.pack(side="bottom", pady=12)

# ---------- Footer ----------

footer = tk.Label(root, text="AI Attendance • Trainer Panel • by A.K.T",
                  bg="#050816", fg="#4b5563", font=("Poppins", 8))
footer.pack(side="bottom", pady=4)

animate_assistant()
root.mainloop()
