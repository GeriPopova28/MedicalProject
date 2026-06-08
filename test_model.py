import tensorflow as tf
import numpy as np
import cv2
import os

# Заредете модела
image_path = r"dataset\train\000001.jpg"
img = cv2.imread(image_path)

# Път до една конкретна снимка за тест
img = cv2.imread(image_path) # Сменете с ваша снимка
img = cv2.resize(img, (224, 224))
img = np.expand_dims(img, axis=0)
img = tf.keras.applications.efficientnet.preprocess_input(img)

pred = model.predict(img)
print("Вероятности:", pred)
print("Клас 0 (Benign) ->", pred[0][0])
print("Клас 1 (Malignant) ->", pred[0][1])