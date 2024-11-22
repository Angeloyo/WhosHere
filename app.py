from flask import Flask, request, Response, render_template, redirect, url_for, send_file
from database import init_db, add_student, delete_student, get_students
import cv2
from pyzbar.pyzbar import decode  # Librería para decodificar QR

app = Flask(__name__)
init_db()

# Configuración general
USE_WEBCAM = True  # Cambia a False para usar el ESP32-CAM
WEB_CAM_INDEX = 0  # Índice de la webcam local
ESP32_URL = "http://<IP_DEL_ESP32>/stream"

# Configuración del video
FRAME_WIDTH = 640    # Ancho del video (cambia a 0 para usar el predeterminado)
FRAME_HEIGHT = 480   # Alto del video (cambia a 0 para usar el predeterminado)

# Lista de alumnos detectados (IDs en verde)
present_students = set()

@app.route('/')
def index():
    students = get_students()
    students_with_status = [
        (student[0], student[1], str(student[0]) in present_students)
        for student in students
    ]
    return render_template('index.html', students=students_with_status)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        action = request.form['action']
        if action == 'add':
            name = request.form['name']
            add_student(name)
        elif action == 'delete':
            student_id = request.form['id']
            delete_student(student_id)
        return redirect(url_for('admin'))
    students = get_students()
    return render_template('admin.html', students=students)

@app.route('/qrcodes/<int:student_id>')
def get_qr(student_id):
    filepath = f"qrcodes/{student_id}.png"
    return send_file(filepath, mimetype='image/png')

def generar_frames():
    global present_students
    if USE_WEBCAM:
        cap = cv2.VideoCapture(WEB_CAM_INDEX)
    else:
        cap = cv2.VideoCapture(ESP32_URL)
    
    if FRAME_WIDTH > 0 and FRAME_HEIGHT > 0:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    while True:
        success, frame = cap.read()
        if not success:
            break
        
        # Decodificar QR en el frame
        decoded_objects = decode(frame)
        if decoded_objects:
            print(f"[INFO] Se detectaron {len(decoded_objects)} códigos QR.")
        else:
            print("[INFO] No se detectaron códigos QR en este frame.")

        for obj in decoded_objects:
            qr_data = obj.data.decode('utf-8')  # Convertir el contenido del QR a texto
            print(f"[INFO] Código QR detectado: {qr_data}")

            # Separar el ID del contenido del QR
            qr_id = qr_data.split('|')[0]  # Tomar solo el ID antes del separador "|"
            print(f"[DEBUG] ID extraído del QR: {qr_id}")

            # Verificar si el ID coincide con algún alumno
            student_ids = [str(student[0]) for student in get_students()]
            if qr_id in student_ids:
                print(f"[INFO] El ID {qr_id} coincide con un alumno.")
                present_students.add(qr_id)  # Marcar al alumno como presente
            else:
                print(f"[WARNING] El ID {qr_id} no coincide con ningún alumno.")

        # Mostrar el frame original
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generar_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)