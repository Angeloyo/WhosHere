import cv2
from deepface import DeepFace
import os
from database import mark_attendance
import random
from pin_state import pin_state
from detected_faces_state import detected_faces_state

# Ruta de las imágenes registradas
REGISTERED_FACES_DIR = "registered_faces"

def face_recognition(socketio, frame, session_id):
    """
    Continuously detects faces in the given frame, compares them with registered faces, and draws bounding boxes.
    :param socketio: Instance of Socket.IO to emit events.
    :param frame: The current video frame from the ESP32-CAM.
    :param session_id: Session ID for recording attendance.
    """
    try:
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        for (x, y, w, h) in faces:
            if pin_state.waiting_for_pin:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                continue

            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            face_region = frame[y:y + h, x:x + w]
            temp_face_path = "temp_face.jpg"
            cv2.imwrite(temp_face_path, face_region)

            try:
                results = DeepFace.find(img_path=temp_face_path, db_path=REGISTERED_FACES_DIR, enforce_detection=False)

                for df in results:
                    if not df.empty:
                        for _, row in df.iterrows():
                            student_id = os.path.basename(row["identity"]).split("_")[0]
                            student_name = os.path.basename(row["identity"]).split("_")[1]
                            
                            cv2.putText(frame, student_name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

                            if detected_faces_state.is_detected(session_id, student_id):
                                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                                cv2.putText(frame, "Asistencia registrada", (x, y - 30), 
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                                continue

                            if not pin_state.waiting_for_pin:
                                new_pin = ''.join(random.choices('1245', k=4))
                                
                                pin_state.expected_pin = new_pin
                                pin_state.current_student_id = student_id
                                pin_state.current_session_id = session_id
                                pin_state.waiting_for_pin = True
                                pin_state.current_pin = ""
                                
                                socketio.emit('request_pin', {
                                    'student_name': student_name,
                                    'pin': new_pin
                                })

                                print(f"Face recognized: {student_id} - {student_name}, waiting for PIN")

            except Exception as e:
                print(f"Error recognizing face: {e}")
            finally:
                if os.path.exists(temp_face_path):
                    os.remove(temp_face_path)

    except Exception as e:
        print(f"Error detecting faces: {e}")
