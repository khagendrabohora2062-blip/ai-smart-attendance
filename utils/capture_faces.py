import cv2
import os
import numpy as np


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


CASCADE_PATH = os.path.join(
    cv2.data.haarcascades,
    "haarcascade_frontalface_default.xml"
)


def capture_face_image(student_id, image_bytes, image_number):

    dataset_path = os.path.join(
        BASE_DIR,
        "dataset"
    )

    student_folder = os.path.join(
        dataset_path,
        str(student_id)
    )

    os.makedirs(
        student_folder,
        exist_ok=True
    )

    if not os.path.exists(CASCADE_PATH):
        raise Exception(
            "Haar Cascade file not found: "
            + CASCADE_PATH
        )

    face_detector = cv2.CascadeClassifier(
        CASCADE_PATH
    )

    if face_detector.empty():
        raise Exception(
            "Failed to load Haar Cascade: "
            + CASCADE_PATH
        )

    try:
        image_number = int(image_number)
    except (TypeError, ValueError):
        return {
            "success": False,
            "message": "Invalid image number.",
            "count": 0
        }

    if image_number <= 0:
        return {
            "success": False,
            "message": "Image number must be greater than 0.",
            "count": 0
        }

    if not image_bytes:
        return {
            "success": False,
            "message": "No image received.",
            "count": 0
        }

    image_array = np.frombuffer(
        image_bytes,
        dtype=np.uint8
    )

    frame = cv2.imdecode(
        image_array,
        cv2.IMREAD_COLOR
    )

    if frame is None:
        return {
            "success": False,
            "message": "Invalid camera image.",
            "count": 0
        }

    gray = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2GRAY
    )

    gray = cv2.equalizeHist(gray)

    faces = face_detector.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(100, 100)
    )

    if len(faces) == 0:
        return {
            "success": False,
            "message": "No face detected. Look directly at the camera.",
            "count": 0
        }

    if len(faces) > 1:
        return {
            "success": False,
            "message": "Multiple faces detected. Only one person should be in front of the camera.",
            "count": 0
        }

    x, y, w, h = faces[0]

    if w < 120 or h < 120:
        return {
            "success": False,
            "message": "Face is too small. Move closer to the camera.",
            "count": 0
        }

    margin = int(min(w, h) * 0.15)

    x1 = max(0, x - margin)
    y1 = max(0, y - margin)
    x2 = min(gray.shape[1], x + w + margin)
    y2 = min(gray.shape[0], y + h + margin)

    face = gray[y1:y2, x1:x2]

    if face.size == 0:
        return {
            "success": False,
            "message": "Unable to crop detected face.",
            "count": 0
        }

    face = cv2.resize(
        face,
        (200, 200),
        interpolation=cv2.INTER_AREA
    )

    image_path = os.path.join(
        student_folder,
        f"{image_number}.jpg"
    )

    if not cv2.imwrite(image_path, face):
        raise Exception(
            "Failed to save face image: "
            + image_path
        )

    image_count = 0

    for filename in os.listdir(student_folder):
        if filename.lower().endswith(
            (".jpg", ".jpeg", ".png")
        ):
            image_count += 1

    return {
        "success": True,
        "message": "Face captured successfully.",
        "count": image_count,
        "image_number": image_number,
        "path": image_path
    }
