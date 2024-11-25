import cv2
from deepface import DeepFace
import os

# Ruta de los rostros registrados
REGISTERED_FACES_DIR = "registered_faces"

# Cargar imágenes registradas
registered_faces = {}
for file in os.listdir(REGISTERED_FACES_DIR):
    if file.endswith(".jpg") or file.endswith(".png"):
        student_id = file.split("_")[0]  # Extraer el ID del archivo
        path = os.path.join(REGISTERED_FACES_DIR, file)
        registered_faces[student_id] = path


# Ruta de las imágenes registradas
REGISTERED_FACES_DIR = "registered_faces"
detected_faces = set()  # Para evitar múltiples reconocimientos del mismo rostro

def face_recognition(socketio, frame, session_id):
    """
    Detects faces in the given frame, compares them with registered faces, and draws bounding boxes.
    :param socketio: Instance of Socket.IO to emit events.
    :param frame: The current video frame from the ESP32-CAM.
    :param session_id: Session ID for recording attendance.
    """
    global detected_faces

    # Guardar frame temporalmente para procesamiento
    temp_frame_path = "temp_frame.jpg"
    cv2.imwrite(temp_frame_path, frame)

    face_locations = []  # Almacenar ubicaciones de rostros detectados

    # Iterar sobre las imágenes registradas
    for file in os.listdir(REGISTERED_FACES_DIR):
        if file.endswith(".jpg") or file.endswith(".png"):
            student_id, _ = file.split("_", 1)
            face_path = os.path.join(REGISTERED_FACES_DIR, file)

            try:
                # Comparar el frame con la imagen registrada
                result = DeepFace.verify(temp_frame_path, face_path, enforce_detection=True)
                if result["verified"] and student_id not in detected_faces:
                    detected_faces.add(student_id)

                    # Marcar asistencia en la base de datos
                    from database import mark_attendance
                    mark_attendance(student_id=student_id, session_id=session_id)

                    # Emitir evento al cliente
                    socketio.emit('update_student', {'id': student_id}, namespace='/')

                    print(f"Face recognized: {student_id}")
                    
                    # Draw a rectangle if facial_area exists
                    if "facial_area" in result:
                        face_area = result["facial_area"]
                        x, y, w, h = face_area["x"], face_area["y"], face_area["w"], face_area["h"]
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            except Exception as e:
                print(f"Error processing face: {e}")

    # Dibujar recuadros en los rostros detectados
    for loc in face_locations:
        x, y, w, h = loc["x"], loc["y"], loc["w"], loc["h"]
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

    # Eliminar el archivo temporal
    if os.path.exists(temp_frame_path):
        os.remove(temp_frame_path)