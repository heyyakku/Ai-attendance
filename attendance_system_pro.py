import cv2
from mtcnn import MTCNN
from keras_facenet import FaceNet
import numpy as np
import pandas as pd
from datetime import datetime
import os
import firebase_admin
from firebase_admin import credentials, firestore

attendance_file = "attendance.csv"

# Firebase Init
USE_FIREBASE = False
db = None
try:
    if os.path.exists("firebase_key.json"):
        cred = credentials.Certificate("firebase_key.json")
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        USE_FIREBASE = True
        print("🔥 Firebase Connected!")
except Exception as e:
    print(f"⚠ Firebase Init Failed: {e}")

# Load single-person embedding
known_embedding = np.load("model/face_embedding.npy")

detector = MTCNN()
embedder = FaceNet()

if not os.path.exists(attendance_file):
    pd.DataFrame(columns=["Name","Date","Time"]).to_csv(attendance_file, index=False)

cap = cv2.VideoCapture(0)

print("▶ Starting Attendance — Press Q to exit")

while True:
    ret, frame = cap.read()
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    faces = detector.detect_faces(rgb)

    for face in faces:
        x, y, w, h = face["box"]
        crop = frame[y:y+h, x:x+w]

        if crop.size == 0:
            continue
        
        crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        crop_resized = cv2.resize(crop_rgb, (160,160))
        crop_emb = embedder.embeddings([crop_resized])[0]

        # Cosine similarity
        similarity = np.dot(known_embedding, crop_emb) / (
            np.linalg.norm(known_embedding) * np.linalg.norm(crop_emb)
        )

        if similarity > 0.70:
            name = "Aman"
        else:
            name = "Unknown"

        cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),2)
        cv2.putText(frame,name,(x,y-5),cv2.FONT_HERSHEY_SIMPLEX,1,(0,255,0),2)

        if name == "Aman":
            date = datetime.now().strftime("%d-%m-%Y")
            time = datetime.now().strftime("%I:%M:%S %p")

            # Local CSV Sync
            df = pd.read_csv(attendance_file)
            if not ((df["Name"]=="Aman") & (df["Date"]==date)).any():
                df.loc[len(df)] = ["Aman", date, time]
                df.to_csv(attendance_file, index=False)
                print(f"✔ Local Attendance Marked for {name}!")

                # Firebase Cloud Sync
                if USE_FIREBASE:
                    try:
                        db.collection("attendance").add({
                            "name": name,
                            "date": date,
                            "time": time,
                            "timestamp": firestore.SERVER_TIMESTAMP
                        })
                        print(f"☁ Firebase Cloud Sync Complete for {name}!")
                    except Exception as e:
                        print(f"❌ Firebase Sync Error: {e}")
    
    cv2.imshow("Attendance System", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
