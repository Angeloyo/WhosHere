import sqlite3
import qrcode
from PIL import Image, ImageDraw, ImageFont
import os

DB_NAME = "students.db"

# Inicializar la base de datos
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

# Añadir un alumno y generar su QR
def add_student(name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO students (name) VALUES (?)", (name,))
    conn.commit()

    # Obtener el ID del alumno recién añadido
    student_id = cursor.lastrowid
    conn.close()

    # Generar QR para el alumno
    generate_qr(student_id, name)
    return student_id

# Eliminar un alumno
def delete_student(student_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()

# Obtener todos los alumnos
def get_students():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()
    conn.close()
    return students

# Generar un QR con el ID y el nombre del alumno
def generate_qr(student_id, name):
    import qrcode
    from PIL import Image, ImageDraw, ImageFont
    import os

    # Crear la carpeta 'qrcodes' si no existe
    os.makedirs("qrcodes", exist_ok=True)

    # Contenido del QR
    data = f"{student_id}|{name}"

    # Generar el QR
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white").convert("RGB")

    # Añadir el texto debajo del QR
    draw = ImageDraw.Draw(img)
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # Ruta típica en Linux
    font_size = 20

    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        font = ImageFont.load_default()  # Fuente por defecto si falla la personalizada

    text = f"ID: {student_id} - {name}"

    # Usar textbbox para calcular las dimensiones del texto
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    img_width, img_height = img.size

    # Crear una nueva imagen más alta para incluir el texto
    new_height = img_height + text_height + 10
    new_img = Image.new("RGB", (img_width, new_height), "white")
    new_img.paste(img, (0, 0))

    # Dibujar el texto centrado
    text_x = (img_width - text_width) // 2
    draw = ImageDraw.Draw(new_img)
    draw.text((text_x, img_height + 5), text, fill="black", font=font)

    # Guardar la imagen
    new_img.save(f"qrcodes/{student_id}.png")
    print(f"QR generado para {name} con ID {student_id}")

