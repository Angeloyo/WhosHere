
# from pyzbar.pyzbar import decode
import cv2
import numpy as np
import requests
from qr_recognition import qr_recognition
from face_recognition import face_recognition

def generate_frames_webcam(socketio, session_id, width=640, height=480):
    """
    Generates frames for streaming, detects a single QR code with OpenCV, and emits events to the client.
    """
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    while True:
        success, frame = cap.read()
        if not success:
            break

        qr_recognition(socketio, frame, session_id)
        face_recognition(socketio, frame, session_id)

        # to-do :
        # only mark attendance when student id from qr and face recognition match !

        # Encode the frame for streaming
        _, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cap.release()

import requests
from requests.exceptions import ChunkedEncodingError

def generate_frames_esp32(socketio, session_id, url):
    """
    Generates frames from an MJPEG stream of an ESP32-CAM and detects QR codes using OpenCV.
    :param socketio: Instance of Socket.IO to emit events.
    :param session_id: Session ID for recording attendance.
    :param url: MJPEG stream URL.
    """
    try:
        stream = requests.get(url, stream=True, timeout=10)
        bytes_data = b''

        for chunk in stream.iter_content(chunk_size=1024):
            try:
                bytes_data += chunk
                a = bytes_data.find(b'\xff\xd8')  # Start of JPEG
                b = bytes_data.find(b'\xff\xd9')  # End of JPEG
                if a != -1 and b != -1:
                    jpg = bytes_data[a:b+2]
                    bytes_data = bytes_data[b+2:]

                    # Validate that the buffer is not empty
                    if len(jpg) == 0:
                        continue  # Skip this frame if the buffer is empty

                    frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                    
                    # Check if decoding was successful
                    if frame is None:
                        continue  # Skip this frame if decoding failed

                    # qr_recognition(socketio, frame, session_id)
                    face_recognition(socketio, frame, session_id)

                    # Encode the frame
                    _, buffer = cv2.imencode('.jpg', frame)
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

            except ChunkedEncodingError as e:
                print(f"Chunked Encoding Error: {e}")
                break  # Exit the loop on this error
            
            except Exception as e:
                print(f"Unexpected error while processing chunks: {e}")
                continue

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to the stream: {e}")
