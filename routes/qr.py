from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    flash
)

from extensions import mysql
from utils.qr_scanner import start_qr_scanner


qr = Blueprint(
    "qr",
    __name__,
    url_prefix="/qr"
)


# ======================================
# QR Dashboard
# ======================================
@qr.route("/")
def dashboard():

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    cursor = mysql.connection.cursor()

    # --------------------------------------
    # Total Students
    # --------------------------------------
    cursor.execute("""
        SELECT COUNT(*)
        FROM students
    """)
    total_students = cursor.fetchone()[0]

    # --------------------------------------
    # Today's QR Attendance
    # --------------------------------------
    cursor.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE attendance_method='QR'
        AND attendance_date=CURDATE()
    """)
    total_today = cursor.fetchone()[0]

    # --------------------------------------
    # Today's Total Present
    # --------------------------------------
    cursor.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE attendance_date=CURDATE()
        AND status='Present'
    """)
    total_present = cursor.fetchone()[0]

    if total_students > 0:
        percentage = round(
            (total_present / total_students) * 100,
            2
        )
    else:
        percentage = 0

    # --------------------------------------
    # Recent QR Attendance
    # --------------------------------------
    cursor.execute("""
        SELECT

            s.student_id,

            s.full_name,

            s.photo,

            a.attendance_time,

            a.status

        FROM attendance a

        INNER JOIN students s
            ON a.student_id = s.id

        WHERE

            a.attendance_method='QR'

            AND a.attendance_date=CURDATE()

        ORDER BY
            a.attendance_time DESC

        LIMIT 10
    """)

    attendance_list = cursor.fetchall()

    cursor.close()

    return render_template(
        "qr/dashboard.html",
        total_students=total_students,
        total_today=total_today,
        total_present=total_present,
        percentage=percentage,
        attendance_list=attendance_list
    )


# ======================================
# Start QR Attendance
# ======================================
@qr.route("/start")
def start():

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    # ======================================
    # QR Callback
    # ======================================
    def process_qr(qr_data):
        cursor = mysql.connection.cursor()

        try:

            # --------------------------------------
            # Get Student
            # --------------------------------------
            cursor.execute("""
                SELECT
                    id,
                    student_id,
                    full_name
                FROM students
                WHERE student_id=%s
            """, (qr_data,))

            student = cursor.fetchone()

            if not student:

                cursor.close()

                return {
                    "success": False,
                    "student_id": qr_data,
                    "name": "",
                    "message": "Student Not Found"
                }

            student_db_id = student[0]

            # --------------------------------------
            # Get Today's OPEN Session
            # --------------------------------------
            cursor.execute("""
                SELECT

                    id,

                    subject_id,

                    teacher_id

                FROM attendance_sessions

                WHERE

                    session_date = CURDATE()

                    AND session_status='OPEN'

                LIMIT 1
            """)

            session_data = cursor.fetchone()

            if not session_data:

                cursor.close()

                return {
                    "success": False,
                    "student_id": student[1],
                    "name": student[2],
                    "message": "No OPEN Session"
                }

            session_id = session_data[0]

            # --------------------------------------
            # Duplicate Check
            # --------------------------------------
            cursor.execute("""
                SELECT id
                FROM attendance
                WHERE
                    session_id=%s
                    AND student_id=%s
            """,
            (
                session_id,
                student_db_id
            ))

            already_marked = cursor.fetchone()

            if already_marked:

                cursor.close()

                return {
                    "success": False,
                    "student_id": student[1],
                    "name": student[2],
                    "message": "Already Marked"
                }

            # --------------------------------------
            # Save Attendance
            # --------------------------------------
            cursor.execute("""
                INSERT INTO attendance
                (
                    session_id,
                    student_id,
                    attendance_date,
                    attendance_time,
                    attendance_method,
                    status
                )
                VALUES
                (
                    %s,
                    %s,
                    CURDATE(),
                    CURTIME(),
                    'QR',
                    'Present'
                )
            """,
            (
                session_id,
                student_db_id
            ))

            mysql.connection.commit()

            cursor.close()

            return {
                "success": True,
                "student_id": student[1],
                "name": student[2],
                "message": "Attendance Marked Successfully"
            }

        except Exception as e:

            mysql.connection.rollback()

            cursor.close()

            return {
                "success": False,
                "student_id": "",
                "name": "",
                "message": str(e)
            }

    try:

        start_qr_scanner(process_qr)

        flash(
            "QR Scanner Closed Successfully.",
            "success"
        )

    except Exception as e:

        flash(
            f"QR Error : {e}",
            "danger"
        )

    return redirect(
        url_for("qr.dashboard")
    )