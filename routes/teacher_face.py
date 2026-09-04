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

# LBPH distance:
# LOWER = BETTER MATCH
#
# 65 is a reasonable starting point.
# If false matches happen, reduce to 55-60.
# If your own face still becomes Unknown, test 70.
MAX_DISTANCE = 65.0

REQUIRED_CONFIRMATIONS = 3

CONFIRMATION_TIMEOUT = 3.0

FACE_SIZE = (200, 200)

FACE_MARGIN = 0.15


# ============================================================
# CLEAR FACE CONFIRMATION
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

        cursor.execute("""
            SELECT
                id,
                session_status
            FROM attendance_sessions
            WHERE id=%s
            AND teacher_id=%s
            LIMIT 1
        """, (
            session_id,
            session["teacher_id"]
        ))

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
# FACE RECOGNITION API
# Browser Camera -> Flask -> OpenCV
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

            cursor.execute("""
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
            """, (
                session_id,
                teacher_id
            ))

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


        if not os.path.exists(
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
                    "trainer.yml not found. "
                    "Please train the face model first."
            })


        # ====================================================
        # CHECK OPENCV FACE MODULE
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
        # HISTOGRAM EQUALIZATION
        #
        # IMPORTANT:
        #
        # Training and recognition now use
        # the same preprocessing.
        # ====================================================

        gray = cv2.equalizeHist(
            gray
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
        #
        # Slightly more tolerant than old settings.
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
        # SELECT FACE
        # ====================================================

        x, y, w, h = faces[0]


        # ====================================================
        # FACE SIZE VALIDATION
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
        # ADD SAME MARGIN USED DURING TRAINING
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
        # FINAL HISTOGRAM EQUALIZATION
        # ====================================================

        face_image = cv2.equalizeHist(
            face_image
        )


        # ====================================================
        # LOAD LBPH MODEL
        # ====================================================

        recognizer = (
            cv2.face.LBPHFaceRecognizer_create(
                radius=1,
                neighbors=8,
                grid_x=8,
                grid_y=8
            )
        )


        try:

            recognizer.read(
                trainer_path
            )

        except Exception as model_error:

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
                    f"Model load error: "
                    f"{str(model_error)}"
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

        except Exception as predict_error:

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
                    f"Prediction error: "
                    f"{str(predict_error)}"
            }), 500


        # ====================================================
        # NORMALIZE VALUES
        # ====================================================

        try:

            label = int(
                label
            )

        except Exception:

            label = 0


        try:

            distance = float(
                distance
            )

        except Exception:

            distance = 999.0


        # ====================================================
        # CONFIDENCE
        #
        # This is only a display score.
        # LBPH distance itself is the actual criterion.
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
        # GET STUDENT USING DATABASE PRIMARY KEY
        #
        # IMPORTANT:
        #
        # The trained model label MUST be students.id
        #
        # Example:
        #
        # students.id       = 7
        # students.student_id = 24001
        #
        # Model label = 7
        #
        # Then this query finds student 24001.
        # ====================================================

        cursor = mysql.connection.cursor()

        try:

            cursor.execute("""
                SELECT
                    id,
                    student_id,
                    full_name,
                    semester,
                    department
                FROM students
                WHERE id=%s
                LIMIT 1
            """, (
                label,
            ))

            student = cursor.fetchone()

        finally:

            cursor.close()


        # ====================================================
        # MODEL LABEL DOES NOT EXIST IN DATABASE
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


        # ====================================================
        # STUDENT DATA
        # ====================================================

        student_db_id = int(
            student[0]
        )

        student_code = str(
            student[1]
        )

        student_name = (
            student[2]
            if student[2]
            else "Unknown Student"
        )


        # ====================================================
        # DUPLICATE ATTENDANCE CHECK
        # ====================================================

        cursor = mysql.connection.cursor()

        try:

            cursor.execute("""
                SELECT id
                FROM attendance
                WHERE student_id=%s
                AND session_id=%s
                LIMIT 1
            """, (
                student_db_id,
                session_id
            ))

            already_marked = (
                cursor.fetchone()
            )

        finally:

            cursor.close()


        # ====================================================
        # ALREADY MARKED
        # ====================================================

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
                "status": "Already Marked"
            })


        # ====================================================
        # CONFIRMATION SETTINGS
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


        # ====================================================
        # SAME PERSON CONFIRMATION
        # ====================================================

        if (
            old_candidate == student_db_id
            and
            current_time - old_time
            <= CONFIRMATION_TIMEOUT
        ):

            count = (
                old_count + 1
            )

        else:

            count = 1


        # ====================================================
        # SAVE CONFIRMATION STATE
        # ====================================================

        session[candidate_key] = (
            student_db_id
        )

        session[count_key] = (
            count
        )

        session[time_key] = (
            current_time
        )

        # Helps Flask save modified session
        session.modified = True


        # ====================================================
        # CONFIRMATION NOT COMPLETE
        # ====================================================

        if (
            count
            <
            REQUIRED_CONFIRMATIONS
        ):

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

            # ------------------------------------------------
            # FINAL DUPLICATE CHECK
            # ------------------------------------------------

            cursor.execute("""
                SELECT id
                FROM attendance
                WHERE student_id=%s
                AND session_id=%s
                LIMIT 1
            """, (
                student_db_id,
                session_id
            ))


            duplicate = (
                cursor.fetchone()
            )


            if duplicate:

                result = (
                    "Already Marked"
                )

            else:

                # --------------------------------------------
                # GENERATE ATTENDANCE ID
                # --------------------------------------------

                cursor.execute("""
                    SELECT
                        COALESCE(
                            MAX(id),
                            0
                        ) + 1
                    FROM attendance
                """)


                next_id = (
                    cursor.fetchone()[0]
                )


                # --------------------------------------------
                # INSERT ATTENDANCE
                # --------------------------------------------

                cursor.execute("""
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
                """, (
                    next_id,
                    student_db_id,
                    session_id,
                    "Attendance marked using browser face recognition"
                ))


                mysql.connection.commit()


                result = (
                    "Present"
                )


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
        # SUCCESS RESPONSE
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


    # ========================================================
    # GLOBAL ERROR
    # ========================================================

    except Exception as e:

        current_app.logger.exception(
            "Browser Face Recognition Error"
        )


        # Try to clear confirmation if session_id exists
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
                f"Face Error: {str(e)}"
        }), 500