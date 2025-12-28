import os
import numpy as np
from keras_facenet import FaceNet
from mtcnn.mtcnn import MTCNN
from PIL import Image

# Initialize models
embedder = FaceNet()
detector = MTCNN()

faces_dir = "faces_new"
embeddings = []
valid_ext = (".jpg", ".jpeg", ".png")

print("📂 Starting face extraction & embedding...")
print("🗂 Folder:", os.path.abspath(faces_dir))

if not os.path.exists(faces_dir):
    print("❌ faces_new folder not found!")
    exit()

for root, _, files in os.walk(faces_dir):
    for img_name in files:

        if not img_name.lower().endswith(valid_ext):
            continue

        img_path = os.path.join(root, img_name)
        print(f"\n🔍 Processing: {img_name}")

        try:
            img = Image.open(img_path).convert("RGB")
            img_np = np.asarray(img)

            # Detect face
            faces = detector.detect_faces(img_np)

            if len(faces) == 0:
                print("❌ No face detected...")
                continue

            # Get bounding box of first face
            x, y, w, h = faces[0]['box']
            face = img_np[y:y+h, x:x+w]

            # Resize for FaceNet
            face_img = Image.fromarray(face).resize((160, 160))
            face_array = np.asarray(face_img)

            # Generate embedding
            emb = embedder.embeddings([face_array])[0]
            embeddings.append(emb)

            print("✔ Face detected & embedded successfully")

        except Exception as e:
            print(f"⚠️ Error: {e}")

# Convert embeddings to numpy array
embeddings = np.array(embeddings)

if len(embeddings) == 0:
    print("\n❌ ERROR: No valid faces embedded!")
    print("➡ Try capturing images again with good light & face centered")
    exit()

# Compute average embedding for final model
mean_embedding = np.mean(embeddings, axis=0)

# Save model file
os.makedirs("model", exist_ok=True)
np.save("model/face_embedding.npy", mean_embedding)

print("\n🎯 TRAINING COMPLETE!")
print("✔ Saved: model/face_embedding.npy")
print("👤 Mode: Single person recognition enabled")
