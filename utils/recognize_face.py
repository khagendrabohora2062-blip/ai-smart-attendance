import sys
import os
import cv2
import time

sys.path.append(
    os.path.dirname(
        os.path.dirname(__file__)
    )
)

from extensions import mysql


# ============================================================
# TRAINER PATH
# ============================================================

TRAINER_PATH = "trainer/trainer.yml"


# ============================================================
# RECOGNITION SETTINGS
# ============================================================

# LBPH distance:
# LOWER = BETTER MATCH

MAX_DISTANCE = 45.0

# Same student should be recognized several times
# before attendance is marked.

REQUIRED_CONFIRMATIONS = 3

# Maximum time allowed between confirmations.

CONFIRMATION_TIMEOUT = 3.0


# ============================================================
# GET STUDENT DETAILS
# ============================================================

def get_student(student_db_id):

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                id,
                student_id,
                full_name,
                department
            FROM students
            WHERE id=%s
            LIMIT 1
            """,
            (
                student_db_id,
            )
        )

        return cursor.fetchone()

    finally:

        cursor.close()


# ============================================================
# SAVE FACE ATTENDANCE
# ============================================================

def save_face_attendance(
    student_db_id,
    session_id
):

    cursor = mysql.connection.cursor()

    try:

        # ====================================================
        # CHECK SESSION
        # ====================================================

        cursor.execute(
            """
            SELECT
                id,
                session_status
            FROM attendance_sessions
            WHERE id=%s
            LIMIT 1
            """,
            (
                session_id,
            )
        )

        attendance_session = cursor.fetchone()

        if not attendance_session:

            return (
                False,
                "Session not found"
            )

        db_session_id = attendance_session[0]

        session_status = attendance_session[1]

        # ====================================================
        # SESSION MUST BE OPEN
        # ====================================================

        if session_status != "OPEN":

            return (
                False,
                "Session Closed"
            )

        # ====================================================
        # DUPLICATE CHECK
        # ====================================================

        cursor.execute(
            """
            SELECT
                id
            FROM attendance
            WHERE student_id=%s
            AND session_id=%s
            LIMIT 1
            """,
            (
                student_db_id,
                db_session_id
            )
        )

        duplicate = cursor.fetchone()

        if duplicate:

            return (
                False,
                "Already Marked"
            )

        # ====================================================
        # GENERATE NEXT ATTENDANCE ID
        # ====================================================

        cursor.execute(
            """
            SELECT
                COALESCE(MAX(id), 0) + 1
            FROM attendance
            """
        )

        next_id_result = cursor.fetchone()

        next_attendance_id = (
            next_id_result[0]
        )

        # ====================================================
        # INSERT ATTENDANCE
        # ====================================================

        cursor.execute(
            """
            INSERT INTO attendance
            (
                id,
                student_id,
                session_id,
                attendance_date,
                attendance_time,
                attendance_method,
                status,
                remarks
            )
            VALUES
            (
                %s,
                %s,
                %s,
                CURDATE(),
                CURTIME(),
                'FACE',
                'Present',
                %s
            )
            """,
            (
                next_attendance_id,
                student_db_id,
                db_session_id,
                "Attendance marked using face recognition"
            )
        )

        mysql.connection.commit()

        print(
            "======================================"
        )

        print(
            "FACE ATTENDANCE SAVED"
        )

        print(
            f"Attendance ID : {next_attendance_id}"
        )

        print(
            f"Student DB ID : {student_db_id}"
        )

        print(
            f"Session ID    : {db_session_id}"
        )

        print(
            "Status        : Present"
        )

        print(
            "Method        : FACE"
        )

        print(
            "======================================"
        )

        return (
            True,
            "Present"
        )

    except Exception as e:

        mysql.connection.rollback()

        print(
            "Attendance Save Error:",
            str(e)
        )

        return (
            False,
            str(e)
        )

    finally:

        cursor.close()


# ============================================================
# FACE RECOGNITION
# ============================================================

def recognize_face(session_id):

    # ========================================================
    # VERIFY SESSION
    # ========================================================

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                attendance_sessions.id,
                attendance_sessions.start_time,
                attendance_sessions.end_time,
                attendance_sessions.session_status,
                subjects.subject_name,
                teachers.full_name
            FROM attendance_sessions

            INNER JOIN subjects
                ON attendance_sessions.subject_id =
                   subjects.id

            INNER JOIN teachers
                ON attendance_sessions.teacher_id =
                   teachers.id

            WHERE attendance_sessions.id=%s
            LIMIT 1
            """,
            (
                session_id,
            )
        )

        session_data = cursor.fetchone()

    finally:

        cursor.close()

    # ========================================================
    # SESSION NOT FOUND
    # ========================================================

    if not session_data:

        raise Exception(
            "Attendance session not found."
        )

    db_session_id = session_data[0]

    session_start_time = session_data[1]

    session_end_time = session_data[2]

    session_status = session_data[3]

    subject_name = session_data[4]

    teacher_name = session_data[5]

    # ========================================================
    # SESSION MUST BE OPEN
    # ========================================================

    if session_status != "OPEN":

        raise Exception(
            "Attendance session is closed."
        )

    # ========================================================
    # CHECK TRAINER
    # ========================================================

    if not os.path.exists(
        TRAINER_PATH
    ):

        raise Exception(
            "trainer.yml not found. "
            "Please train the face model first."
        )

    # ========================================================
    # CHECK OPENCV FACE
    # ========================================================

    if not hasattr(cv2, "face"):

        raise Exception(
            "OpenCV face module is not available. "
            "Install opencv-contrib-python."
        )

    # ========================================================
    # LOAD TRAINER
    # ========================================================

    recognizer = (
        cv2.face.LBPHFaceRecognizer_create(
            radius=1,
            neighbors=8,
            grid_x=8,
            grid_y=8
        )
    )

    recognizer.read(
        TRAINER_PATH
    )

    # ========================================================
    # FACE DETECTOR
    # ========================================================

    face_detector = cv2.CascadeClassifier(
        cv2.data.haarcascades +
        "haarcascade_frontalface_default.xml"
    )

    if face_detector.empty():

        raise Exception(
            "Haar Cascade could not be loaded."
        )

    # ========================================================
    # CAMERA
    # ========================================================

    camera = cv2.VideoCapture(0)

    if not camera.isOpened():

        raise Exception(
            "Camera not found."
        )

    camera.set(
        cv2.CAP_PROP_FRAME_WIDTH,
        640
    )

    camera.set(
        cv2.CAP_PROP_FRAME_HEIGHT,
        480
    )

    font = cv2.FONT_HERSHEY_SIMPLEX

    # ========================================================
    # STUDENTS MARKED DURING THIS CAMERA SESSION
    # ========================================================

    marked_students = set()

    # ========================================================
    # CONFIRMATION TRACKING
    # ========================================================

    candidate_student = None

    candidate_count = 0

    candidate_last_time = 0

    # ========================================================
    # CAMERA LOOP
    # ========================================================

    try:

        while True:

            success, frame = camera.read()

            if not success:

                break

            # =================================================
            # GRAYSCALE
            # =================================================

            gray = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2GRAY
            )

            # =================================================
            # FACE DETECTION
            # =================================================

            faces = face_detector.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=7,
                minSize=(120, 120)
            )

            # =================================================
            # HEADER
            # =================================================

            cv2.putText(
                frame,
                f"Subject: {subject_name}",
                (10, 30),
                font,
                0.65,
                (255, 255, 0),
                2
            )

            cv2.putText(
                frame,
                f"Teacher: {teacher_name}",
                (10, 60),
                font,
                0.65,
                (255, 255, 0),
                2
            )

            cv2.putText(
                frame,
                f"Start: {session_start_time}",
                (10, 90),
                font,
                0.6,
                (255, 255, 0),
                2
            )

            cv2.putText(
                frame,
                "Press Q to Exit",
                (10, frame.shape[0] - 20),
                font,
                0.6,
                (255, 255, 255),
                2
            )

            # =================================================
            # NO FACE
            # =================================================

            if len(faces) == 0:

                candidate_student = None

                candidate_count = 0

                cv2.putText(
                    frame,
                    "No face detected",
                    (10, 125),
                    font,
                    0.65,
                    (0, 0, 255),
                    2
                )

            # =================================================
            # MULTIPLE FACES
            # =================================================

            elif len(faces) > 1:

                candidate_student = None

                candidate_count = 0

                for (
                    x,
                    y,
                    w,
                    h
                ) in faces:

                    cv2.rectangle(
                        frame,
                        (x, y),
                        (x + w, y + h),
                        (0, 0, 255),
                        2
                    )

                    cv2.putText(
                        frame,
                        "Multiple Faces",
                        (x, y - 10),
                        font,
                        0.6,
                        (0, 0, 255),
                        2
                    )

                cv2.putText(
                    frame,
                    "ONLY ONE PERSON AT A TIME",
                    (10, 125),
                    font,
                    0.65,
                    (0, 0, 255),
                    2
                )

            # =================================================
            # EXACTLY ONE FACE
            # =================================================

            else:

                (
                    x,
                    y,
                    w,
                    h
                ) = faces[0]

                # =============================================
                # FACE IMAGE
                # =============================================

                face_image = gray[
                    y:y + h,
                    x:x + w
                ]

                face_image = cv2.resize(
                    face_image,
                    (200, 200)
                )

                # =============================================
                # PREDICT
                # =============================================

                label, distance = (
                    recognizer.predict(
                        face_image
                    )
                )

                # =============================================
                # STRICT MATCH
                # =============================================

                if distance <= MAX_DISTANCE:

                    student = get_student(
                        label
                    )

                    # =========================================
                    # STUDENT FOUND
                    # =========================================

                    if student:

                        db_id = student[0]

                        student_code = student[1]

                        name = student[2]

                        department = student[3]

                        # =====================================
                        # CONFIRMATION
                        # =====================================

                        current_time = time.time()

                        if (
                            candidate_student
                            == db_id
                            and
                            (
                                current_time -
                                candidate_last_time
                            )
                            <= CONFIRMATION_TIMEOUT
                        ):

                            candidate_count += 1

                        else:

                            candidate_student = db_id

                            candidate_count = 1

                        candidate_last_time = (
                            current_time
                        )

                        # =====================================
                        # STATUS
                        # =====================================

                        if db_id in marked_students:

                            status = "Already Marked"

                        else:

                            status = (
                                f"Confirming "
                                f"{candidate_count}/"
                                f"{REQUIRED_CONFIRMATIONS}"
                            )

                        # =====================================
                        # MARK ATTENDANCE
                        # =====================================

                        if (
                            candidate_count
                            >=
                            REQUIRED_CONFIRMATIONS
                            and
                            db_id
                            not in
                            marked_students
                        ):

                            saved, result = (
                                save_face_attendance(
                                    db_id,
                                    db_session_id
                                )
                            )

                            if saved:

                                status = "Present"

                                marked_students.add(
                                    db_id
                                )

                                candidate_student = None

                                candidate_count = 0

                            else:

                                status = result

                                if (
                                    result
                                    ==
                                    "Already Marked"
                                ):

                                    marked_students.add(
                                        db_id
                                    )

                        # =====================================
                        # COLOR
                        # =====================================

                        if status == "Present":

                            color = (
                                0,
                                255,
                                0
                            )

                        elif status == "Already Marked":

                            color = (
                                255,
                                255,
                                0
                            )

                        else:

                            color = (
                                0,
                                255,
                                255
                            )

                        # =====================================
                        # FACE BOX
                        # =====================================

                        cv2.rectangle(
                            frame,
                            (x, y),
                            (x + w, y + h),
                            color,
                            2
                        )

                        # =====================================
                        # NAME
                        # =====================================

                        cv2.putText(
                            frame,
                            name,
                            (x, y - 60),
                            font,
                            0.7,
                            color,
                            2
                        )

                        # =====================================
                        # STUDENT ID
                        # =====================================

                        cv2.putText(
                            frame,
                            f"ID: {student_code}",
                            (x, y - 35),
                            font,
                            0.6,
                            color,
                            2
                        )

                        # =====================================
                        # DEPARTMENT
                        # =====================================

                        cv2.putText(
                            frame,
                            department or "",
                            (x, y - 10),
                            font,
                            0.5,
                            color,
                            2
                        )

                        # =====================================
                        # STATUS
                        # =====================================

                        cv2.putText(
                            frame,
                            status,
                            (x, y + h + 25),
                            font,
                            0.6,
                            color,
                            2
                        )

                        # =====================================
                        # DISTANCE
                        # =====================================

                        cv2.putText(
                            frame,
                            f"Match Distance: {distance:.1f}",
                            (x, y + h + 50),
                            font,
                            0.5,
                            color,
                            1
                        )

                    # =========================================
                    # LABEL DOES NOT EXIST IN DATABASE
                    # =========================================

                    else:

                        candidate_student = None

                        candidate_count = 0

                        color = (
                            0,
                            0,
                            255
                        )

                        cv2.rectangle(
                            frame,
                            (x, y),
                            (x + w, y + h),
                            color,
                            2
                        )

                        cv2.putText(
                            frame,
                            "Unknown Student",
                            (x, y - 10),
                            font,
                            0.7,
                            color,
                            2
                        )

                # =============================================
                # DISTANCE TOO HIGH
                # =============================================

                else:

                    candidate_student = None

                    candidate_count = 0

                    color = (
                        0,
                        0,
                        255
                    )

                    cv2.rectangle(
                        frame,
                        (x, y),
                        (x + w, y + h),
                        color,
                        2
                    )

                    cv2.putText(
                        frame,
                        "UNKNOWN",
                        (x, y - 10),
                        font,
                        0.8,
                        color,
                        2
                    )

                    cv2.putText(
                        frame,
                        f"Distance: {distance:.1f}",
                        (x, y + h + 25),
                        font,
                        0.5,
                        color,
                        1
                    )

            # =================================================
            # SHOW CAMERA
            # =================================================

            cv2.imshow(
                "AI Face Attendance",
                frame
            )

            # =================================================
            # KEY
            # =================================================

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q") or key == 27:

                break

    finally:

        camera.release()

        cv2.destroyAllWindows()


# ============================================================
# TERMINAL TEST
# ============================================================

if __name__ == "__main__":

    from app import create_app

    app = create_app()

    with app.app_context():

        recognize_face(1)