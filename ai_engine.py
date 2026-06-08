import os
import cv2
import numpy as np
import tensorflow as tf
import time

from tensorflow.keras.models import load_model
from tensorflow.keras.applications.efficientnet import preprocess_input
from fpdf import FPDF


class MedicalAI:

    def __init__(self):

        try:
            from tensorflow.keras.models import model_from_json

            # LOAD MODEL ARCHITECTURE
            with open("model_architecture.json", "r") as f:
                loaded_json = f.read()

            self.model = model_from_json(loaded_json)

            # LOAD WEIGHTS
            self.model.load_weights("best_weights.h5")

            print("✅ Model loaded successfully")

        except Exception as e:
            self.model = None
            print(f"⚠ Model load error: {e}")

        # IMPORTANT:
        # MUST MATCH TRAINING CLASSES
        self.classes = ["Benign", "Malignant"]

    # =====================================================
    # QUIZ
    # =====================================================
    def generate_quiz(self, lab_data, symptoms):
        if not isinstance(lab_data, dict):
            lab_data = {}

        try:
            tsh_val = lab_data.get("tsh")
            tsh = float(tsh_val) if tsh_val not in [None, ""] else 0
        except:
            tsh = 0

        if tsh > 4.0:
            return {
                "question": "Какво може да означава висок TSH?",
                "options": ["Хипотиреоидизъм", "Нормална функция", "Ниска кръвна захар"],
                "answer": 0
            }
        elif 0 < tsh < 0.4:
            return {
                "question": "Какво може да означава нисък TSH?",
                "options": ["Хипертиреоидизъм", "Диабет", "Анемия"],
                "answer": 0
            }

        return {
            "question": "Коя жлеза контролира метаболизма?",
            "options": ["Щитовидна жлеза", "Бял дроб", "Черен дроб"],
            "answer": 0
        }

    # =====================================================
    # MAIN PREDICTION
    # =====================================================
    def predict(self, img_array, lab_data=None, symptoms=None):
        if self.model is None:
            return ("Error", 0, "Model not loaded", None)

        try:
            if img_array is None:
                return ("Error", 0, "No image provided", None)

            # IMAGE PREPROCESS
            img_rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
            img_resized = cv2.resize(img_rgb, (224, 224))

            img_input = np.expand_dims(img_resized, axis=0).astype("float32")
            img_input = preprocess_input(img_input)

            # MODEL PREDICTION
            preds = self.model.predict(img_input, verbose=0)[0]

            base_confidence = float(np.max(preds) * 100)
            class_idx = int(np.argmax(preds))
            label = self.classes[class_idx]

            # INFO MAP
            info = {
                "Benign": {
                    "title": "Benign finding",
                    "advice": "No malignant structure detected."
                },
                "Malignant": {
                    "title": "Malignant finding",
                    "advice": "Possible malignancy detected. Specialist required."
                }
            }
            

            title = info[label]["title"]
            advice = info[label]["advice"]

            # LAB DATA CORRELATION
            lab_score = 0
            if isinstance(lab_data, dict):
                def safe_float(v):
                    try:
                        if v is None or str(v).strip() == "":
                            return None
                        return float(v)
                    except:
                        return None

                tsh = safe_float(lab_data.get("tsh"))
                ft4 = safe_float(lab_data.get("ft4"))

                if tsh is not None and tsh > 4.2:
                    lab_score += 2
                if tsh is not None and tsh < 0.4:
                    lab_score += 2
                if ft4 is not None and ft4 > 22:
                    lab_score += 1

            # SYMPTOMS CORRELATION
            symptom_score = 0
            if symptoms:
                symptoms = [str(s).lower().strip() for s in symptoms]

                hypo = ["fatigue", "weight gain", "cold intolerance", "depression", "dry skin", "hair loss"]
                hyper = ["weight loss", "anxiety", "palpitations", "sweating", "insomnia", "tremor"]

                symptom_score += sum(1 for s in hypo if s in symptoms)
                symptom_score += sum(1 for s in hyper if s in symptoms)

            # FUSION LOGIC FOR CONFIDENCE SCORE
            confidence = base_confidence + (lab_score * 4) + (symptom_score * 2)
            confidence = min(max(confidence, 1), 99)

            # OVERRIDE LOGIC BASED ON LABS/SYMPTOMS
            if label == "Malignant":
                title = "High risk lesion detected"
                advice += " Severe endocrine imbalance suspected."
            elif lab_score >= 2:
                title = "Thyroid dysfunction suspected"
                advice += " Thyroid dysfunction indicators detected."

            if symptom_score >= 2:
                advice += " Symptoms correlate with endocrine dysfunction."

            # LOW CONFIDENCE UNCERTAINTY FILTER
            if base_confidence < 45:
                return (
                    "Uncertain Scan",
                    round(confidence, 2),
                    "Low confidence prediction from image analysis. Repeat scan or update laboratory tests.",
                    img_array
                )

            # HEATMAP GENERATION
            heatmap = self.generate_heatmap(img_array)
            overlay = self.overlay_heatmap(heatmap, img_array)

            return (
                title,
                round(confidence, 2),
                advice,
                overlay
            )

        except Exception as e:
            print("Prediction error:", e)
            return ("Error", 0, str(e), img_array)

    # =====================================================
    # EXPLANATION GENERATOR
    # =====================================================
    def get_explanation(self, prediction, confidence, lab_data=None, symptoms=None):
        conf = float(confidence)

        text = "CLINICAL AI INTERPRETATION\n"
        text += "===========================\n\n"
        text += f"Primary finding: {prediction}\n"
        text += f"Model confidence: {conf:.1f}%\n"

        # Коректно определяне на нивата на риск
        if "Critical" in prediction or conf >= 85:
            text += "Risk level: CRITICAL / HIGH\n\n"
            text += "Strong pathological patterns or major hormonal imbalances detected. Immediate clinical evaluation required.\n\n"
        elif "Suspicious" in prediction or conf >= 60:
            text += "Risk level: MODERATE\n\n"
            text += "Possible abnormal tissue patterns or minor test discrepancies detected. Clinical follow-up recommended.\n\n"
        else:
            text += "Risk level: LOW\n\n"
            text += "No major radiological or endocrinological indicators detected.\n\n"

        if lab_data and isinstance(lab_data, dict):
            text += "Laboratory correlation:\n"
            try:
                def extract_float(v):
                    if v is None or str(v).strip() == "":
                        return None
                    return float(v)

                tsh = extract_float(lab_data.get("tsh"))
                ft4 = extract_float(lab_data.get("ft4"))

                if tsh is not None:
                    if tsh > 4.2:
                        text += f"- Elevated TSH ({tsh} mIU/L): Indicators point toward hypothyroidism.\n"
                    elif tsh < 0.4:
                        text += f"- Low TSH ({tsh} mIU/L): Indicators point toward hyperthyroidism.\n"
                    else:
                        text += f"- Normal TSH ({tsh} mIU/L).\n"

                if ft4 is not None:
                    if ft4 > 22:
                        text += f"- Elevated FT4 ({ft4} pmol/L).\n"
            except:
                text += "- Failed to parse lab metrics correctly.\n"
            text += "\n"

        if symptoms and len(symptoms) > 0:
            text += "Reported clinical symptoms:\n"
            for s in symptoms:
                if str(s).strip():
                    text += f"- {s.strip()}\n"
            text += "\n"

        text += "Disclaimer: AI decision support tool only. Not a standalone diagnostic confirmation."
        return text

    # =====================================================
    # GRAD-CAM HEATMAP
    # =====================================================
    def generate_heatmap(self, img_array):
        try:
            if self.model is None:
                return None

            img_rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
            img_resized = cv2.resize(img_rgb, (224, 224))
            img_input = preprocess_input(np.expand_dims(img_resized, axis=0).astype("float32"))

            last_conv_layer = None
            # Намиране на конволюционния слой, работи стабилно и при вложени модели
            for layer in reversed(self.model.layers):
                if hasattr(layer, 'output_shape') and len(layer.output_shape) == 4:
                    last_conv_layer = layer.name
                    break
                # Алтернативна поддръжка за някои видове EfficientNet имплементации
                if 'conv' in layer.name.lower() or 'top_activation' in layer.name.lower():
                    last_conv_layer = layer.name
                    break

            if not last_conv_layer:
                return None

            grad_model = tf.keras.Model(
                inputs=self.model.inputs,
                outputs=[self.model.get_layer(last_conv_layer).output, self.model.output]
            )

            with tf.GradientTape() as tape:
                conv, pred = grad_model(img_input)
                class_idx = tf.argmax(pred[0])
                loss = pred[:, class_idx]

            grads = tape.gradient(loss, conv)
            if grads is None:
                return None

            pooled = tf.reduce_mean(grads, axis=(0, 1, 2))
            conv = conv[0]

            heatmap = tf.reduce_sum(pooled * conv, axis=-1)
            heatmap = tf.maximum(heatmap, 0)

            max_val = tf.reduce_max(heatmap)
            if max_val == 0:
                return None

            heatmap /= max_val
            return heatmap.numpy()

        except Exception as e:
            print("Heatmap error:", e)
            return None

    # =====================================================
    # OVERLAY HEATMAP
    # =====================================================
    def overlay_heatmap(self, heatmap, original_img):
        try:
            if heatmap is None:
                return original_img

            heatmap = cv2.resize(heatmap, (original_img.shape[1], original_img.shape[0]))
            heatmap = np.uint8(255 * heatmap)
            heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)

            return cv2.addWeighted(original_img, 0.7, heatmap, 0.3, 0)

        except Exception as e:
            print("Overlay error:", e)
            return original_img