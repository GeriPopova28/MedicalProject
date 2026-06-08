import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2' 
from tkinter import *
from tkinter import messagebox, filedialog
from tkinter.ttk import Progressbar
import json, datetime
import cv2
import numpy as np
import hashlib
import matplotlib.pyplot as plt
from PIL import Image as PILImage  # <--- ТОВА Е ВАЖНОТО: прекръстваме го на PILImage
from PIL import ImageTk
import mysql.connector
from fpdf import FPDF

# Референции за лупата, за да не ги трие Garbage Collector-а
magnified_tk = None
current_full_img_cv = None

def export_pdf_report(patient_name, data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="MEDICAL DIAGNOSTIC REPORT", ln=True, align='C')
    
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Patient: {patient_name}", ln=True)
    pdf.cell(200, 10, txt=f"Date: {datetime.datetime.now().strftime('%Y-%m-%d')}", ln=True)
    pdf.ln(5)
    pdf.cell(200, 10, txt=f"AI Prediction: {data['ai']}", ln=True)
    pdf.cell(200, 10, txt=f"Confidence: {data['confidence']*100:.2f}%", ln=True)
    pdf.ln(10)
    pdf.multi_cell(0, 10, txt=f"Doctor's Notes: {data.get('advice', 'No notes.')}")
    
    filename = f"Report_{patient_name}_{datetime.datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(filename)
    messagebox.showinfo("PDF Export", f"Report saved as {filename}")

def enhance_medical_image(img_path):
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    # Прилагаме CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(img)
    return enhanced

