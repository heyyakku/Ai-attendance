import cv2
import os
from mtcnn import MTCNN

name = input("Enter person name: ")

folder = f"data/{name}"
os.makedirs(folder, exist_ok=True)

cap = cv2.VideoCapture(0)
detector = MTCNN()

count = 0
print("📸 Capturing images... Press Q to stop")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    faces = detector.detect_faces(rgb)

    for face in faces:
        x, y, w, h = face["box"]
        crop = frame[y:y+h, x:x+w]

        if crop.size > 0:
            count += 1
            cv2.imwrite(f"{folder}/{count}.jpg", crop)
            cv2.rectangle(frame, (x,y), (x+w, y+h), (0,255,0), 2)

    cv2.putText(frame, f"Images: {count}", (10,30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

    cv2.imshow("Capture", frame)

    if cv2.waitKey(1) & 0xFF == ord('q') or count >= 80:
        break

cap.release()
cv2.destroyAllWindows()
print(f"✔ Saved {count} images inside {folder}")
