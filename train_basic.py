import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.preprocessing.image import ImageDataGenerator

IMG_SIZE = (224, 224)
BATCH_SIZE = 16
DATASET_DIR = "dataset"

# =========================
# DATA
# =========================
datagen = ImageDataGenerator(
    validation_split=0.2,
    preprocessing_function=tf.keras.applications.efficientnet.preprocess_input,
    rotation_range=15,
    zoom_range=0.2,
    horizontal_flip=True
)

train_data = datagen.flow_from_directory(
    DATASET_DIR,
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode="categorical",
    subset="training"
)

val_data = datagen.flow_from_directory(
    DATASET_DIR,
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode="categorical",
    subset="validation"
)

print("CLASSES:", train_data.class_indices)

# =========================
# MODEL
# =========================
base = tf.keras.applications.EfficientNetB0(
    include_top=False,
    weights="imagenet",
    input_shape=(224, 224, 3)
)

base.trainable = False

x = layers.GlobalAveragePooling2D()(base.output)
x = layers.Dense(256, activation="relu")(x)
x = layers.Dropout(0.4)(x)

output = layers.Dense(2, activation="softmax")(x)

model = models.Model(inputs=base.input, outputs=output)

# =========================
# COMPILE
# =========================
model.compile(
    optimizer=tf.keras.optimizers.Adam(1e-4),
    loss="categorical_crossentropy",
    metrics=["accuracy"]
)

# =========================
# TRAIN
# =========================
model.fit(
    train_data,
    validation_data=val_data,
    epochs=15
)

# =========================
# SAVE
# =========================
model.save("model_basic.keras")

print("✅ TRAINING DONE")