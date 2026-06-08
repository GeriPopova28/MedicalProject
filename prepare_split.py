import os
import random
import shutil

random.seed(42)

SOURCE_DIR = "dataset"

TRAIN_DIR = "dataset/train"
VAL_DIR = "dataset/val"

CLASSES = ["Benign", "Malignant"]

SPLIT = 0.8

# create folders
for split in ["train", "val"]:
    for cls in CLASSES:
        os.makedirs(f"dataset/{split}/{cls}", exist_ok=True)

for cls in CLASSES:

    src = os.path.join(SOURCE_DIR, cls)

    images = [
        f for f in os.listdir(src)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ]

    random.shuffle(images)

    split_idx = int(len(images) * SPLIT)

    train_images = images[:split_idx]
    val_images = images[split_idx:]

    # train
    for img in train_images:
        shutil.copy(
            os.path.join(src, img),
            os.path.join(TRAIN_DIR, cls, img)
        )

    # val
    for img in val_images:
        shutil.copy(
            os.path.join(src, img),
            os.path.join(VAL_DIR, cls, img)
        )

    print(f"{cls}:")
    print(f"Train -> {len(train_images)}")
    print(f"Val   -> {len(val_images)}")

print("\n✅ DATASET SPLIT READY")