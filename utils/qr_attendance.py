from datetime import datetime

from extensions import mysql


# ==========================================
# Mark QR Attendance
# ==========================================
def mark_qr_attendance(student_code):

    cursor = mysql.connection.cursor()

    try:

        # --------------------------------------
        # Get Student
        # --------------------------------------
        cursor.execute(
            """
            SELECT id

            FROM students

            WHERE student_id=%s
            """,
            (student_code,)
        )

        student = cursor.fetchone()

        if not student:

            return False, "Student not found."

        student_id = student[0]

        today = datetime.now().date()

        current_time = datetime.now().time()

        # --------------------------------------
        # Get OPEN Session
        # --------------------------------------
        cursor.execute(
            """
            SELECT id

            FROM attendance_sessions

            WHERE

                session_date=%s

                AND session_status='OPEN'

            LIMIT 1
            """,
            (today,)
        )

        session = cursor.fetchone()

        if not session:

            return False, "No OPEN session."

        session_id = session[0]

        # --------------------------------------
        # Duplicate Check
        # --------------------------------------
        cursor.execute(
            """
            SELECT id

            FROM attendance

            WHERE

                session_id=%s

                AND student_id=%s
            """,
            (
                session_id,
                student_id
            )
        )

        if cursor.fetchone():

            return False, "Attendance already marked."

        # --------------------------------------
        # Save Attendance
        # --------------------------------------
        cursor.execute(
            """
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

                %s,

                %s,

                %s,

                %s

            )
            """,
            (
                session_id,
                student_id,
                today,
                current_time,
                "QR",
                "Present"
            )
        )

        mysql.connection.commit()

        return True, "Attendance marked successfully."

    except Exception as e:

        mysql.connection.rollback()

        return False, str(e)

    finally:

        cursor.close()