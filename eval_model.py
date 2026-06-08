import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications.efficientnet import preprocess_input
from sklearn.metrics import classification_report, confusion_matrix

IMG_SIZE = (224, 224)
DATASET_DIR = "dataset"

model = tf.keras.models.load_model("best_model.h5")

val_datagen = ImageDataGenerator(preprocessing_function=preprocess_input)

val_gen = val_datagen.flow_from_directory(
    DATASET_DIR + "/val",
    target_size=IMG_SIZE,
    batch_size=16,
    class_mode="categorical",
    shuffle=False
)

# predictions
y_pred = model.predict(val_gen)
y_pred_classes = np.argmax(y_pred, axis=1)

y_true = val_gen.classes

print("\n📊 CLASS REPORT:")
print(classification_report(y_true, y_pred_classes, target_names=list(val_gen.class_indices.keys())))

print("\n📊 CONFUSION MATRIX:")
print(confusion_matrix(y_true, y_pred_classes))