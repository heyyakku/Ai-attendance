import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'   # Disable TF logs (0,1,2,3)
import logging
logging.getLogger('tensorflow').setLevel(logging.ERROR)  # Disable TF warnings

import cv2
import numpy as np
from keras_facenet import FaceNet
from mtcnn.mtcnn import MTCNN
from PIL import Image

# Load trained embedding
known_embedding = np.load("model/face_embedding.npy")

# Load models silently
embedder = FaceNet()
detector = MTCNN()

# Similarity threshold
THRESHOLD = 0.75  

# Start webcam
cap = cv2.VideoCapture(0)
print("\n🎥 Recognition started (Press Q to exit)")

while True:
    ret, frame = cap.read()
    if not ret:
        print("❌ Frame capture failed!")
        break

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    faces = detector.detect_faces(rgb)

    for face in faces:
        x, y, w, h = face['box']

        face_img = rgb[y:y+h, x:x+w]
        face_img = Image.fromarray(face_img).resize((160, 160))
        face_arr = np.asarray(face_img)

        embedding = embedder.embeddings([face_arr])[0]

        # Cosine similarity
        similarity = np.dot(known_embedding, embedding) / (
            np.linalg.norm(known_embedding) * np.linalg.norm(embedding)
        )

        if similarity > THRESHOLD:
            label = f"Access Granted ({similarity:.2f})"
            color = (0, 255, 0)
        else:
            label = f"Unknown ({similarity:.2f})"
            color = (0, 0, 255)

        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        cv2.putText(frame, label, (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    cv2.imshow("Face Recognition", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
