import cv2
import os
import numpy as np


# ============================================================
# BASE DIRECTORY
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


# ============================================================
# DATASET PATH
# ============================================================

DATASET_PATH = os.path.join(
    BASE_DIR,
    "dataset"
)


# ============================================================
# HAAR CASCADE
# ============================================================

CASCADE_PATH = os.path.join(
    cv2.data.haarcascades,
    "haarcascade_frontalface_default.xml"
)


# ============================================================
# FACE SETTINGS
# ============================================================

FACE_SIZE = (200, 200)

MIN_FACE_SIZE = (100, 100)

FACE_MARGIN = 0.15


# ============================================================
# CAPTURE FACE IMAGE
# ============================================================

def capture_face_image(
    student_id,
    image_bytes,
    image_number
):

    # --------------------------------------------------------
    # Validate Student ID
    # --------------------------------------------------------

    if student_id is None:

        return {
            "success": False,
            "message": "Student ID is required.",
            "count": 0
        }

    student_id = str(student_id).strip()

    if not student_id:

        return {
            "success": False,
            "message": "Student ID is required.",
            "count": 0
        }


    # --------------------------------------------------------
    # Validate Image Number
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # Validate Image
    # --------------------------------------------------------

    if not image_bytes:

        return {
            "success": False,
            "message": "No image received.",
            "count": 0
        }


    # --------------------------------------------------------
    # Student Dataset Folder
    #
    # IMPORTANT:
    # student_id used here must be the SAME ID
    # that is used by the training model.
    # --------------------------------------------------------

    student_folder = os.path.join(
        DATASET_PATH,
        student_id
    )

    os.makedirs(
        student_folder,
        exist_ok=True
    )


    # --------------------------------------------------------
    # Load Haar Cascade
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # Decode Browser Image
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # Convert to Gray
    # --------------------------------------------------------

    gray = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2GRAY
    )


    # --------------------------------------------------------
    # Histogram Equalization
    #
    # Same preprocessing is also used during recognition.
    # --------------------------------------------------------

    gray = cv2.equalizeHist(
        gray
    )


    # --------------------------------------------------------
    # Detect Face
    # --------------------------------------------------------

    faces = face_detector.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=MIN_FACE_SIZE
    )


    # --------------------------------------------------------
    # No Face
    # --------------------------------------------------------

    if len(faces) == 0:

        return {
            "success": False,
            "message": (
                "No face detected. "
                "Look directly at the camera."
            ),
            "count": 0
        }


    # --------------------------------------------------------
    # Multiple Faces
    # --------------------------------------------------------

    if len(faces) > 1:

        return {
            "success": False,
            "message": (
                "Multiple faces detected. "
                "Only one person should be in front "
                "of the camera."
            ),
            "count": 0
        }


    # --------------------------------------------------------
    # Get Face
    # --------------------------------------------------------

    x, y, w, h = faces[0]


    # --------------------------------------------------------
    # Face Too Small
    # --------------------------------------------------------

    if w < 100 or h < 100:

        return {
            "success": False,
            "message": (
                "Face is too small. "
                "Move closer to the camera."
            ),
            "count": 0
        }


    # --------------------------------------------------------
    # Add Margin Around Face
    #
    # IMPORTANT:
    # Training and recognition must use the same crop.
    # --------------------------------------------------------

    margin = int(
        min(w, h) * FACE_MARGIN
    )


    x1 = max(
        0,
        x - margin
    )

    y1 = max(
        0,
        y - margin
    )

    x2 = min(
        gray.shape[1],
        x + w + margin
    )

    y2 = min(
        gray.shape[0],
        y + h + margin
    )


    # --------------------------------------------------------
    # Crop Face
    # --------------------------------------------------------

    face = gray[
        y1:y2,
        x1:x2
    ]


    if face.size == 0:

        return {
            "success": False,
            "message": "Unable to crop detected face.",
            "count": 0
        }


    # --------------------------------------------------------
    # Resize
    # --------------------------------------------------------

    face = cv2.resize(
        face,
        FACE_SIZE,
        interpolation=cv2.INTER_AREA
    )


    # --------------------------------------------------------
    # Equalize Cropped Face Again
    # --------------------------------------------------------

    face = cv2.equalizeHist(
        face
    )


    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    image_path = os.path.join(
        student_folder,
        f"{image_number}.jpg"
    )


    success = cv2.imwrite(
        image_path,
        face
    )


    if not success:

        raise Exception(
            "Failed to save face image: "
            + image_path
        )


    # --------------------------------------------------------
    # Count Images
    # --------------------------------------------------------

    image_count = 0


    for filename in os.listdir(
        student_folder
    ):

        if filename.lower().endswith(
            (
                ".jpg",
                ".jpeg",
                ".png"
            )
        ):

            image_count += 1


    # --------------------------------------------------------
    # Return
    # --------------------------------------------------------

    return {

        "success": True,

        "message":
            "Face captured successfully.",

        "count":
            image_count,

        "image_number":
            image_number,

        "path":
            image_path
    }