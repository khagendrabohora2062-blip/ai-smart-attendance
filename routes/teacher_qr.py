
from flask import (
    Blueprint,
    session,
    redirect,
    url_for,
    flash
)

from extensions import mysql

from utils.teacher_qr_scanner import (
    start_teacher_qr_scanner
)


# ============================================================
# TEACHER QR BLUEPRINT
# ============================================================

teacher_qr = Blueprint(
    "teacher_qr",
    __name__,
    url_prefix="/teacher/qr"
)


# ============================================================
# START QR ATTENDANCE
# ============================================================

@teacher_qr.route("/start/<int:session_id>")
def start(session_id):

    # ========================================================
    # TEACHER LOGIN CHECK
    # ========================================================

    if "teacher_id" not in session:
        return redirect(
            url_for("teacher_auth.login")
        )

    cursor = mysql.connection.cursor()

    try:

        # ====================================================
        # GET ATTENDANCE SESSION
        # ====================================================

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

    # ========================================================
    # SESSION NOT FOUND
    # ========================================================

    if not attendance_session:

        flash(
            "Attendance session not found.",
            "danger"
        )

        return redirect(
            url_for(
                "teacher_attendance.index"
            )
        )

    # ========================================================
    # SESSION CLOSED
    # ========================================================

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

    # ========================================================
    # QR CALLBACK
    # ========================================================

    def process_qr(qr_data):

        cursor = mysql.connection.cursor()

        try:

            # =================================================
            # CLEAN QR DATA
            # =================================================

            qr_data = str(qr_data).strip()

            if not qr_data:

                return {
                    "success": False,
                    "student_id": "",
                    "name": "",
                    "message": "Invalid QR"
                }

            # =================================================
            # FIND STUDENT
            # =================================================

            cursor.execute("""
                SELECT
                    id,
                    student_id,
                    full_name
                FROM students
                WHERE student_id=%s
                LIMIT 1
            """, (
                qr_data,
            ))

            student = cursor.fetchone()

            # =================================================
            # STUDENT NOT FOUND
            # =================================================

            if not student:

                return {
                    "success": False,
                    "student_id": qr_data,
                    "name": "",
                    "message": "Student Not Found"
                }

            student_db_id = student[0]
            student_code = student[1]
            student_name = student[2]

            # =================================================
            # DUPLICATE CHECK
            # =================================================

            cursor.execute("""
                SELECT
                    id
                FROM attendance
                WHERE session_id=%s
                AND student_id=%s
                LIMIT 1
            """, (
                session_id,
                student_db_id
            ))

            already_marked = cursor.fetchone()

            if already_marked:

                return {
                    "success": False,
                    "student_id": student_code,
                    "name": student_name,
                    "message": "Already Marked"
                }

            # =================================================
            # MARK PRESENT
            #
            # QR attendance:
            # Method  = QR
            # Status  = Present
            # Remarks = Attendance marked through QR
            # =================================================

            cursor.execute("""
                INSERT INTO attendance
                (
                    session_id,
                    student_id,
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
                    CURDATE(),
                    CURTIME(),
                    'QR',
                    'Present',
                    'Attendance marked through QR'
                )
            """, (
                session_id,
                student_db_id
            ))

            # =================================================
            # COMMIT
            # =================================================

            mysql.connection.commit()

            # =================================================
            # SUCCESS RESULT
            # =================================================

            return {
                "success": True,
                "student_id": student_code,
                "name": student_name,
                "message": "Attendance Marked - Present"
            }

        except Exception as e:

            # =================================================
            # ROLLBACK
            # =================================================

            mysql.connection.rollback()

            print(
                "QR ATTENDANCE DATABASE ERROR:",
                str(e)
            )

            return {
                "success": False,
                "student_id": "",
                "name": "",
                "message": "Database Error"
            }

        finally:

            cursor.close()

    # ========================================================
    # START CAMERA SCANNER
    # ========================================================

    try:

        start_teacher_qr_scanner(
            process_qr
        )

        flash(
            "QR Attendance Scanner Closed.",
            "success"
        )

    except Exception as e:

        print(
            "QR SCANNER ERROR:",
            str(e)
        )

        flash(
            f"QR Scanner Error: {e}",
            "danger"
        )

    # ========================================================
    # RETURN TEACHER ATTENDANCE
    # ========================================================

    return redirect(
        url_for(
            "teacher_attendance.index"
        )
    )
