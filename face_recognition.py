import cv2
from deepface import DeepFace
import os
from database import mark_attendance

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
detected_faces = {}  # Diccionario para almacenar los IDs detectados por sesión

def face_recognition(socketio, frame, session_id):
    """
    Detects faces in the given frame, compares them with registered faces, and draws bounding boxes.
    :param socketio: Instance of Socket.IO to emit events.
    :param frame: The current video frame from the ESP32-CAM.
    :param session_id: Session ID for recording attendance.
    """
    global detected_faces

    # Inicializar el conjunto para la sesión actual si no existe
    if session_id not in detected_faces:
        detected_faces[session_id] = set()

    # Save the frame temporarily for processing
    temp_frame_path = "temp_frame.jpg"
    cv2.imwrite(temp_frame_path, frame)

    try:
        # Compare the frame with registered faces
        results = DeepFace.find(img_path=temp_frame_path, db_path=REGISTERED_FACES_DIR, enforce_detection=False)

        # Process results from DeepFace.find (list of DataFrames)
        for df in results:
            if not df.empty:
                for _, row in df.iterrows():
                    student_id = os.path.basename(row["identity"]).split("_")[0]  # Extract student ID from filename
                    if student_id not in detected_faces[session_id]:
                        detected_faces[session_id].add(student_id)

                        # Mark attendance in the database
                        mark_attendance(student_id=student_id, session_id=session_id)

                        # Emit event to the client
                        socketio.emit('update_student', {'id': student_id}, namespace='/')

                        print(f"Face recognized: {student_id}")

        # Use OpenCV's face detection to draw rectangles
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

    except Exception as e:
        print(f"Error processing face: {e}")
    finally:
        # Remove the temporary file
        if os.path.exists(temp_frame_path):
            os.remove(temp_frame_path)