# --- Конфигурация на MySQL ---
db_config = {
    "host": "localhost",
    "user": "root",        # Твоето потребителско име (обикновено root)
    "password": "GeriP2807", # ТВОЯТА ПАРОЛА ТУК
    "database": "medai_db", 
    "port": 3306
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        print(f"❌ MySQL Error: {err}") # Ще изпише в конзолата точно какво не е наред
        return None

def process_and_find_roi(image_path):
    # 1. Зареждаме снимката с OpenCV
    img = cv2.imread(image_path)
    if img is None: return None, 0
    
    # 2. Изчистване (Preprocessing)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) # Превръщаме в сиво
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)    # Изчистваме "шума"
    
    # 3. Прагова сегментация (Thresholding)
    # Тук програмата разделя "обекта" от "фона"
    _, thresh = cv2.threshold(blurred, 100, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # 4. Намиране на контури (Критичната област)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    area = 0
    if contours:
        # Намираме най-големия контур (вероятната критична зона)
        c = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(c)
        
        # Рисуваме червена линия около критичната област
        cv2.drawContours(img, [c], -1, (0, 0, 255), 2)
        
        # Очертаваме и правоъгълник (Bounding Box)
        x, y, w, h = cv2.boundingRect(c)
        cv2.rectangle(img, (x, y), (x+w, y+h), (255, 0, 0), 1)
        cv2.putText(img, "CRITICAL ZONE", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

    return img, area

# Тези импорти трябва да са внимателни
try:
    import tensorflow as tf
    from tensorflow.keras.models import load_model
except ImportError:
    print("Грешка: Инсталирайте tensorflow (pip install tensorflow)")

# ... следват функциите ти ...

def log_action(user, action):
    try:
        with open("audit_log.txt", "a", encoding="utf-8") as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] User: {user} | Action: {action}\n")
    except Exception as e:
        print(f"Log error: {e}")
        
# -----------------------------
# --- Зареждане на AI модел ---
# -----------------------------
try:
    model = load_model("final_model.keras")
    print("✅ AI model loaded")
except:
    ai_model = None
    print("⚠ No trained model found")

# -----------------------------
# --- Файлове за база данни ---
# -----------------------------
USERS_DB = "users.json"
PATIENTS_DB = "patients.json"

if os.path.exists(USERS_DB):
    with open(USERS_DB, "r") as f:
        users_db = json.load(f)
else:
    users_db = {}

if os.path.exists(PATIENTS_DB):
    with open(PATIENTS_DB, "r") as f:
        patients_db = json.load(f)
else:
    patients_db = {}

# -----------------------------
# --- Ъпдейт на стари записи ---
# -----------------------------
def update_old_entries():
    for patient, entries in patients_db.items():
        for e in entries:
            e.setdefault('color', (255,255,255))
            e.setdefault('symbol', '?')
            e.setdefault('advice', "No advice yet")
            e.setdefault('timestamp', "N/A")
update_old_entries()

# -----------------------------
# --- Хеш за пароли ---
# -----------------------------
def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()

# -----------------------------
# --- Запис на бази ---
# -----------------------------
def save_users(): 
    with open(USERS_DB, "w") as f: json.dump(users_db, f)
def save_patients(): 
    with open(PATIENTS_DB, "w") as f: json.dump(patients_db, f)

# -----------------------------
# --- Crop ROI ---
# -----------------------------
def crop_roi(img):
    gray = img if len(img.shape) == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        c = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(c)
        return img[y:y+h, x:x+w]
    return img

# -----------------------------
# --- Explainable AI ---
# -----------------------------
def ai_explain(treatment, area, mean):
    explanations = {
        "Medication": f"Small area ({area}) and low intensity ({mean}) → minimal intervention.",
        "Observation": f"Moderate area ({area}) or intensity ({mean}) → monitoring recommended.",
        "Surgery": f"Large area ({area}) or high intensity ({mean}) → surgery suggested."
    }
    return explanations.get(treatment, "")

# -----------------------------
# --- AI Предсказване ---
# -----------------------------
def ai_predict(username, area, perimeter, mean, img_array=None):
    if ai_model is None or img_array is None:
        return "No Model", 0.0, "?", (255,255,255), "Model not loaded", [0,0,0]

    try:
        img_cropped = crop_roi(img_array)
        img = cv2.resize(img_cropped, (160, 160))
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        img = img.astype("float32") / 255.0
        img = np.expand_dims(img, axis=0)

        predictions = ai_model.predict(img, verbose=0)[0]
        print(f"[AI FULL] Predictions: {predictions}")

        classes = ["Medication", "Observation", "Surgery"]
        idx = np.argmax(predictions)
        conf = float(predictions[idx])
        treatment = classes[idx]

        second_idx = np.argsort(predictions)[-2]
        second_conf = float(predictions[second_idx])

        print(f"[AI DEBUG] Best: {treatment} ({conf:.2f}) | Second: {classes[second_idx]} ({second_conf:.2f})")

        # Adaptive confidence
        if conf < 0.4:
            return "Uncertain", conf, "?", (180,180,180), "⚠ AI is not confident", predictions.tolist()

        # Цветове и символи
        if treatment == "Surgery":
            symbol, color = "✖", (255,0,0)
        elif treatment == "Observation":
            symbol, color = "✓", (255,255,0)
        else:
            symbol, color = "⚠", (0,255,0)

        # AI advice
        if conf - second_conf < 0.15:
            advice = f"AI is unsure between {treatment} and {classes[second_idx]}"
        else:
            advice = f"AI predicts {treatment} with confidence {conf:.2f}. " + ai_explain(treatment, area, mean)

        print(f"[AI RESULT] User: {username} | {treatment} ({conf:.2f})")
        return treatment, conf, symbol, color, advice, predictions.tolist()

    except Exception as e:
        print("AI ERROR:", e)
        return "Error", 0.0, "?", (255,0,0), "Prediction failed", [0,0,0]

# -----------------------------
# --- Heatmap (Grad-CAM стил) ---
# -----------------------------
def generate_ai_heatmap(img_resized, area, mean, img_array=None, alpha=0.6):
    norm_img = cv2.normalize(img_resized, None, 0, 255, cv2.NORM_MINMAX)

    if ai_model is not None and img_array is not None:
        try:
            img_cropped = crop_roi(img_array)
            img_input = cv2.resize(img_cropped, (224,224))
            if len(img_input.shape) == 2:
                img_input = cv2.cvtColor(img_input, cv2.COLOR_GRAY2RGB)
            img_input = img_input.astype("float32") / 255.0
            img_input = np.expand_dims(img_input, axis=0)

            from tensorflow.keras.models import Model
            last_conv_layer = ai_model.layers[-3]
            grad_model = Model([ai_model.inputs], [last_conv_layer.output, ai_model.output])

            with tf.GradientTape() as tape:
                conv_outputs, predictions = grad_model(img_input)
                pred_index = tf.argmax(predictions[0])
                loss = predictions[:, pred_index]

            grads = tape.gradient(loss, conv_outputs)
            if grads is None:
                raise Exception("No gradients computed")

            conv_outputs = conv_outputs[0].numpy()
            axes = tuple(range(len(grads.shape)-1))
            pooled_grads = tf.reduce_mean(grads, axis=axes).numpy()

            for i in range(conv_outputs.shape[-1]):
                conv_outputs[..., i] *= pooled_grads[i]

            heatmap = np.mean(conv_outputs, axis=-1)
            heatmap = np.maximum(heatmap, 0)
            heatmap /= np.max(heatmap) + 1e-8
            heatmap = cv2.resize(heatmap, (img_resized.shape[1], img_resized.shape[0]))
            heatmap_color = cv2.applyColorMap(np.uint8(255*heatmap), cv2.COLORMAP_JET)
            overlay = cv2.addWeighted(cv2.cvtColor(img_resized, cv2.COLOR_GRAY2BGR), 1-alpha, heatmap_color, alpha, 0)
            return overlay

        except Exception as e:
            print("Heatmap Grad-CAM failed:", e)

    # Fallback heatmap
    area_factor = min(area / 20000, 2)
    mean_factor = min(mean / 150, 2)
    weight_map = (norm_img.astype(np.float32) * area_factor * mean_factor).clip(0,255).astype(np.uint8)
    heatmap_color = cv2.applyColorMap(weight_map, cv2.COLORMAP_JET)
    overlay = cv2.addWeighted(cv2.cvtColor(img_resized, cv2.COLOR_GRAY2BGR), 1-alpha, heatmap_color, alpha, 0)
    return overlay

# -----------------------------
# --- Registration / Login ---
# -----------------------------
def register():
    username = entry_reg_username.get()
    password = entry_reg_password.get()
    role = var_role.get()
    if not username or not password:
        messagebox.showerror("Error","Enter username and password")
        return
    if username in users_db:
        messagebox.showerror("Error","User exists")
        return
    users_db[username] = {"password": hash_pass(password), "role": role}
    save_users()
    messagebox.showinfo("Success", f"User {username} registered")
    entry_reg_username.delete(0, END)
    entry_reg_password.delete(0, END)

def login():
    username = entry_login_username.get()
    password = entry_login_password.get()
    if username not in users_db or users_db[username]["password"] != hash_pass(password):
        messagebox.showerror("Error","Wrong credentials")
        return
    role = users_db[username]["role"]
    login_window.destroy()
    if role=="doctor":
        open_doctor_window(username)
    else:
        open_patient_window(username)

# -----------------------------
# --- Patient Window ---
# -----------------------------

def generate_report(username, data):
    report_win = Toplevel()
    report_win.title("Medical Diagnostic Report")
    report_win.geometry("450x600")
    report_win.configure(bg="white")

    # Стилизирана бланка
    Label(report_win, text="MED-AI DIAGNOSTIC SYSTEMS", font=("Courier", 16, "bold"), bg="white", fg="#1f618d").pack(pady=10)
    Label(report_win, text="OFFICIAL ANALYSIS REPORT", font=("Arial", 10, "bold"), bg="white").pack()
    
    canvas = Canvas(report_win, height=2, bg="black", highlightthickness=0)
    canvas.pack(fill="x", padx=20, pady=10)

    report_text = f"""
    DATE: {data.get('timestamp', 'N/A')}
    PATIENT ID: {username.upper()}
    -------------------------------------------
    
    ANALYSIS DETAILS:
    - Target Area: {data.get('area', 0)} px
    - Tissue Density (Mean): {data.get('mean', 0)}
    
    AI DIAGNOSIS: 
    >>> {data.get('ai', 'Unknown').upper()} <<<
    
    CONFIDENCE LEVEL: {data.get('confidence', 0)*100:.2f}%
    
    PHYSICIAN ADVICE:
    {data.get('advice', 'No specific advice.')}
    
    -------------------------------------------
    DISCLAIMER: This report is generated by an 
    AI system and should be reviewed by a 
    certified medical professional.
    """
    
    Label(report_win, text=report_text, font=("Courier", 11), bg="white", justify=LEFT, anchor="nw").pack(padx=20, pady=20, fill="both")
    
    Button(report_win, text="CLOSE & SAVE", command=report_win.destroy, bg="#1f618d", fg="white").pack(pady=10)

def open_comparison_view(username):
    if username not in patients_db or len(patients_db[username]) < 2:
        messagebox.showinfo("Инфо", "Трябват поне 2 записа за сравнение!")
        return

    comp_win = Toplevel()
    comp_win.title(f"Comparison: {username}")
    comp_win.geometry("900x500")
    comp_win.configure(bg="#2c3e50") # Тъмен режим за по-добър контраст

    Label(comp_win, text="SIDE-BY-SIDE PROGRESS ANALYSIS", font=("Arial", 14, "bold"), 
          bg="#2c3e50", fg="white").pack(pady=10)

    frame = Frame(comp_win, bg="#2c3e50")
    frame.pack(expand=True, fill="both")

    # Взимаме първата и последната снимка
    first = patients_db[username][0]
    last = patients_db[username][-1]

    for i, data in enumerate([first, last]):
        sub_f = Frame(frame, bg="#34495e", bd=2, relief=RIDGE)
        sub_f.pack(side=LEFT, padx=20, pady=10, expand=True)
        
        lbl_title = "INITIAL SCAN" if i == 0 else "LATEST SCAN"
        Label(sub_f, text=lbl_title, bg="#34495e", fg="#ecf0f1", font=("Arial", 10, "bold")).pack()
        
        # Зареждане на картинката
        img = cv2.imread(data["image"])
        img = cv2.resize(img, (300, 300))
        img_tk = ImageTk.PhotoImage(PILImage.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)))
        
        img_lbl = Label(sub_f, image=img_tk, bg="black")
        img_lbl.image = img_tk
        img_lbl.pack(pady=5)
        
        info = f"Date: {data['timestamp'][:10]}\nArea: {data['area']} px\nResult: {data['ai']}"
        Label(sub_f, text=info, bg="#34495e", fg="white", justify=LEFT).pack(pady=5)

    # Изчисляване на разликата
    diff = first['area'] - last['area']
    status = "IMPROVING" if diff > 0 else "EXPANDING"
    color = "#2ecc71" if diff > 0 else "#e74c3c"
    
    Label(comp_win, text=f"TREND: {status} ({abs(diff)} px difference)", 
          font=("Arial", 12, "bold"), bg=color, fg="white").pack(side=BOTTOM, fill="x")
    
