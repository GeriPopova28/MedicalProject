import os
import numpy as np
import tensorflow as tf
import cv2
from tensorflow.keras.preprocessing.image import ImageDataGenerator

# =========================
# SETTINGS
# =========================
IMG_SIZE = 224
DATASET_PATH = "dataset"
MODEL_PATH = "best_model.keras"

# =========================
# LOAD MODEL
# =========================
model = tf.keras.models.load_model(MODEL_PATH, compile=False)
print("✅ Model loaded")

# =========================
# SAME PREPROCESSING AS TRAINING
# =========================
datagen = ImageDataGenerator(
    preprocessing_function=tf.keras.applications.efficientnet.preprocess_input
)

data = datagen.flow_from_directory(
    DATASET_PATH,
    target_size=(IMG_SIZE, IMG_SIZE),
    batch_size=1,
    class_mode="categorical",
    shuffle=False
)

class_names = list(data.class_indices.keys())
print("Classes:", class_names)

# =========================
# DETECT MISLABELED
# =========================
wrong = []

print("\n🔍 Checking dataset...\n")

for i in range(len(data.filenames)):
    img_path = os.path.join(DATASET_PATH, data.filenames[i])

    img = cv2.imread(img_path)
    if img is None:
        continue

    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
    img = np.expand_dims(img, axis=0)
    img = tf.keras.applications.efficientnet.preprocess_input(img)

    pred = model.predict(img, verbose=0)[0]

    true_class = data.labels[i]
    pred_class = np.argmax(pred)

    confidence = np.max(pred)

    # =========================
    # RULE FOR "WRONG LABEL"
    # =========================
    if pred_class != true_class and confidence > 0.70:
        wrong.append({
            "file": data.filenames[i],
            "true": class_names[true_class],
            "pred": class_names[pred_class],
            "conf": float(confidence)
        })

# =========================
# RESULTS
# =========================
print(f"\n❌ Found {len(wrong)} likely mislabeled images:\n")

for w in wrong[:50]:
    print(f"{w['file']}")
    print(f"   TRUE: {w['true']}")
    print(f"   PRED: {w['pred']}")
    print(f"   CONF: {w['conf']:.2f}")
    print("-" * 40)

# save report
with open("mislabeled_report.txt", "w", encoding="utf-8") as f:
    for w in wrong:
        f.write(f"{w['file']} | TRUE: {w['true']} | PRED: {w['pred']} | CONF: {w['conf']:.2f}\n")

print("\n✅ Report saved as mislabeled_report.txt")