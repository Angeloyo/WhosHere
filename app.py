from flask import Flask, request, Response, render_template, redirect, url_for, send_file
from database import init_db, add_student, delete_student, get_students
import cv2

app = Flask(__name__)
init_db()

# Cambia esta variable entre "webcam" o la URL del ESP32
USE_WEBCAM = True  # Ponlo en False para usar el ESP32-CAM
WEB_CAM_INDEX = 0  # Índice de la webcam local
ESP32_URL = "http://<IP_DEL_ESP32>/stream"

@app.route('/')
def index():
    students = get_students()  # Esto obtiene los datos de la base de datos
    return render_template('index.html', students=students)

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
    # Enviar el archivo QR correspondiente
    filepath = f"qrcodes/{student_id}.png"
    return send_file(filepath, mimetype='image/png')

def generar_frames():
    # Selecciona la fuente de video: webcam o ESP32-CAM
    if USE_WEBCAM:
        cap = cv2.VideoCapture(WEB_CAM_INDEX)
    else:
        cap = cv2.VideoCapture(ESP32_URL)
    
    while True:
        success, frame = cap.read()
        if not success:
            break
        # Procesar el frame aquí si hace falta (QR o rostro)
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    # Genera el streaming de video desde la fuente seleccionada
    return Response(generar_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)