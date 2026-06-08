import os
import shutil
import xml.etree.ElementTree as ET

# =========================
# PATHS
# =========================
BASE_PATH = r"C:\Users\User\Downloads\28455641 (1)\TN5000_forReview\TN5000_forReview"

IMAGES_PATH = os.path.join(BASE_PATH, "JPEGImages")
ANNOTATIONS_PATH = os.path.join(BASE_PATH, "Annotations")

OUTPUT_DATASET = "dataset"

BENIGN_DIR = os.path.join(OUTPUT_DATASET, "Benign")
MALIGNANT_DIR = os.path.join(OUTPUT_DATASET, "Malignant")

os.makedirs(BENIGN_DIR, exist_ok=True)
os.makedirs(MALIGNANT_DIR, exist_ok=True)

# =========================
# PROCESS XML FILES
# =========================
count_benign = 0
count_malignant = 0

for xml_file in os.listdir(ANNOTATIONS_PATH):

    if not xml_file.endswith(".xml"):
        continue

    xml_path = os.path.join(ANNOTATIONS_PATH, xml_file)

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # image filename
        filename = root.find("filename").text

        image_path = os.path.join(IMAGES_PATH, filename)

        if not os.path.exists(image_path):
            continue

        # find label
        malignant = False

        for obj in root.findall("object"):

            name = obj.find("name").text.lower()

            # malignant labels
            if "malignant" in name or name == "1":
                malignant = True

        # copy image
        if malignant:
            shutil.copy(image_path, os.path.join(MALIGNANT_DIR, filename))
            count_malignant += 1
        else:
            shutil.copy(image_path, os.path.join(BENIGN_DIR, filename))
            count_benign += 1

    except Exception as e:
        print("Error:", xml_file, e)

print("\n✅ DATASET CREATED")
print(f"Benign: {count_benign}")
print(f"Malignant: {count_malignant}")