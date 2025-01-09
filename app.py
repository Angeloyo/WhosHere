from flask import Flask, request, render_template, redirect, url_for, Response, send_file, jsonify
from database import *
from cam import generate_frames_webcam, generate_frames_esp32
from flask_socketio import SocketIO
from pin_state import pin_state
from detected_faces_state import detected_faces_state

app = Flask(__name__)
socketio = SocketIO(app)
init_db()

# Rutas Generales
@app.route('/')
def index():
    pin_state.expected_pin = None
    pin_state.current_student_id = None 
    pin_state.current_session_id = None
    pin_state.waiting_for_pin = False
    pin_state.current_pin = ""
    detected_faces_state.clear_all()  # Limpiar todas las sesiones
    sessions = get_sessions()
    return render_template('index.html', sessions=sessions)

# Ruta principal para mostrar el feed y la lista de alumnos
@app.route('/attendance', methods=['GET'])
def attendance():
    session_id = request.args.get('session_id', type=int, default=1)
    
    # Reiniciar el estado del PIN para la nueva sesión
    pin_state.expected_pin = None
    pin_state.current_student_id = None
    pin_state.current_session_id = None
    pin_state.waiting_for_pin = False
    pin_state.current_pin = ""
    
    # Inicializar/actualizar el estado de detected_faces para esta sesión
    detected_faces_state.init_session(session_id)
    
    # Obtener los estudiantes que ya han pasado lista y actualizar detected_faces
    present_students = get_present_students(session_id)
    for student_id in present_students:
        detected_faces_state.add_face(session_id, str(student_id))  # Convertir a string si es necesario
    
    # Obtener lista de todos los alumnos
    students = get_students()
    
    # Añadir información de estado a cada alumno
    students_with_status = [
        (student[0], student[1], student[0] in present_students)
        for student in students
    ]
    
    return render_template('attendance.html', 
                         students=students_with_status, 
                         session_id=session_id)

# Ruta para el streaming de video
@app.route('/webcam_feed/<int:session_id>')
def webcam_feed(session_id):
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
        elif action == 'delete_session':
            session_id = request.form['session_id']
            delete_session(session_id)  # Llama a la función para eliminar la sesión
        return redirect(url_for('admin'))

    students = get_students()
    sessions = get_sessions()
    return render_template('admin.html', students=students, sessions=sessions)

@app.route('/keypress')
def handle_keypress():
    key = request.args.get('key')
    
    if pin_state.waiting_for_pin:
        socketio.emit('key_pressed', {'key': key})
        
        pin_state.current_pin += key
        if len(pin_state.current_pin) == 4:
            if pin_state.current_pin == pin_state.expected_pin:
                # Marcar asistencia
                mark_attendance(pin_state.current_student_id, pin_state.current_session_id)
                # Añadir a detected_faces_state
                detected_faces_state.add_face(pin_state.current_session_id, pin_state.current_student_id)
                socketio.emit('pin_correct')
                socketio.emit('update_student', {'id': pin_state.current_student_id})
            else:
                socketio.emit('pin_wrong')
            
            pin_state.current_pin = ""
            pin_state.waiting_for_pin = False
            
    return jsonify({"status": "received"})

@socketio.on('wrong_student')
def handle_wrong_student():
    # Resetear el estado del PIN
    pin_state.expected_pin = None
    pin_state.current_student_id = None
    pin_state.current_session_id = None
    pin_state.waiting_for_pin = False
    pin_state.current_pin = ""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
