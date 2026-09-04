import cv2
import os
import numpy as np
from PIL import Image


# ============================================================
# BASE DIRECTORY
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


# ============================================================
# PATHS
# ============================================================

DATASET_PATH = os.path.join(
    BASE_DIR,
    "dataset"
)

TRAINER_DIR = os.path.join(
    BASE_DIR,
    "trainer"
)

TRAINER_PATH = os.path.join(
    TRAINER_DIR,
    "trainer.yml"
)


# ============================================================
# FACE SIZE
# ============================================================

FACE_SIZE = (200, 200)


# ============================================================
# GET DATASET IMAGES AND LABELS
# ============================================================

def get_images_and_labels():

    face_samples = []

    ids = []


    # ========================================================
    # CHECK DATASET
    # ========================================================

    if not os.path.exists(
        DATASET_PATH
    ):

        print(
            "Dataset folder missing:",
            DATASET_PATH
        )

        return face_samples, ids


    # ========================================================
    # READ STUDENT FOLDERS
    # ========================================================

    folders = sorted(
        os.listdir(
            DATASET_PATH
        )
    )


    for folder in folders:

        folder_path = os.path.join(
            DATASET_PATH,
            folder
        )


        # ----------------------------------------------------
        # Only folders
        # ----------------------------------------------------

        if not os.path.isdir(
            folder_path
        ):

            continue


        # ----------------------------------------------------
        # IMPORTANT
        #
        # Folder name must be database students.id
        #
        # Example:
        #
        # dataset/
        #     12/
        #
        # Here label = 12
        # ----------------------------------------------------

        try:

            label = int(
                folder
            )

        except ValueError:

            print(
                "Skipping invalid dataset folder:",
                folder
            )

            continue


        valid_images = 0


        # ====================================================
        # READ IMAGES
        # ====================================================

        for image_name in sorted(
            os.listdir(
                folder_path
            )
        ):

            image_path = os.path.join(
                folder_path,
                image_name
            )


            if not image_name.lower().endswith(
                (
                    ".jpg",
                    ".jpeg",
                    ".png"
                )
            ):

                continue


            try:

                # --------------------------------------------
                # Read image as grayscale
                # --------------------------------------------

                img = Image.open(
                    image_path
                ).convert("L")


                img_numpy = np.array(
                    img,
                    dtype=np.uint8
                )


                if img_numpy.size == 0:

                    continue


                # --------------------------------------------
                # Resize
                # --------------------------------------------

                img_numpy = cv2.resize(
                    img_numpy,
                    FACE_SIZE,
                    interpolation=cv2.INTER_AREA
                )


                # --------------------------------------------
                # Same histogram preprocessing
                # --------------------------------------------

                img_numpy = cv2.equalizeHist(
                    img_numpy
                )


                # --------------------------------------------
                # Add training image
                # --------------------------------------------

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
        # DATASET INFO
        # ====================================================

        if valid_images > 0:

            print(
                f"Student label {label}: "
                f"{valid_images} images"
            )

        else:

            print(
                f"Student label {label}: "
                "NO VALID IMAGES"
            )


    return face_samples, ids


# ============================================================
# TRAIN FACE MODEL
# ============================================================

def train_faces():

    print()
    print(
        "======================================"
    )
    print(
        "       FACE TRAINING STARTED"
    )
    print(
        "======================================"
    )
    print()


    # ========================================================
    # CHECK OPENCV FACE
    # ========================================================

    if not hasattr(
        cv2,
        "face"
    ):

        print(
            "ERROR: cv2.face is not available."
        )

        print(
            "Install opencv-contrib-python."
        )

        return False


    # ========================================================
    # LOAD DATA
    # ========================================================

    faces, ids = get_images_and_labels()


    # ========================================================
    # NO DATA
    # ========================================================

    if len(faces) == 0:

        print(
            "ERROR: No valid face images found."
        )

        return False


    if len(ids) == 0:

        print(
            "ERROR: No labels found."
        )

        return False


    # ========================================================
    # STUDENTS
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
        "Student database IDs:",
        unique_students
    )
    print()


    # ========================================================
    # CREATE LBPH RECOGNIZER
    # ========================================================

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
        np.array(
            ids,
            dtype=np.int32
        )
    )


    # ========================================================
    # CREATE TRAINER DIRECTORY
    # ========================================================

    os.makedirs(
        TRAINER_DIR,
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
    print(
        "======================================"
    )

    print(
        "       FACE TRAINING COMPLETED"
    )

    print(
        "======================================"
    )

    print(
        "Training Images :",
        len(faces)
    )

    print(
        "Students        :",
        len(unique_students)
    )

    print(
        "Student IDs     :",
        unique_students
    )

    print(
        "Saved Model     :",
        TRAINER_PATH
    )

    print(
        "======================================"
    )

    print()


    return True


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    train_faces()