def open_medical_journal(username):
    journal_win = Toplevel()
    journal_win.title(f"Medical Journal: {username}")
    journal_win.geometry("500x600")
    journal_win.configure(bg="#ecf0f1")

    Label(journal_win, text="📊 PERSONAL HEALTH LOG", font=("Arial", 14, "bold"), 
          bg="#ecf0f1", fg="#2c3e50").pack(pady=10)

    txt_area = Text(journal_win, height=20, width=55, font=("Consolas", 10))
    txt_area.pack(pady=10, padx=10)

    if username not in patients_db or not patients_db[username]:
        txt_area.insert(END, "No records found. Upload a scan to start your journal.")
    else:
        log = "ID | DATE       | STATUS      | AREA \n"
        log += "-"*45 + "\n"
        for i, rec in enumerate(patients_db[username]):
            log += f"{i+1:02d} | {rec['timestamp'][:10]} | {rec['ai'][:10].ljust(11)} | {rec['area']}px\n"
        
        # Автоматичен анализ на тенденцията
        areas = [r['area'] for r in patients_db[username]]
        if len(areas) >= 2:
            trend = areas[-1] - areas[0]
            log += "\n" + "="*45 + "\n"
            log += f"TOTAL CHANGE: {trend} pixels\n"
            if trend < 0:
                log += "SYSTEM ADVICE: Positive regression detected. Keep current treatment.\n"
            elif trend > 1000:
                log += "SYSTEM ADVICE: WARNING! Rapid growth. Contact specialist ASAP.\n"
            else:
                log += "SYSTEM ADVICE: Stable condition. Regular monitoring required.\n"
        
        txt_area.insert(END, log)
    
    txt_area.config(state=DISABLED) # Само за четене
    Button(journal_win, text="PRINT LOG (Simulation)", command=lambda: messagebox.showinfo("Print", "Sending to printer..."), 
           bg="#34495e", fg="white").pack(pady=10)
    
