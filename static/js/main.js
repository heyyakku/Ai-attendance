/* ================================
   AI Attendance Premium JS
   Handles:
   ✔ Sidebar Toggle
   ✔ Notification Checker
   ✔ Camera Start/Stop
   ✔ Smooth UI Animations
   ================================ */

document.addEventListener("DOMContentLoaded", () => {

    /* -------------------------
       SIDEBAR TOGGLE
    ---------------------------- */
    const sidebar = document.querySelector(".sidebar");
    const toggleBtn = document.querySelector(".menu-toggle");

    if (toggleBtn) {
        toggleBtn.addEventListener("click", () => {
            sidebar.classList.toggle("active");

            // Adjust body class for content shifting
            if (sidebar.classList.contains("active")) {
                document.body.classList.add("sidebar-collapsed");
            } else {
                document.body.classList.remove("sidebar-collapsed");
            }
        });
    }

    /* -------------------------
       CAMERA CONTROL (Mark Attendance)
    ---------------------------- */
    const startBtn = document.getElementById("btnStart");
    const stopBtn = document.getElementById("btnStop");
    const liveStream = document.getElementById("liveStream");

    if (startBtn) {
        startBtn.addEventListener("click", async () => {
            try {
                await fetch("/start_camera", { method: "POST" });
                liveStream.src = "/video_feed?ts=" + Date.now(); // fresh stream
            } catch (e) {
                alert("Camera failed to start: " + e);
            }
        });
    }

    if (stopBtn) {
        stopBtn.addEventListener("click", async () => {
            try {
                await fetch("/stop_camera", { method: "POST" });
                liveStream.src = "";
                liveStream.alt = "Camera stopped";
            } catch (e) {
                alert("Camera stop failed: " + e);
            }
        });
    }

    /* -------------------------
       NOTIFICATION SYSTEM
       Checks every 6 sec
    ---------------------------- */
    const notifDot = document.getElementById("notifDot");

    async function checkNotifications() {
        try {
            const res = await fetch("/check-notifications");
            const data = await res.json();

            // red dot on sidebar
            if (notifDot) {
                notifDot.style.display = data.red_dot ? "inline-block" : "none";
            }

            // popup alert
            if (data.popup) {
                showPopup(data.message);
            }

        } catch (err) {
            console.log("Notification check failed:", err);
        }
    }

    setInterval(checkNotifications, 6000);

    /* -------------------------
       POPUP UI
    ---------------------------- */
    function showPopup(msg) {
        const box = document.createElement("div");
        box.className = "popup-msg";
        box.innerHTML = msg;

        document.body.appendChild(box);

        setTimeout(() => {
            box.style.opacity = "0";
            setTimeout(() => box.remove(), 600);
        }, 2800);
    }

    /* -------------------------
       Popup message style
    ---------------------------- */
    const popupStyle = document.createElement("style");
    popupStyle.textContent = `
        .popup-msg {
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(90deg, rgba(62,140,255,0.2), rgba(62,140,255,0.05));
            padding: 14px 22px;
            color: #fff;
            border-radius: 10px;
            font-size: 14px;
            border: 1px solid rgba(62,140,255,0.3);
            box-shadow: 0 10px 30px rgba(0,0,0,0.4);
            backdrop-filter: blur(8px);
            transition: opacity .5s ease;
            z-index: 99999;
        }
    `;
    document.head.appendChild(popupStyle);

});
