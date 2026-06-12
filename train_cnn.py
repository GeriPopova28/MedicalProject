import os
import numpy as np
import tensorflow as tf

from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import EfficientNetB0
from tensorflow.keras.applications.efficientnet import preprocess_input
from tensorflow.keras import layers, models
from sklearn.utils import class_weight
from sklearn.metrics import classification_report, confusion_matrix

IMG_SIZE = (224, 224)
BATCH_SIZE = 16
DATASET_DIR = "dataset"
def build_model():

    base_model = EfficientNetB0(
        weights="imagenet",
        include_top=False,
        input_shape=IMG_SIZE + (3,)
    )

    base_model.trainable = False

    inputs = tf.keras.Input(shape=IMG_SIZE + (3,))

    x = preprocess_input(inputs)
    x = base_model(x, training=False)

    x = layers.GlobalAveragePooling2D()(x)

    x = layers.Dense(512, activation="relu")(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.5)(x)

    x = layers.Dense(256, activation="relu")(x)
    x = layers.Dropout(0.3)(x)

    outputs = layers.Dense(2, activation="softmax")(x)

    model = models.Model(inputs, outputs)

    return model, base_model


# =========================
# TRAIN
# =========================
def train():

    datagen = ImageDataGenerator(
        preprocessing_function=preprocess_input,  
        rotation_range=20,
        zoom_range=0.2,
        width_shift_range=0.1,
        height_shift_range=0.1,
        horizontal_flip=True,
        validation_split=0.2
    )

    train_gen = datagen.flow_from_directory(
        DATASET_DIR,
        target_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        class_mode="categorical",
        subset="training",
        shuffle=True
    )

    val_gen = datagen.flow_from_directory(
        DATASET_DIR,
        target_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        class_mode="categorical",
        subset="validation",
        shuffle=False
    )

    print("\nCLASS MAP:", train_gen.class_indices)

    class_weights_raw = class_weight.compute_class_weight(
        class_weight="balanced",
        classes=np.unique(train_gen.classes),
        y=train_gen.classes
    )

    class_weights = dict(zip(
        np.unique(train_gen.classes),
        class_weights_raw.astype(float)
    ))

    print("\nCLASS WEIGHTS:", class_weights)

    model, base_model = build_model()

    model.compile(
        optimizer=tf.keras.optimizers.Adam(3e-4),
        loss="categorical_crossentropy",
        metrics=["accuracy"]
    )

    model.fit(
        train_gen,
        validation_data=val_gen,
        epochs=10,
        class_weight=class_weights,
        workers=1,
        use_multiprocessing=False  
    )

    base_model.trainable = True

    for layer in base_model.layers[:-30]:
        layer.trainable = False

    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-5),
        loss="categorical_crossentropy",
        metrics=["accuracy"]
    )

    model.fit(
        train_gen,
        validation_data=val_gen,
        epochs=15,
        class_weight=class_weights,
        workers=1,
        use_multiprocessing=False  
    )

    model.save("ai_model_real.keras")
    print("\nMODEL SAVED SUCCESSFULLY")

val_preds = model.predict(val_gen)
y_pred = np.argmax(val_preds, axis=1)
y_true = val_gen.classes

print(classification_report(y_true, y_pred))
print(confusion_matrix(y_true, y_pred))

if __name__ == "__main__":
    train()