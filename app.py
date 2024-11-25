from flask import Flask, request, render_template, redirect, url_for, Response, send_file
from database import (
    init_db, add_student, delete_student, get_students,
    add_session, get_sessions, get_present_students
)
from cam import generar_frames_webcam, generar_frames_esp32_with_qr_opencv
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)
init_db()

# Rutas Generales
@app.route('/')
def index():
    sessions = get_sessions()
    return render_template('index.html', sessions=sessions)

# Ruta principal para mostrar el feed y la lista de alumnos
@app.route('/attendance', methods=['GET'])
def attendance():
    session_id = request.args.get('session_id', type=int, default=1)  # ID de la sesión actual
    students = get_students()  # Obtener lista de todos los alumnos
    present_students = get_present_students(session_id)  # Obtener IDs de alumnos presentes

    # Añadir información de estado a cada alumno
    students_with_status = [
        (student[0], student[1], student[0] in present_students)
        for student in students
    ]

    return render_template('attendance.html', students=students_with_status, session_id=session_id)

# Ruta para el streaming de video
@app.route('/video_feed/<int:session_id>')
def video_feed(session_id):
    # Streaming de video con detección de QR
    return Response(generate_frames_webcam(socketio, session_id),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/esp32_feed/<int:session_id>')
def esp32_feed(session_id):
    esp32_url = "http://192.168.0.186:81/stream"  # Cambia por la IP de tu ESP32-CAM
    return Response(generate_frames_esp32(socketio, session_id, esp32_url),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/qrcodes/<int:student_id>')
def get_qr(student_id):
    filepath = f"qrcodes/{student_id}.png"
    return send_file(filepath, mimetype='image/png')

# Rutas Administrativas
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
        elif action == 'add_session':
            subject = request.form['subject']
            date = request.form['date']
            add_session(subject, date)
        return redirect(url_for('admin'))

    students = get_students()
    sessions = get_sessions()
    return render_template('admin.html', students=students, sessions=sessions)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)