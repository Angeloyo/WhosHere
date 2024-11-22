from flask import Flask, render_template, redirect, url_for, send_file, request, Response
from flask_socketio import SocketIO, emit
from database import init_db, add_student, delete_student, get_students
import cv2
from pyzbar.pyzbar import decode

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
init_db()

# Configuración general
USE_WEBCAM = True
WEB_CAM_INDEX = 0
ESP32_URL = "http://<IP_DEL_ESP32>/stream"

FRAME_WIDTH = 640
FRAME_HEIGHT = 480
present_students = set()

@app.route('/')
def index():
    students = get_students()
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
        
        decoded_objects = decode(frame)
        for obj in decoded_objects:
            qr_data = obj.data.decode('utf-8')
            qr_id = qr_data.split('|')[0]  # Extraer el ID
            student_ids = [str(student[0]) for student in get_students()]
            if qr_id in student_ids and qr_id not in present_students:
                present_students.add(qr_id)
                print(f"[INFO] QR válido: {qr_id}")
                # Emitir el evento al cliente
                socketio.emit('update_student', {'id': qr_id})
            else:
                print(f"[WARNING] QR inválido o ya registrado: {qr_id}")

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generar_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001)