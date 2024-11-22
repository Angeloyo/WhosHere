from flask import Flask, request, Response, render_template, redirect, url_for
from database import init_db, add_student, delete_student, get_students
import cv2
import numpy as np

app = Flask(__name__)
init_db()

# Variable global para almacenar el último frame recibido
frame_global = None

@app.route('/')
def index():
    students = get_students()  # Esto obtiene los datos de la base de datos
    return render_template('index.html', students=students)

# Ruta /admin: página para gestionar alumnos
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

@app.route('/upload_video', methods=['POST'])
def upload_video():
    global frame_global
    # Recibe el frame enviado por el cliente
    file = request.files['video']
    img_array = np.frombuffer(file.read(), np.uint8)
    frame_global = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    return "Frame recibido", 200

def generar_frames():
    while True:
        if frame_global is not None:
            # Codifica el frame en formato JPEG
            _, buffer = cv2.imencode('.jpg', frame_global)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    # Genera el streaming de video
    return Response(generar_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
