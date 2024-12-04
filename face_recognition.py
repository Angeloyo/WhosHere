import cv2
from deepface import DeepFace
import os
from database import mark_attendance

# Ruta de las imágenes registradas
REGISTERED_FACES_DIR = "registered_faces"
detected_faces = {}  # Diccionario para almacenar los IDs detectados por sesión


def face_recognition(socketio, frame, session_id):
    """
    Continuously detects faces in the given frame, compares them with registered faces, and draws bounding boxes.
    :param socketio: Instance of Socket.IO to emit events.
    :param frame: The current video frame from the ESP32-CAM.
    :param session_id: Session ID for recording attendance.
    """
    global detected_faces

    # Inicializar el conjunto para la sesión actual si no existe
    if session_id not in detected_faces:
        detected_faces[session_id] = set()

    try:
        # Detect faces using OpenCV
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        for (x, y, w, h) in faces:
            # Draw rectangle around the face
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            # Save the face region temporarily for recognition
            face_region = frame[y:y + h, x:x + w]
            temp_face_path = "temp_face.jpg"
            cv2.imwrite(temp_face_path, face_region)

            try:
                # Compare the face with registered faces
                results = DeepFace.find(img_path=temp_face_path, db_path=REGISTERED_FACES_DIR, enforce_detection=False)

                for df in results:
                    if not df.empty:
                        for _, row in df.iterrows():
                            student_id = os.path.basename(row["identity"]).split("_")[0]  # Extract student ID
                            student_name = os.path.basename(row["identity"]).split("_")[1]  # Extract student name
                            
                            # Draw the name above the rectangle
                            cv2.putText(frame, student_name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

                            # Mark attendance only if not already marked
                            if student_id not in detected_faces[session_id]:
                                detected_faces[session_id].add(student_id)

                                # Mark attendance in the database
                                mark_attendance(student_id=student_id, session_id=session_id)

                                # Emit event to the client
                                socketio.emit('update_student', {'id': student_id}, namespace='/')

                                print(f"Face recognized: {student_id} - {student_name}")

            except Exception as e:
                print(f"Error recognizing face: {e}")
            finally:
                if os.path.exists(temp_face_path):
                    os.remove(temp_face_path)

    except Exception as e:
        print(f"Error detecting faces: {e}")