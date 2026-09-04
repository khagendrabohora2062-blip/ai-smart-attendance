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

# LBPH distance threshold
MAX_DISTANCE = 65.0


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
# START FACE ATTENDANCE
# Browser Camera Page
# ============================================================

@teacher_face.route(
    "/start/<int:session_id>"
)
def start_face_attendance(session_id):

    # --------------------------------------------------------
    # TEACHER LOGIN CHECK
    # --------------------------------------------------------

    if "teacher_id" not in session:
        return redirect(
            url_for(
                "teacher_auth.login"
            )
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


    # --------------------------------------------------------
    # SESSION NOT FOUND
    # --------------------------------------------------------

    if not attendance_session:

        flash(
            "Attendance session is closed or not found.",
            "danger"
        )

        return redirect(
            url_for(
                "teacher_attendance.index"
            )
        )


    # --------------------------------------------------------
    # SESSION MUST BE OPEN
    # --------------------------------------------------------

    if attendance_session[1] != "OPEN":

        flash(
            "Attendance session is closed.",
            "warning"
        )

        return redirect(
            url_for(
                "teacher_attendance.index"
            )
        )


    # --------------------------------------------------------
    # OPEN BROWSER FACE PAGE
    # --------------------------------------------------------

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
# IMMEDIATE PRESENT
#       ↓
# Attendance
#
# IMPORTANT:
# No 3-confirmation system.
# First valid recognition = Present.
#
# Scanner remains active for next student.
# ============================================================

@teacher_face.route(
    "/recognize",
    methods=["POST"]
)
def recognize_browser_face():

    # ========================================================
    # TEACHER LOGIN CHECK
    # ========================================================

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

    session_id = None


    try:

        # ====================================================
        # GET SESSION ID
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


        # ====================================================
        # CONVERT SESSION ID TO INTEGER
        # ====================================================

        try:

            session_id = int(
                session_id
            )

        except (
            TypeError,
            ValueError
        ):

            return jsonify({
                "success": False,
                "name": "",
                "student_id": "",
                "confidence": 0,
                "distance": 0,
                "status": "Invalid Session ID"
            }), 400


        # ====================================================
        # GET IMAGE
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


        # ====================================================
        # SESSION NOT FOUND
        # ====================================================

        if not attendance_session:

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

        trainer_path = TRAINER_PATH


        # ----------------------------------------------------
        # FALLBACK PATH
        # ----------------------------------------------------

        if not os.path.isfile(
            trainer_path
        ):

            alternate_path = os.path.join(
                current_app.root_path,
                "trainer",
                "trainer.yml"
            )

            if os.path.isfile(
                alternate_path
            ):

                trainer_path = alternate_path


        # ====================================================
        # CHECK TRAINER FILE
        # ====================================================

        if not os.path.isfile(
            trainer_path
        ):

            return jsonify({
                "success": False,
                "name": "",
                "student_id": "",
                "confidence": 0,
                "distance": 0,
                "status":
                    "trainer.yml not found. "
                    "Please train the face model and "
                    "make sure trainer/trainer.yml "
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
        # OPENCV FACE MODULE CHECK
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


        # ====================================================
        # FACE TOO SMALL
        # ====================================================

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
        # FACE MARGIN
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


        # ====================================================
        # CROP FACE
        # ====================================================

        face_image = gray[
            y1:y2,
            x1:x2
        ]


        if face_image.size == 0:

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
        # HISTOGRAM EQUALIZATION
        # ====================================================

        face_image = cv2.equalizeHist(
            face_image
        )


        # ====================================================
        # CREATE LBPH RECOGNIZER
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
        # LOAD TRAINER
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
        # PREDICT FACE
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


        label = int(
            label
        )

        distance = float(
            distance
        )


        # ====================================================
        # CONFIDENCE
        # ====================================================

        confidence = max(
            0.0,
            min(
                100.0,
                100.0 - distance
            )
        )


        # ====================================================
        # UNKNOWN FACE
        # ====================================================

        if (
            label <= 0
            or
            distance > MAX_DISTANCE
        ):

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
        #
        # IMPORTANT:
        # Model label = students.id
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


        # ====================================================
        # STUDENT DATA
        # ====================================================

        student_db_id = int(
            student[0]
        )

        student_code = str(
            student[1]
        )

        student_name_value = (
            student[2]
            or
            "Unknown Student"
        )


        # ====================================================
        # DUPLICATE CHECK
        #
        # Same student + same attendance session
        # cannot be marked twice.
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


        # ====================================================
        # ALREADY MARKED
        #
        # IMPORTANT:
        # Scanner does NOT stop.
        # ====================================================

        if already_marked:

            return jsonify({
                "success": False,
                "name": student_name_value,
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
        # SAVE ATTENDANCE
        #
        # NO 3-CONFIRMATION SYSTEM.
        #
        # First valid recognition = Present.
        # ====================================================

        cursor = mysql.connection.cursor()

        try:

            # ------------------------------------------------
            # FINAL DUPLICATE CHECK
            # ------------------------------------------------

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


            # ------------------------------------------------
            # IF DUPLICATE
            # ------------------------------------------------

            if duplicate:

                result = "Already Marked"


            # ------------------------------------------------
            # INSERT ATTENDANCE
            # ------------------------------------------------

            else:

                # --------------------------------------------
                # GET NEXT ID
                # --------------------------------------------

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


                # --------------------------------------------
                # INSERT PRESENT
                # --------------------------------------------

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


                # --------------------------------------------
                # COMMIT
                # --------------------------------------------

                mysql.connection.commit()

                result = "Present"


        except Exception:

            mysql.connection.rollback()

            raise

        finally:

            cursor.close()


        # ====================================================
        # FINAL RESPONSE
        #
        # Camera remains active because frontend should
        # continue scanning after this response.
        # ====================================================

        return jsonify({
            "success":
                result == "Present",

            "name":
                student_name_value,

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


    # ========================================================
    # GLOBAL ERROR
    # ========================================================

    except Exception as e:

        current_app.logger.exception(
            "Browser Face Recognition Error"
        )

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