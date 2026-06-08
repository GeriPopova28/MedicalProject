import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.applications import EfficientNetB0
from tensorflow.keras.applications.efficientnet import preprocess_input

# =========================
# CONFIG
# =========================
IMG_SIZE = 224
NUM_CLASSES = 3


# =========================
# IMAGE BRANCH
# =========================
image_input = tf.keras.Input(shape=(IMG_SIZE, IMG_SIZE, 3), name="image_input")

x = preprocess_input(image_input)

base_model = EfficientNetB0(
    include_top=False,
    weights="imagenet",
    input_shape=(IMG_SIZE, IMG_SIZE, 3)
)

base_model.trainable = False

x = base_model(x, training=False)
x = layers.GlobalAveragePooling2D()(x)

x = layers.Dense(256, activation="relu")(x)
x = layers.BatchNormalization()(x)
x = layers.Dropout(0.4)(x)


# =========================
# LAB BRANCH
# =========================
lab_input = tf.keras.Input(shape=(4,), name="lab_input")  
# [TSH, FT4, MAT, TAT]

y = layers.Dense(64, activation="relu")(lab_input)
y = layers.BatchNormalization()(y)
y = layers.Dense(32, activation="relu")(y)
y = layers.Dropout(0.2)(y)


# =========================
# FUSION
# =========================
combined = layers.concatenate([x, y])

z = layers.Dense(128, activation="relu")(combined)
z = layers.BatchNormalization()(z)
z = layers.Dropout(0.4)(z)

z = layers.Dense(64, activation="relu")(z)
z = layers.Dropout(0.2)(z)


# =========================
# OUTPUT
# =========================
output = layers.Dense(NUM_CLASSES, activation="softmax")(z)


model = models.Model(
    inputs=[image_input, lab_input],
    outputs=output
)


# =========================
# COMPILE
# =========================
model.compile(
    optimizer=tf.keras.optimizers.Adam(1e-4),
    loss="categorical_crossentropy",
    metrics=[
        "accuracy",
        tf.keras.metrics.Precision(name="precision"),
        tf.keras.metrics.Recall(name="recall")
    ]
)

model.summary()