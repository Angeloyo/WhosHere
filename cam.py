
# from pyzbar.pyzbar import decode
import cv2
import numpy as np
import requests
from database import mark_attendance

def generate_frames_webcam(socketio, session_id, width=640, height=480):
    """
    Generates frames for streaming, detects a single QR code with OpenCV, and emits events to the client.
    """
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    qr_decoder = cv2.QRCodeDetector()
    detected_ids = set()

    while True:
        success, frame = cap.read()
        if not success:
            break

        # Detect and decode a single QR code
        qr_data, points, _ = qr_decoder.detectAndDecode(frame)
        if qr_data:
            qr_data_id, qr_data_name = qr_data.split('|')  # Assumes format "ID|Name"
            if qr_data_id not in detected_ids:
                detected_ids.add(qr_data_id)

                # Mark attendance in the database
                mark_attendance(student_id=qr_data_id, session_id=session_id)

                # Emit event to update the client
                socketio.emit('update_student', {'id': qr_data_id}, namespace='/')

            # Draw a rectangle around the QR code
            if points is not None and len(points) > 0:
                points = points[0].astype(int)  # Convert to integers
                for i in range(len(points)):
                    pt1 = tuple(points[i])
                    pt2 = tuple(points[(i + 1) % len(points)])
                    cv2.line(frame, pt1, pt2, (0, 255, 0), 2)

                # Display the QR code ID on the video
                x, y = points[0]  # Coordinate of the first point
                cv2.putText(frame, qr_data_name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        # Encode the frame for streaming
        _, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cap.release()

def generate_frames_esp32(socketio, session_id, url):
    """
    Generates frames from an MJPEG stream of an ESP32-CAM and detects QR codes using OpenCV.
    :param socketio: Instance of Socket.IO to emit events.
    :param session_id: Session ID for recording attendance.
    :param url: MJPEG stream URL.
    """
    stream = requests.get(url, stream=True)
    bytes_data = b''
    detected_ids = set()
    qr_code_detector = cv2.QRCodeDetector()

    for chunk in stream.iter_content(chunk_size=1024):
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

            # Detect QR codes with OpenCV
            data, points, _ = qr_code_detector.detectAndDecode(frame)
            if data:
                qr_data_id = data.split('|')[0]  # Student ID
                qr_data_name = data.split('|')[1] if '|' in data else 'Unknown'  # Student name (optional)
                if qr_data_id not in detected_ids:
                    detected_ids.add(qr_data_id)

                    # Mark attendance in the database
                    mark_attendance(student_id=qr_data_id, session_id=session_id)

                    # Emit event to update the client
                    socketio.emit('update_student', {'id': qr_data_id})

                # Draw a rectangle around the QR code
                if points is not None and len(points) > 0:
                    points = points[0].astype(int)  # Convert to integers
                    for i in range(len(points)):
                        pt1 = tuple(points[i])
                        pt2 = tuple(points[(i + 1) % len(points)])
                        cv2.line(frame, pt1, pt2, (0, 255, 0), 2)

                    # Display the QR code ID on the video
                    x, y = points[0]  # Coordinate of the first point
                    cv2.putText(frame, qr_data_name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

            # Encode the frame
            _, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')