from flask import (
    Blueprint,
    session,
    redirect,
    url_for,
    flash,
    render_template,
    request,
    jsonify,
    current_app
)

import os
import time
import cv2
import numpy as np

from extensions import mysql


# ============================================================
# TEACHER FACE BLUEPRINT
# ============================================================

teacher_face = Blueprint(
    "teacher_face",
    __name__,
    url_prefix="/teacher/face"
)


# ============================================================
# FACE SETTINGS
# ============================================================

FACE_SIZE = (200, 200)

FACE_MARGIN = 0.15

MAX_DISTANCE = 65.0

REQUIRED_CONFIRMATIONS = 3

CONFIRMATION_TIMEOUT = 3.0


# ============================================================
# BASE / TRAINER PATH
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
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
# CLEAR CONFIRMATION
# ============================================================

def clear_face_confirmation(session_id):

    session.pop(
        f"face_candidate_{session_id}",
        None
    )

    session.pop(
        f"face_count_{session_id}",
        None
    )

    session.pop(
        f"face_time_{session_id}",
        None
    )

    session.modified = True


# ============================================================
# START FACE ATTENDANCE
# Browser Camera Page
# ============================================================

@teacher_face.route(
    "/start/<int:session_id>"
)
def start_face_attendance(session_id):

    if "teacher_id" not in session:

        return redirect(
            url_for("teacher_auth.login")
        )


    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                id,
                session_status
            FROM attendance_sessions
            WHERE id=%s
            AND teacher_id=%s
            LIMIT 1
            """,
            (
                session_id,
                session["teacher_id"]
            )
        )

        attendance_session = cursor.fetchone()

    finally:

        cursor.close()


    if not attendance_session:

        flash(
            "Attendance session is closed or not found.",
            "danger"
        )

        return redirect(
            url_for("teacher_attendance.index")
        )


    if attendance_session[1] != "OPEN":

        flash(
            "Attendance session is closed.",
            "warning"
        )

        return redirect(
            url_for("teacher_attendance.index")
        )


    return render_template(
        "teacher/browser_face.html",
        session_id=session_id
    )


# ============================================================
# BROWSER FACE RECOGNITION API
#
# Browser Camera
#       ↓
# JavaScript
#       ↓
# JPEG
#       ↓
# Flask
#       ↓
# OpenCV
#       ↓
# trainer.yml
#       ↓
# Student
#       ↓
# Attendance
# ============================================================

@teacher_face.route(
    "/recognize",
    methods=["POST"]
)
def recognize_browser_face():

    if "teacher_id" not in session:

        return jsonify({
            "success": False,
            "name": "",
            "student_id": "",
            "confidence": 0,
            "distance": 0,
            "status": "Unauthorized"
        }), 401


    teacher_id = session["teacher_id"]


    try:

        # ====================================================
        # SESSION ID
        # ====================================================

        session_id = request.form.get(
            "session_id"
        )


        if not session_id:

            return jsonify({
                "success": False,
                "name": "",
                "student_id": "",
                "confidence": 0,
                "distance": 0,
                "status": "Session ID missing"
            }), 400


        try:

            session_id = int(
                session_id
            )

        except (TypeError, ValueError):

            return jsonify({
                "success": False,
                "name": "",
                "student_id": "",
                "confidence": 0,
                "distance": 0,
                "status": "Invalid Session ID"
            }), 400


        # ====================================================
        # IMAGE
        # ====================================================

        image_file = request.files.get(
            "image"
        )


        if image_file is None:

            return jsonify({
                "success": False,
                "name": "",
                "student_id": "",
                "confidence": 0,
                "distance": 0,
                "status": "Image missing"
            }), 400


        image_bytes = image_file.read()


        if not image_bytes:

            return jsonify({
                "success": False,
                "name": "",
                "student_id": "",
                "confidence": 0,
                "distance": 0,
                "status": "Empty image"
            }), 400


        # ====================================================
        # VERIFY ATTENDANCE SESSION
        # ====================================================

        cursor = mysql.connection.cursor()

        try:

            cursor.execute(
                """
                SELECT
                    s.id,
                    s.session_status,
                    s.teacher_id,
                    sub.subject_name
                FROM attendance_sessions s
                LEFT JOIN subjects sub
                    ON s.subject_id = sub.id
                WHERE s.id=%s
                AND s.teacher_id=%s
                LIMIT 1
                """,
                (
                    session_id,
                    teacher_id
                )
            )

            attendance_session = cursor.fetchone()

        finally:

            cursor.close()


        if not attendance_session:

            clear_face_confirmation(
                session_id
            )

            return jsonify({
                "success": False,
                "name": "",
                "student_id": "",
                "confidence": 0,
                "distance": 0,
                "status":
                    "Attendance session not found"
            })


        # ====================================================
        # SESSION MUST BE OPEN
        # ====================================================

        if attendance_session[1] != "OPEN":

            clear_face_confirmation(
                session_id
            )

            return jsonify({
                "success": False,
                "name": "",
                "student_id": "",
                "confidence": 0,
                "distance": 0,
                "status": "Session Closed"
            })


        # ====================================================
        # TRAINER PATH
        # ====================================================

        trainer_path = os.path.join(
            current_app.root_path,
            "trainer",
            "trainer.yml"
        )


        # Fallback to absolute project path

        if not os.path.isfile(
            trainer_path
        ):

            trainer_path = TRAINER_PATH


        # ====================================================
        # CHECK TRAINER
        # ====================================================

        if not os.path.isfile(
            trainer_path
        ):

            clear_face_confirmation(
                session_id
            )

            return jsonify({
                "success": False,
                "name": "",
                "student_id": "",
                "confidence": 0,
                "distance": 0,
                "status":
                    "trainer.yml not found at "
                    + trainer_path
                    + ". Please train the face model "
                      "and make sure trainer/trainer.yml "
                      "is deployed."
            })


        # ====================================================
        # CHECK EMPTY TRAINER
        # ====================================================

        if os.path.getsize(
            trainer_path
        ) <= 0:

            return jsonify({
                "success": False,
                "name": "",
                "student_id": "",
                "confidence": 0,
                "distance": 0,
                "status":
                    "trainer.yml is empty. "
                    "Please train the face model again."
            })


        # ====================================================
        # OPENCV FACE MODULE
        # ====================================================

        if not hasattr(
            cv2,
            "face"
        ):

            return jsonify({
                "success": False,
                "name": "",
                "student_id": "",
                "confidence": 0,
                "distance": 0,
                "status":
                    "OpenCV face module unavailable. "
                    "Install opencv-contrib-python."
            })


        # ====================================================
        # DECODE BROWSER IMAGE
        # ====================================================

        np_array = np.frombuffer(
            image_bytes,
            dtype=np.uint8
        )


        frame = cv2.imdecode(
            np_array,
            cv2.IMREAD_COLOR
        )


        if frame is None:

            return jsonify({
                "success": False,
                "name": "",
                "student_id": "",
                "confidence": 0,
                "distance": 0,
                "status": "Invalid image"
            })


        # ====================================================
        # GRAYSCALE
        # ====================================================

        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )


        # ====================================================
        # FACE DETECTOR
        # ====================================================

        cascade_path = (
            cv2.data.haarcascades
            +
            "haarcascade_frontalface_default.xml"
        )


        face_detector = cv2.CascadeClassifier(
            cascade_path
        )


        if face_detector.empty():

            return jsonify({
                "success": False,
                "name": "",
                "student_id": "",
                "confidence": 0,
                "distance": 0,
                "status":
                    "Face detector unavailable"
            })


        # ====================================================
        # DETECT FACE
        # ====================================================

        faces = face_detector.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(100, 100)
        )


        # ====================================================
        # NO FACE
        # ====================================================

        if len(faces) == 0:

            clear_face_confirmation(
                session_id
            )

            return jsonify({
                "success": False,
                "name": "",
                "student_id": "",
                "confidence": 0,
                "distance": 0,
                "status": "No face detected"
            })


        # ====================================================
        # MULTIPLE FACES
        # ====================================================

        if len(faces) > 1:

            clear_face_confirmation(
                session_id
            )

            return jsonify({
                "success": False,
                "name": "",
                "student_id": "",
                "confidence": 0,
                "distance": 0,
                "status":
                    "Multiple faces detected"
            })


        # ====================================================
        # FACE COORDINATES
        # ====================================================

        x, y, w, h = faces[0]


        if w < 100 or h < 100:

            return jsonify({
                "success": False,
                "name": "",
                "student_id": "",
                "confidence": 0,
                "distance": 0,
                "status":
                    "Face too small. "
                    "Move closer to camera."
            })


        # ====================================================
        # SAME CROP AS CAPTURE
        # ====================================================

        margin = int(
            min(w, h)
            *
            FACE_MARGIN
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


        face_image = gray[
            y1:y2,
            x1:x2
        ]


        if face_image.size == 0:

            clear_face_confirmation(
                session_id
            )

            return jsonify({
                "success": False,
                "name": "",
                "student_id": "",
                "confidence": 0,
                "distance": 0,
                "status":
                    "Unable to crop face"
            })


        # ====================================================
        # RESIZE
        # ====================================================

        face_image = cv2.resize(
            face_image,
            FACE_SIZE,
            interpolation=cv2.INTER_AREA
        )


        # ====================================================
        # EQUALIZE
        # ====================================================

        face_image = cv2.equalizeHist(
            face_image
        )


        # ====================================================
        # CREATE RECOGNIZER
        # ====================================================

        recognizer = (
            cv2.face.LBPHFaceRecognizer_create(
                radius=1,
                neighbors=8,
                grid_x=8,
                grid_y=8
            )
        )


        # ====================================================
        # LOAD MODEL
        # ====================================================

        try:

            recognizer.read(
                trainer_path
            )

        except Exception as e:

            current_app.logger.exception(
                "Unable to load trainer.yml"
            )

            return jsonify({
                "success": False,
                "name": "",
                "student_id": "",
                "confidence": 0,
                "distance": 0,
                "status":
                    "Model load error: "
                    + str(e)
            }), 500


        # ====================================================
        # PREDICT
        # ====================================================

        try:

            label, distance = (
                recognizer.predict(
                    face_image
                )
            )

        except Exception as e:

            current_app.logger.exception(
                "Face prediction error"
            )

            return jsonify({
                "success": False,
                "name": "",
                "student_id": "",
                "confidence": 0,
                "distance": 0,
                "status":
                    "Prediction error: "
                    + str(e)
            }), 500


        label = int(label)

        distance = float(distance)


        # ====================================================
        # DISPLAY CONFIDENCE
        # ====================================================

        confidence = max(
            0.0,
            min(
                100.0,
                100.0 - distance
            )
        )


        # ====================================================
        # UNKNOWN
        # ====================================================

        if (
            label <= 0
            or
            distance > MAX_DISTANCE
        ):

            clear_face_confirmation(
                session_id
            )

            return jsonify({
                "success": False,
                "name": "Unknown Student",
                "student_id": "",
                "confidence": round(
                    confidence,
                    1
                ),
                "distance": round(
                    distance,
                    2
                ),
                "status":
                    "Unknown Face"
            })


        # ====================================================
        # FIND STUDENT
        # MODEL LABEL = students.id
        # ====================================================

        cursor = mysql.connection.cursor()

        try:

            cursor.execute(
                """
                SELECT
                    id,
                    student_id,
                    full_name,
                    semester,
                    department
                FROM students
                WHERE id=%s
                LIMIT 1
                """,
                (
                    label,
                )
            )

            student = cursor.fetchone()

        finally:

            cursor.close()


        # ====================================================
        # STUDENT NOT FOUND
        # ====================================================

        if not student:

            clear_face_confirmation(
                session_id
            )

            return jsonify({
                "success": False,
                "name": "Unknown Student",
                "student_id": "",
                "confidence": round(
                    confidence,
                    1
                ),
                "distance": round(
                    distance,
                    2
                ),
                "status":
                    "Face recognized but "
                    "student record not found"
            })


        student_db_id = int(
            student[0]
        )

        student_code = str(
            student[1]
        )

        student_name = (
            student[2]
            or
            "Unknown Student"
        )


        # ====================================================
        # DUPLICATE CHECK
        # ====================================================

        cursor = mysql.connection.cursor()

        try:

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
                    session_id
                )
            )

            already_marked = cursor.fetchone()

        finally:

            cursor.close()


        if already_marked:

            clear_face_confirmation(
                session_id
            )

            return jsonify({
                "success": False,
                "name": student_name,
                "student_id": student_code,
                "confidence": round(
                    confidence,
                    1
                ),
                "distance": round(
                    distance,
                    2
                ),
                "status":
                    "Already Marked"
            })


        # ====================================================
        # CONFIRMATION
        # ====================================================

        candidate_key = (
            f"face_candidate_{session_id}"
        )

        count_key = (
            f"face_count_{session_id}"
        )

        time_key = (
            f"face_time_{session_id}"
        )


        old_candidate = session.get(
            candidate_key
        )

        old_count = session.get(
            count_key,
            0
        )

        old_time = session.get(
            time_key,
            0
        )


        current_time = time.time()


        if (
            old_candidate == student_db_id
            and
            current_time - old_time
            <= CONFIRMATION_TIMEOUT
        ):

            count = old_count + 1

        else:

            count = 1


        session[candidate_key] = (
            student_db_id
        )

        session[count_key] = (
            count
        )

        session[time_key] = (
            current_time
        )

        session.modified = True


        # ====================================================
        # NOT YET CONFIRMED
        # ====================================================

        if count < REQUIRED_CONFIRMATIONS:

            return jsonify({
                "success": False,
                "name": student_name,
                "student_id": student_code,
                "confidence": round(
                    confidence,
                    1
                ),
                "distance": round(
                    distance,
                    2
                ),
                "status":
                    f"Confirming "
                    f"{count}/"
                    f"{REQUIRED_CONFIRMATIONS}"
            })


        # ====================================================
        # SAVE ATTENDANCE
        # ====================================================

        cursor = mysql.connection.cursor()

        try:

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
                    session_id
                )
            )

            duplicate = cursor.fetchone()


            if duplicate:

                result = "Already Marked"

            else:

                cursor.execute(
                    """
                    SELECT
                        COALESCE(
                            MAX(id),
                            0
                        ) + 1
                    FROM attendance
                    """
                )

                next_id = (
                    cursor.fetchone()[0]
                )


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
                        next_id,
                        student_db_id,
                        session_id,
                        "Attendance marked using browser face recognition"
                    )
                )


                mysql.connection.commit()

                result = "Present"


        except Exception:

            mysql.connection.rollback()

            raise

        finally:

            cursor.close()


        # ====================================================
        # CLEAR CONFIRMATION
        # ====================================================

        clear_face_confirmation(
            session_id
        )


        # ====================================================
        # RESPONSE
        # ====================================================

        return jsonify({
            "success":
                result == "Present",

            "name":
                student_name,

            "student_id":
                student_code,

            "confidence":
                round(
                    confidence,
                    1
                ),

            "distance":
                round(
                    distance,
                    2
                ),

            "status":
                result
        })


    except Exception as e:

        current_app.logger.exception(
            "Browser Face Recognition Error"
        )


        try:

            if "session_id" in locals():

                clear_face_confirmation(
                    session_id
                )

        except Exception:

            pass


        return jsonify({
            "success": False,
            "name": "",
            "student_id": "",
            "confidence": 0,
            "distance": 0,
            "status":
                "Face Error: "
                + str(e)
        }), 500