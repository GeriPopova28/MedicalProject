import tensorflow as tf
import numpy as np
from tensorflow.keras.preprocessing import image

# 1. Зареждане на вече обучения модел
model = tf.keras.models.load_model('medical_model.h5') # Увери се, че името съвпада

# 2. Функция за подготовка на изображението
def prepare_image(img_path):
    img = image.load_img(img_path, target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0) # Добавяне на batch измерение
    img_array /= 255.0 # Нормализация
    return img_array

# 3. Път към снимка за тест
test_image_path = "path_to_your_ultrasound_image.jpg"

# 4. Прогноза
img = prepare_image(test_image_path)
prediction = model.predict(img)

# Дефиниране на класовете (както са в твоя лог)
classes = ['Medication', 'Observation', 'Surgery']
result = classes[np.argmax(prediction)]
confidence = np.max(prediction) * 100

print(f"Диагноза: {result}")
print(f"Увереност: {confidence:.2f}%")