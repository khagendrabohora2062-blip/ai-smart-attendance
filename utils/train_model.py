import cv2
import os
import numpy as np
from PIL import Image


# ============================================================
# PATHS
# ============================================================

DATASET_PATH = "dataset"

TRAINER_PATH = "trainer/trainer.yml"


# ============================================================
# GET DATASET IMAGES AND LABELS
# ============================================================

def get_images_and_labels():

    face_samples = []

    ids = []

    # ========================================================
    # CHECK DATASET
    # ========================================================

    if not os.path.exists(DATASET_PATH):

        print(
            "Dataset folder missing."
        )

        return face_samples, ids

    # ========================================================
    # READ STUDENT FOLDERS
    # ========================================================

    for folder in sorted(
        os.listdir(DATASET_PATH)
    ):

        folder_path = os.path.join(
            DATASET_PATH,
            folder
        )

        # Only folders
        if not os.path.isdir(folder_path):

            continue

        # ====================================================
        # STUDENT DATABASE ID
        # ====================================================

        try:

            label = int(folder)

        except ValueError:

            print(
                "Skipping invalid folder:",
                folder
            )

            continue

        valid_images = 0

        # ====================================================
        # READ IMAGES
        # ====================================================

        for image in sorted(
            os.listdir(folder_path)
        ):

            image_path = os.path.join(
                folder_path,
                image
            )

            if not image.lower().endswith(
                (".jpg", ".jpeg", ".png")
            ):

                continue

            try:

                img = Image.open(
                    image_path
                ).convert("L")

                img_numpy = np.array(
                    img,
                    dtype="uint8"
                )

                # ============================================
                # CHECK IMAGE SIZE
                # ============================================

                if img_numpy.size == 0:

                    continue

                # Make all training images same size
                img_numpy = cv2.resize(
                    img_numpy,
                    (200, 200)
                )

                face_samples.append(
                    img_numpy
                )

                ids.append(
                    label
                )

                valid_images += 1

            except Exception as e:

                print(
                    f"Image error [{image_path}]:",
                    e
                )

        # ====================================================
        # STUDENT DATASET INFO
        # ====================================================

        if valid_images > 0:

            print(
                f"Student {label}: "
                f"{valid_images} images"
            )

        else:

            print(
                f"Student {label}: "
                f"NO VALID IMAGES"
            )

    return face_samples, ids


# ============================================================
# TRAIN FACE MODEL
# ============================================================

def train_faces():

    print()
    print("==============================")
    print("FACE TRAINING STARTED")
    print("==============================")
    print()

    # ========================================================
    # LOAD DATA
    # ========================================================

    faces, ids = get_images_and_labels()

    # ========================================================
    # NO DATA
    # ========================================================

    if len(faces) == 0:

        print()
        print(
            "ERROR: No face images found."
        )

        return False

    # ========================================================
    # CHECK STUDENTS
    # ========================================================

    unique_students = sorted(
        set(ids)
    )

    print()
    print(
        "Total training images:",
        len(faces)
    )

    print(
        "Total students:",
        len(unique_students)
    )

    print(
        "Student labels:",
        unique_students
    )

    # ========================================================
    # CREATE RECOGNIZER
    # ========================================================

    if not hasattr(cv2, "face"):

        print()
        print(
            "ERROR: cv2.face is not available."
        )

        print(
            "Install opencv-contrib-python."
        )

        return False

    recognizer = (
        cv2.face.LBPHFaceRecognizer_create(
            radius=1,
            neighbors=8,
            grid_x=8,
            grid_y=8
        )
    )

    # ========================================================
    # TRAIN
    # ========================================================

    recognizer.train(
        faces,
        np.array(ids)
    )

    # ========================================================
    # CREATE TRAINER DIRECTORY
    # ========================================================

    os.makedirs(
        "trainer",
        exist_ok=True
    )

    # ========================================================
    # SAVE MODEL
    # ========================================================

    recognizer.save(
        TRAINER_PATH
    )

    # ========================================================
    # COMPLETE
    # ========================================================

    print()
    print("==============================")
    print("FACE TRAINING COMPLETED")
    print("==============================")

    print(
        "Training Images :",
        len(faces)
    )

    print(
        "Students        :",
        len(unique_students)
    )

    print(
        "Saved Model     :",
        TRAINER_PATH
    )

    print("==============================")
    print()

    return True


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    train_faces()