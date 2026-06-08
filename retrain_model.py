import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.models import load_model

MODEL_PATH = "best_model.h5"
DATASET_PATH = "dataset"

# ========================
# LOAD MODEL
# ========================
model = load_model(MODEL_PATH)

# ========================
# DATASET
# ========================
datagen = ImageDataGenerator(
    rescale=1./255,
    validation_split=0.2
)

train_data = datagen.flow_from_directory(
    DATASET_PATH,
    target_size=(224, 224),
    batch_size=16,
    class_mode='categorical',
    subset='training',
    shuffle=True
)

val_data = datagen.flow_from_directory(
    DATASET_PATH,
    target_size=(224, 224),
    batch_size=16,
    class_mode='categorical',
    subset='validation',
    shuffle=False
)

# ========================
# SAFETY CHECK (VERY IMPORTANT)
# ========================
num_classes = len(train_data.class_indices)
print("Classes:", train_data.class_indices)
print("Num classes:", num_classes)

# 🚨 FIX IF MODEL MISMATCH
if model.output_shape[-1] != num_classes:
    raise ValueError(
        f"Model output ({model.output_shape[-1]}) != dataset classes ({num_classes})"
    )

# ========================
# FREEZE LAYERS
# ========================
for layer in model.layers[:-20]:
    layer.trainable = False

for layer in model.layers[-20:]:
    layer.trainable = True

# ========================
# COMPILE
# ========================
model.compile(
    optimizer=tf.keras.optimizers.Adam(1e-5),
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

# ========================
# TRAIN
# ========================
model.fit(
    train_data,
    validation_data=val_data,
    epochs=5
)

# ========================
# SAVE
# ========================
model.save("best_model.h5")

print("✅ Model updated successfully")