def open_patient_window(username):
    patient_win = Toplevel()
    patient_win.title(f"Patient: {username}")
    patient_win.geometry("600x850") # Малко по-широк за графиките
    patient_win.configure(bg="#f0f4f8")

    Label(patient_win, text=f"Welcome, {username}!", fg="#1f618d",
          font=("Arial",16,"bold"), bg="#f0f4f8").pack(pady=10)

    current_idx = [0]

    # --- Image Frame ---
    img_frame = Frame(patient_win, bg="white", bd=2, relief=RIDGE)
    img_frame.pack(pady=10)
    img_label = Label(img_frame, bg="white")
    img_label.pack(padx=10, pady=10)

    # --- Transparency Slider ---
    alpha_val = DoubleVar(value=0.6)
    alpha_slider = Scale(patient_win, from_=0, to=1, resolution=0.1,
                         orient=HORIZONTAL, variable=alpha_val,
                         length=200, label="Heatmap Transparency")
    alpha_slider.pack()

    # --- Info Frame ---
    info_frame = Frame(patient_win, bg="white", bd=2, relief=RIDGE)
    info_frame.pack(pady=10, fill="x", padx=20)

    ai_label = Label(info_frame, text="", fg="#1f618d", bg="white", font=("Arial",12,"bold"))
    ai_label.pack(pady=5)

    confidence_bar = Progressbar(info_frame, length=300)
    confidence_bar.pack(pady=5)

    advice_label = Label(info_frame, text="", fg="#7d3c98", bg="white",
                         wraplength=400, justify=LEFT)
    advice_label.pack(pady=5)

    timestamp_label = Label(info_frame, text="", fg="grey", bg="white")
    timestamp_label.pack(pady=5)

    history_box = Listbox(patient_win, height=5)
    history_box.pack(fill="x", padx=20)

    # --- ФУНКЦИЯ ЗА ПРОГРЕС (Графика на площта) ---
    def show_progress(user):
        if user not in patients_db or len(patients_db[user]) < 2:
            messagebox.showinfo("Info", "Трябват поне 2 снимки за графика на прогреса!")
            return
        
        plt.figure("Patient Progress", figsize=(6, 4))
        dates = [entry.get('timestamp', 'N/A')[:10] for entry in patients_db[user]]
        areas = [entry.get('area', 0) for entry in patients_db[user]]
        
        plt.plot(dates, areas, marker='o', color='blue', label='Tumor/ROI Area')
        plt.title(f"Analysis Progress: {user}")
        plt.ylabel("Area (pixels)")
        plt.xticks(rotation=45)
        plt.legend()
        plt.tight_layout()
        plt.show()

    def on_upload():
        file_path = filedialog.askopenfilename()
        if not file_path: return
    
    # Извикваме нашата нова функция
        processed_img, calculated_area = process_and_find_roi(file_path)
    
        if processed_img is not None:
        # Конвертираме от OpenCV формат (BGR) към формат за Tkinter (RGB)
            processed_img = cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB)
            img_pil = PILImage.fromarray(processed_img)
            img_pil = img_pil.resize((300, 300)) # Преоразмеряваме за екрана
        
            img_tk = ImageTk.PhotoImage(img_pil)
        
        # Показваме снимката в твоя Label (напр. lbl_image)
            lbl_scan_display.config(image=img_tk)
            lbl_scan_display.image = img_tk
        
        # Автоматично попълваме полето за Area
            area_entry.delete(0, END)
            area_entry.insert(0, str(int(calculated_area)))
        
            messagebox.showinfo("AI Analysis", f"Critical area detected: {int(calculated_area)} pixels")

    # --- Display Image Function ---
    def display_image(*args):
        if username not in patients_db or not patients_db[username]:
            img_label.config(image="", text="No images yet")
            ai_label.config(text="No data")
            return

        records = patients_db[username]
        if current_idx[0] >= len(records): current_idx[0] = 0
        data = records[current_idx[0]]

        if not os.path.exists(data["image"]):
            img_label.config(text="File missing on disk", image="")
            return

        # Зареждане и обработка
        img_orig = cv2.imread(data["image"], cv2.IMREAD_GRAYSCALE)
        img_resized = cv2.resize(img_orig, (224, 224))

        overlay = generate_ai_heatmap(
            img_resized,
            data.get('area', 0),
            data.get('mean', 0),
            img_array=img_orig,
            alpha=alpha_val.get()
        )
        
        # --- ФИКСЪТ Е ТУК ---
        img_rgb = cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB)
        pil_img = PILImage.fromarray(img_rgb) # <--- Използваме новото име PILImage
        img_tk = ImageTk.PhotoImage(pil_img)
        img_label.config(image=img_tk)
        img_label.image = img_tk
        # -------------------

        conf = data.get("confidence", 0.0)
        ai_res = data.get("ai", "Unknown")
        ai_label.config(text=f"AI Result: {ai_res} ({conf:.2f})")
        confidence_bar['value'] = conf * 100
        advice_label.config(text=data.get("advice", ""))

    # Свързваме слайдера с функцията
    alpha_val.trace("w", display_image)

    # --- Upload Image ---
    def upload_image():
        file_path = filedialog.askopenfilename(filetypes=[("Images","*.jpg;*.png;*.jpeg")])
        if not file_path: return

        img = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
        if img is None: return

        # Изчисления
        resized = cv2.resize(img, (200,200))
        area = int(np.sum(resized > 50)) 
        mean = int(np.mean(resized))
        
        # AI ПРЕДСКАЗВАНЕ
        treatment, conf, symbol, color, advice, probs = ai_predict(username, area, 0, mean, img)

        if username not in patients_db: patients_db[username] = []
        
        patients_db[username].append({
            "image": file_path,
            "area": area,
            "mean": mean,
            "ai": treatment,
            "confidence": conf,
            "probs": probs,
            "advice": advice,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        save_patients()
        current_idx[0] = len(patients_db[username]) - 1
        display_image()

    def change_index(step):
        if username in patients_db and patients_db[username]:
            current_idx[0] = (current_idx[0] + step) % len(patients_db[username])
            display_image()

    def try_generate_report():
        if username in patients_db and patients_db[username]:
            generate_report(username, patients_db[username][current_idx[0]])
        else:
            messagebox.showwarning("Warning", "Please upload a scan first!")

    # --- Buttons ---
    btn_frame = Frame(patient_win, bg="#f0f4f8")
    btn_frame.pack(pady=10)
    Button(btn_frame, text="Upload Scan", bg="#1f618d", fg="white", command=upload_image, width=15).pack(side=LEFT, padx=5)
    Button(btn_frame, text="View Progress", bg="#28b463", fg="white", command=lambda: show_progress(username), width=15).pack(side=LEFT, padx=5)

    nav = Frame(patient_win, bg="#f0f4f8")
    nav.pack()
    Button(nav, text="<< Prev", command=lambda: change_index(-1), width=10).pack(side=LEFT, padx=10)
    Button(nav, text="Next >>", command=lambda: change_index(1), width=10).pack(side=LEFT, padx=10)
    Button(btn_frame, text="Generate Report", bg="#e67e22", fg="white", 
       command=lambda: generate_report(username, patients_db[username][current_idx[0]]), 
       width=15).pack(side=LEFT, padx=5)
    
    Button(btn_frame, text="Compare Scans", bg="#9b59b6", fg="white", 
       command=lambda: open_comparison_view(username), width=15).pack(side=LEFT, padx=5)
    
    Button(btn_frame, text="Health Journal", bg="#34495e", fg="white", 
       command=lambda: open_medical_journal(username), width=15).pack(side=LEFT, padx=5)
    
    Button(btn_frame, text="Generate Report", bg="#e67e22", fg="white", 
       command=try_generate_report, width=15).pack(side=LEFT, padx=5)
    # Стартиране на показването
    display_image()

def show_logs():
    log_win = Toplevel()
    log_win.title("Audit Logs")
    log_win.geometry("600x400")
    txt = Text(log_win, font=("Consolas", 10))
    txt.pack(fill="both", expand=True)
    
    if os.path.exists("audit_log.txt"):
        with open("audit_log.txt", "r", encoding="utf-8") as f:
            txt.insert(END, f.read())
    else:
        txt.insert(END, "No logs found.")
    txt.config(state=DISABLED)

def show_logs():
    log_win = Toplevel()
    log_win.title("📜 System Audit Logs")
    log_win.geometry("600x400")
    txt = Text(log_win, font=("Consolas", 10), bg="#f4f4f4")
    txt.pack(fill="both", expand=True, padx=10, pady=10)
    
    if os.path.exists("audit_log.txt"):
        with open("audit_log.txt", "r", encoding="utf-8") as f:
            txt.insert(END, f.read())
    else:
        txt.insert(END, "No logs recorded yet.")
    txt.config(state=DISABLED)

def doctor_open_patient():
    messagebox.showinfo("Module Loading", "Full patient history analysis is being generated...")

# --- ДОКТОРСКИ МОДУЛ (ЗАВЪРШЕН) ---
def open_doctor_window(username):
    doctor_win = Toplevel()
    doctor_win.title(f"👨‍⚕️ Professional Medical Dashboard - Dr. {username}")
    doctor_win.geometry("1250x850")
    doctor_win.configure(bg="#f0f4f8")

    # --- Header ---
    header_frame = Frame(doctor_win, bg="#1fb38d", height=70)
    header_frame.pack(fill="x")
    Label(header_frame, text=f"Medical Analysis System | Physician: {username}", 
          font=("Arial", 16, "bold"), bg="#1fb38d", fg="white").pack(pady=15)

    # --- Main Container ---
    main_container = Frame(doctor_win, bg="#f0f4f8")
    main_container.pack(fill="both", expand=True, padx=20, pady=10)

    # --- ЛЯВА ЧАСТ (Списък пациенти) ---
    left_frame = Frame(main_container, bg="#f0f4f8")
    left_frame.pack(side=LEFT, fill="y", padx=(0, 20))

    Label(left_frame, text="📋 Patient Directory", font=("Arial", 10, "bold"), bg="#f0f4f8").pack(anchor="w")
    search_ent = Entry(left_frame, font=("Arial", 11), width=30)
    search_ent.pack(pady=5)

    lb_frame = Frame(left_frame)
    lb_frame.pack(fill="both", expand=True)
    scrollbar = Scrollbar(lb_frame)
    scrollbar.pack(side=RIGHT, fill=Y)

    lb = Listbox(lb_frame, width=35, height=35, font=("Courier New", 10), 
                 yscrollcommand=scrollbar.set, selectbackground="#1fb38d")
    lb.pack(side=LEFT, fill="both")
    scrollbar.config(command=lb.yview)

    # --- ДЯСНА ЧАСТ (Анализ) ---
    right_frame = Frame(main_container, bg="white", bd=1, relief=RIDGE)
    right_frame.pack(side=RIGHT, fill="both", expand=True)

    # 1. Визуализация (Снимка + Лупа)
    visual_section = Frame(right_frame, bg="white")
    visual_section.pack(fill="x", padx=10, pady=10)

    main_img_sub = Frame(visual_section, bg="white")
    main_img_sub.pack(side=LEFT, padx=5)
    img_container = Frame(main_img_sub, bg="#2c3e50", bd=2, relief=SUNKEN)
    img_container.pack()
    img_display_lbl = Label(img_container, text="[ SELECT PATIENT ]", bg="#2c3e50", fg="white", 
                            font=("Arial", 10), width=55, height=16, cursor="hand2")
    img_display_lbl.pack()

    zoom_sub = Frame(visual_section, bg="white")
    zoom_sub.pack(side=LEFT, padx=15)
    img_zoom_lbl = Label(zoom_sub, text="Hover over scan", bg="#2c3e50", fg="#bdc3c7", 
                         width=280, height=280, relief=RIDGE)
    img_zoom_lbl.pack_propagate(False)
    img_zoom_lbl.pack(pady=2)

    # 2. Данни
    data_section = Frame(right_frame, bg="#f8f9fa", bd=1, relief=SOLID)
    data_section.pack(fill="x", padx=15, pady=5)
    det_txt = Text(data_section, bg="#f8f9fa", font=("Consolas", 10), height=5, state=DISABLED, relief=FLAT)
    det_txt.pack(fill="x", padx=10, pady=5)

    conf_frame = Frame(data_section, bg="#f8f9fa")
    conf_frame.pack(fill="x", padx=10, pady=(0, 10))
    conf_label = Label(conf_frame, text="AI Confidence: 0%", font=("Arial", 9, "bold"), bg="#f8f9fa")
    conf_label.pack(side=LEFT)
    conf_canvas = Canvas(conf_frame, width=250, height=12, bg="#ecf0f1", highlightthickness=0)
    conf_canvas.pack(side=LEFT, padx=15)

    # 3. Бележки
    Label(right_frame, text="👨‍⚕️ Physician's Evaluation:", font=("Arial", 10, "bold"), bg="white", fg="#1f618d").pack(anchor="w", padx=15)
    doctor_note_ent = Text(right_frame, height=4, font=("Arial", 11), bg="#fdfefe", bd=1, relief=SOLID)
    doctor_note_ent.pack(padx=15, pady=5, fill="x")

    # --- Логически функции ---
    def refresh_list(filter_text=""):
        lb.delete(0, END)
        for p_name, recs in patients_db.items():
            if filter_text.lower() in p_name.lower():
                stat = recs[-1]['ai'] if recs else "N/A"
                icon = "🔴" if stat == "Surgery" else "🟢"
                lb.insert(END, f"{icon} {p_name.ljust(15)} | {stat}")

    def on_select(event):
        global current_full_img_cv, magnified_tk
        selection = lb.curselection()
        if not selection: return
        item_text = lb.get(selection[0])
        p_name = item_text.split('|')[0].strip().split(" ", 1)[-1]
        
        if p_name in patients_db and patients_db[p_name]:
            last_rec = patients_db[p_name][-1]
            det_txt.config(state=NORMAL)
            det_txt.delete("1.0", END)
            det_txt.insert(END, f"PATIENT: {p_name}\nPREDICTION: {last_rec['ai']}\nAREA: {last_rec['area']} px\nDATE: {last_rec['timestamp']}")
            det_txt.config(state=DISABLED)
            
            conf = last_rec.get('confidence', 0)
            conf_canvas.delete("all")
            bar_color = "#27ae60" if conf > 0.8 else "#f1c40f" if conf > 0.5 else "#e74c3c"
            conf_canvas.create_rectangle(0, 0, conf * 250, 12, fill=bar_color, outline="")
            conf_label.config(text=f"AI Confidence: {conf*100:.1f}%", fg=bar_color)

            img_path = last_rec.get('image', '')
            if img_path and os.path.exists(img_path):
                current_full_img_cv = cv2.imread(img_path)
                if current_full_img_cv is not None:
                    img_rgb = cv2.cvtColor(current_full_img_cv, cv2.COLOR_BGR2RGB)
                    img_tk = ImageTk.PhotoImage(PILImage.fromarray(img_rgb).resize((450, 280)))
                    img_display_lbl.config(image=img_tk, text="")
                    img_display_lbl.image = img_tk

    def update_zoom(e):
        global magnified_tk, current_full_img_cv
        if current_full_img_cv is None: return
        H, W = current_full_img_cv.shape[:2]
        scale_x, scale_y = W / 450, H / 280
        orig_x, orig_y = int(e.x * scale_x), int(e.y * scale_y)
        z = 50
        crop = current_full_img_cv[max(0, orig_y-z):min(H, orig_y+z), max(0, orig_x-z):min(W, orig_x+z)]
        if crop.size > 0:
            crop_res = cv2.resize(crop, (280, 280))
            magnified_tk = ImageTk.PhotoImage(PILImage.fromarray(cv2.cvtColor(crop_res, cv2.COLOR_BGR2RGB)))
            img_zoom_lbl.config(image=magnified_tk, text="")
            img_zoom_lbl.image = magnified_tk

    def finalize_diagnosis(status):
        selection = lb.curselection()
        if not selection: return
        p_name = lb.get(selection[0]).split('|')[0].strip().split(" ", 1)[-1]
        note = doctor_note_ent.get("1.0", END).strip()
        if p_name in patients_db:
            patients_db[p_name][-1].update({'validation': status, 'advice': note})
            save_patients()
            log_action(username, f"Validated {p_name} as {status}")
            messagebox.showinfo("Success", "Diagnosis saved.")
            refresh_list()

    def save_and_export():
        selection = lb.curselection()
        if not selection: return
        p_name = lb.get(selection[0]).split('|')[0].strip().split(" ", 1)[-1]
        last_rec = patients_db[p_name][-1]
        last_rec['advice'] = doctor_note_ent.get("1.0", END).strip()
        export_pdf_report(p_name, last_rec)

    # --- Бутони ---
    btn_f = Frame(right_frame, bg="white")
    btn_f.pack(pady=10)
    Button(btn_f, text="✅ CONFIRM AI", bg="#27ae60", fg="white", width=15, command=lambda: finalize_diagnosis("VERIFIED")).pack(side=LEFT, padx=5)
    Button(btn_f, text="⚠️ OVERWRITE", bg="#e67e22", fg="white", width=15, command=lambda: finalize_diagnosis("CORRECTED")).pack(side=LEFT, padx=5)
    Button(right_frame, text="📄 Generate Official Report", bg="#1f618d", fg="white", font=("Arial", 10, "bold"), command=save_and_export).pack(pady=5)
    
    # --- Event Bindings ---
    img_display_lbl.bind('<Motion>', update_zoom)
    lb.bind("<<ListboxSelect>>", on_select)
    search_ent.bind("<KeyRelease>", lambda e: refresh_list(search_ent.get()))
    
    refresh_list()

# --- СТАРТИРАНЕ ---
if __name__ == "__main__":
    login_window = Tk()
    login_window.title("MedAI Login")
    login_window.geometry("350x500")

    # Register Frame
    register_frame = Frame(login_window, bg="white", bd=2, relief=RIDGE)
    register_frame.pack(pady=10, padx=20, fill="x")
    Label(register_frame, text="Register", font=("Arial",14,"bold"), bg="white", fg="#1f618d").pack(pady=5)
    Label(register_frame, text="Username", bg="white").pack()
    entry_reg_username = Entry(register_frame)
    entry_reg_username.pack()
    Label(register_frame, text="Password", bg="white").pack()
    entry_reg_password = Entry(register_frame, show="*")
    entry_reg_password.pack()
    var_role = StringVar(value="patient")
    Radiobutton(register_frame, text="Patient", variable=var_role, value="patient", bg="white").pack()
    Radiobutton(register_frame, text="Doctor", variable=var_role, value="doctor", bg="white").pack()
    Button(register_frame, text="Register", command=register).pack(pady=5)

    # Логин част
    login_frame = Frame(login_window, bg="white", bd=2, relief=RIDGE)
    login_frame.pack(pady=10, padx=20, fill="x")
    Label(login_frame, text="Login", font=("Arial", 12, "bold"), bg="white").pack()
    entry_login_username = Entry(login_frame); entry_login_username.pack()
    entry_login_password = Entry(login_frame, show="*"); entry_login_password.pack()
    Button(login_frame, text="Login", command=login).pack(pady=5)

    login_window.mainloop()