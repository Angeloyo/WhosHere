
from pyzbar.pyzbar import decode
import cv2
import numpy as np
import requests

import cv2
from pyzbar.pyzbar import decode
import numpy as np

def generar_frames(socketio, session_id, width=640, height=480):
    """
    Genera frames para el streaming, detecta QR, y emite eventos al cliente.
    :param socketio: Instancia de Socket.IO para emitir eventos.
    :param session_id: ID de la sesión para marcar asistencia.
    :param width: Ancho del video.
    :param height: Alto del video.
    """
    cap = cv2.VideoCapture(1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    detected_ids = set()  # Almacenar IDs ya detectados para evitar duplicados

    while True:
        success, frame = cap.read()
        if not success:
            break

        # Detectar códigos QR
        decoded_objects = decode(frame)
        for obj in decoded_objects:
            qr_data_id = obj.data.decode('utf-8').split('|')[0]  # ID del alumno
            qr_data_name = obj.data.decode('utf-8').split('|')[1]  # nombre del alumno
            if qr_data_id not in detected_ids:
                detected_ids.add(qr_data_id)

                # Marcar asistencia en la base de datos
                from database import mark_attendance
                mark_attendance(student_id=qr_data_id, session_id=session_id)

                # Emitir evento para actualizar al cliente
                socketio.emit('update_student', {'id': qr_data_id})

            # Dibujar un recuadro alrededor del QR
            points = obj.polygon
            if len(points) == 4:
                pts = [(point.x, point.y) for point in points]
                pts = np.array(pts, dtype=np.int32)
                cv2.polylines(frame, [pts], isClosed=True, color=(0, 255, 0), thickness=2)

            # Mostrar el ID del QR en el video
            (x, y, w, h) = obj.rect
            cv2.putText(frame, qr_data_name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            # cv2.putText(frame, qr_data_id, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        # Codificar el frame para el streaming
        _, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cap.release()

def generar_frames_esp32(url):
    """
    Genera frames desde un flujo MJPEG de un ESP32-CAM.
    :param url: URL del flujo MJPEG (por ejemplo, http://192.168.0.101:81/stream).
    """
    stream = requests.get(url, stream=True)
    bytes_data = b''
    for chunk in stream.iter_content(chunk_size=1024):
        bytes_data += chunk
        a = bytes_data.find(b'\xff\xd8')  # Inicio del JPEG
        b = bytes_data.find(b'\xff\xd9')  # Fin del JPEG
        if a != -1 and b != -1:
            jpg = bytes_data[a:b+2]
            bytes_data = bytes_data[b+2:]
            frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
            _, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            
def generar_frames_esp32_with_qr(socketio, session_id, url):
    """
    Genera frames desde un flujo MJPEG de un ESP32-CAM y detecta QR.
    :param socketio: Instancia de Socket.IO para emitir eventos.
    :param session_id: ID de la sesión para registrar asistencia.
    :param url: URL del flujo MJPEG.
    """
    stream = requests.get(url, stream=True)
    bytes_data = b''
    detected_ids = set()

    for chunk in stream.iter_content(chunk_size=1024):
        bytes_data += chunk
        a = bytes_data.find(b'\xff\xd8')  # Inicio del JPEG
        b = bytes_data.find(b'\xff\xd9')  # Fin del JPEG
        if a != -1 and b != -1:
            jpg = bytes_data[a:b+2]
            bytes_data = bytes_data[b+2:]
            frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)

            # Detectar códigos QR
            # decoded_objects = decode(frame)
            # for obj in decoded_objects:
            #     qr_data = obj.data.decode('utf-8').split('|')[0]
            #     if qr_data not in detected_ids:
            #         detected_ids.add(qr_data)
            #         from database import mark_attendance
            #         mark_attendance(student_id=qr_data, session_id=session_id)
            #         socketio.emit('update_student', {'id': qr_data}, namespace='/')
            decoded_objects = decode(frame)
            for obj in decoded_objects:
                qr_data_id = obj.data.decode('utf-8').split('|')[0]  # ID del alumno
                qr_data_name = obj.data.decode('utf-8').split('|')[1]  # nombre del alumno
                if qr_data_id not in detected_ids:
                    detected_ids.add(qr_data_id)

                    # Marcar asistencia en la base de datos
                    from database import mark_attendance
                    mark_attendance(student_id=qr_data_id, session_id=session_id)

                    # Emitir evento para actualizar al cliente
                    socketio.emit('update_student', {'id': qr_data_id})

                # Dibujar un recuadro alrededor del QR
                points = obj.polygon
                if len(points) == 4:
                    pts = [(point.x, point.y) for point in points]
                    pts = np.array(pts, dtype=np.int32)
                    cv2.polylines(frame, [pts], isClosed=True, color=(0, 255, 0), thickness=2)

                # Mostrar el ID del QR en el video
                (x, y, w, h) = obj.rect
                cv2.putText(frame, qr_data_name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

            # Codificar el frame
            _, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')