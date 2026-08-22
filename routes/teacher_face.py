from flask import (
    Blueprint,
    session,
    redirect,
    url_for,
    flash
)

from extensions import mysql

from utils.recognize_face import recognize_face


# ============================================================
# TEACHER FACE BLUEPRINT
# ============================================================

teacher_face = Blueprint(
    "teacher_face",
    __name__,
    url_prefix="/teacher/face"
)


# ============================================================
# START FACE ATTENDANCE
# ============================================================

@teacher_face.route(
    "/start/<int:session_id>"
)
def start_face_attendance(session_id):

    # ========================================================
    # LOGIN CHECK
    # ========================================================

    if "teacher_id" not in session:

        return redirect(
            url_for("teacher_auth.login")
        )


    cursor = mysql.connection.cursor()


    try:

        # ====================================================
        # VERIFY OPEN SESSION
        # ====================================================

        cursor.execute("""
            SELECT id

            FROM attendance_sessions

            WHERE id=%s

            AND teacher_id=%s

            AND session_status='OPEN'

            LIMIT 1
        """, (
            session_id,
            session["teacher_id"]
        ))

        attendance_session = cursor.fetchone()


    finally:

        cursor.close()


    # ========================================================
    # SESSION NOT FOUND
    # ========================================================

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


    # ========================================================
    # START FACE RECOGNITION
    # ========================================================

    try:

        recognize_face(
            session_id=session_id
        )


        flash(
            "Face Attendance Completed.",
            "success"
        )


    except Exception as e:

        flash(
            f"Face Attendance Error: {e}",
            "danger"
        )


    return redirect(
        url_for(
            "teacher_attendance.index"
        )
    )