import cv2
import os
import time


# ============================================================
# FACE CAPTURE / REGISTRATION
# ============================================================

def capture_faces(student_id, total_images=50):

    # ========================================================
    # DATASET FOLDER
    # ========================================================

    dataset_path = "dataset"

    student_folder = os.path.join(
        dataset_path,
        str(student_id)
    )

    os.makedirs(
        student_folder,
        exist_ok=True
    )

    # ========================================================
    # REMOVE OLD IMAGES
    # ========================================================

    for file in os.listdir(student_folder):

        file_path = os.path.join(
            student_folder,
            file
        )

        if os.path.isfile(file_path):

            if file.lower().endswith(
                (".jpg", ".jpeg", ".png")
            ):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(
                        "Could not remove:",
                        file,
                        e
                    )

    # ========================================================
    # LOAD HAAR CASCADE
    # ========================================================

    face_detector = cv2.CascadeClassifier(
        cv2.data.haarcascades +
        "haarcascade_frontalface_default.xml"
    )

    if face_detector.empty():

        raise Exception(
            "Failed to load Haar Cascade."
        )

    # ========================================================
    # OPEN CAMERA
    # ========================================================

    camera = cv2.VideoCapture(0)

    if not camera.isOpened():

        raise Exception(
            "Unable to open camera."
        )

    camera.set(
        cv2.CAP_PROP_FRAME_WIDTH,
        640
    )

    camera.set(
        cv2.CAP_PROP_FRAME_HEIGHT,
        480
    )

    count = 0

    last_capture_time = 0

    capture_delay = 0.30

    try:

        # ====================================================
        # CAMERA LOOP
        # ====================================================

        while True:

            success, frame = camera.read()

            if not success:
                break

            gray = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2GRAY
            )

            # =================================================
            # FACE DETECTION
            # =================================================

            faces = face_detector.detectMultiScale(
                gray,
                scaleFactor=1.2,
                minNeighbors=6,
                minSize=(100, 100)
            )

            # =================================================
            # NO FACE
            # =================================================

            if len(faces) == 0:

                cv2.putText(
                    frame,
                    "Show ONE face to camera",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    (0, 0, 255),
                    2
                )

            # =================================================
            # MORE THAN ONE FACE
            # =================================================

            elif len(faces) > 1:

                cv2.putText(
                    frame,
                    "ONLY ONE FACE ALLOWED",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    (0, 0, 255),
                    2
                )

                cv2.putText(
                    frame,
                    "Other people move away",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 0, 255),
                    2
                )

                # Draw all detected faces
                for (x, y, w, h) in faces:

                    cv2.rectangle(
                        frame,
                        (x, y),
                        (x + w, y + h),
                        (0, 0, 255),
                        2
                    )

            # =================================================
            # EXACTLY ONE FACE
            # =================================================

            else:

                (x, y, w, h) = faces[0]

                # Draw face
                cv2.rectangle(
                    frame,
                    (x, y),
                    (x + w, y + h),
                    (0, 255, 0),
                    2
                )

                # =================================================
                # FACE SIZE CHECK
                # =================================================

                if w < 120 or h < 120:

                    cv2.putText(
                        frame,
                        "Move closer to camera",
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 255),
                        2
                    )

                else:

                    current_time = time.time()

                    # =============================================
                    # CAPTURE WITH DELAY
                    # =============================================

                    if (
                        current_time -
                        last_capture_time
                    ) >= capture_delay:

                        face = gray[
                            y:y + h,
                            x:x + w
                        ]

                        # Resize all images to same size
                        face = cv2.resize(
                            face,
                            (200, 200)
                        )

                        count += 1

                        image_path = os.path.join(
                            student_folder,
                            f"{count}.jpg"
                        )

                        cv2.imwrite(
                            image_path,
                            face
                        )

                        last_capture_time = (
                            current_time
                        )

                    # =============================================
                    # CAPTURE STATUS
                    # =============================================

                    cv2.putText(
                        frame,
                        f"Captured: {count}/{total_images}",
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.75,
                        (0, 255, 0),
                        2
                    )

                    cv2.putText(
                        frame,
                        "Move head slightly",
                        (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 255, 0),
                        2
                    )

                    cv2.putText(
                        frame,
                        "Press Q or ESC to Cancel",
                        (10, 90),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 255, 0),
                        2
                    )

            # =================================================
            # SHOW CAMERA
            # =================================================

            cv2.imshow(
                "AI Smart Attendance - Face Registration",
                frame
            )

            # =================================================
            # KEY
            # =================================================

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q") or key == 27:

                break

            if count >= total_images:

                break

    finally:

        camera.release()

        cv2.destroyAllWindows()

    return count


# ============================================================
# TERMINAL TEST
# ============================================================

if __name__ == "__main__":

    student_id = input(
        "Enter Student Database ID: "
    ).strip()

    print()
    print("==============================")
    print("Starting Face Capture...")
    print("ONLY ONE PERSON IN FRONT OF CAMERA")
    print("==============================")
    print()

    total = capture_faces(
        student_id,
        total_images=50
    )

    print()
    print("==============================")
    print("Face Capture Completed")
    print("Student ID :", student_id)
    print("Images     :", total)
    print("==============================")