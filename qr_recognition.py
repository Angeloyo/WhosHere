import cv2
from database import mark_attendance

def qr_recognition(socketio, frame, session_id):

    qr_decoder = cv2.QRCodeDetector()
    detected_ids = set()

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