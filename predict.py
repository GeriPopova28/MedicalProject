import tensorflow as tf
import numpy as np
from tensorflow.keras.preprocessing import image

model = tf.keras.models.load_model('ai_model_real.keras') 

def prepare_image(img_path):
    img = image.load_img(img_path, target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0) 
    return img_array

test_image_path = "path_to_your_ultrasound_image.jpg"

img = prepare_image(test_image_path)
prediction = model.predict(img)

classes = ['Benign', 'Malignant'] 
result = classes[np.argmax(prediction)]
confidence = np.max(prediction) * 100

print(f"Диагноза: {result}")
print(f"Увереност: {confidence:.2f}%")