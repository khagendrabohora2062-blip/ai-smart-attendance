from datetime import datetime

from extensions import mysql


# ============================================================
# MARK FACE ATTENDANCE
# ============================================================

def mark_face_attendance(student_db_id, session_id):

    cursor = mysql.connection.cursor()

    try:

        # ====================================================
        # GET SESSION INFORMATION
        # ====================================================

        cursor.execute("""
            SELECT
                id,
                session_date,
                start_time,
                end_time,
                session_status
            FROM attendance_sessions
            WHERE id=%s
        """, (
            session_id,
        ))

        attendance_session = cursor.fetchone()

        if not attendance_session:

            print("ERROR: Attendance session not found")

            return False


        session_db_id = attendance_session[0]
        session_date = attendance_session[1]
        start_time = attendance_session[2]
        end_time = attendance_session[3]
        session_status = attendance_session[4]


        # ====================================================
        # SESSION MUST BE OPEN
        # ====================================================

        if session_status != "OPEN":

            print(
                "ERROR: Attendance session is closed"
            )

            return False


        # ====================================================
        # CHECK DUPLICATE ATTENDANCE
        # ====================================================

        cursor.execute("""
            SELECT
                id,
                status
            FROM attendance
            WHERE session_id=%s
            AND student_id=%s
        """, (
            session_db_id,
            student_db_id
        ))

        existing_record = cursor.fetchone()


        if existing_record:

            print(
                "Duplicate attendance already exists:",
                existing_record
            )

            return False


        # ====================================================
        # CURRENT DATE & TIME
        # ====================================================

        now = datetime.now()

        attendance_date = session_date

        attendance_time = now.time()


        # ====================================================
        # CONVERT MYSQL TIME TO SECONDS
        # ====================================================

        def time_to_seconds(value):

            if value is None:
                return None

            if hasattr(value, "total_seconds"):

                return int(
                    value.total_seconds()
                )

            if hasattr(value, "hour"):

                return (
                    value.hour * 3600
                    + value.minute * 60
                    + value.second
                )

            return None


        # ====================================================
        # DETERMINE PRESENT / LATE
        # ====================================================

        status = "Present"

        start_seconds = time_to_seconds(
            start_time
        )


        current_seconds = (
            now.hour * 3600
            + now.minute * 60
            + now.second
        )


        if start_seconds is not None:

            if current_seconds > start_seconds:

                status = "Late"

            else:

                status = "Present"


        # ====================================================
        # SAVE ATTENDANCE
        # ====================================================

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
                %s,
                %s,
                'FACE',
                %s,
                %s
            )
        """, (
            session_db_id,
            student_db_id,
            attendance_date,
            attendance_time,
            status,
            "Face Recognition"
        ))


        mysql.connection.commit()


        # ====================================================
        # DEBUG INFORMATION
        # ====================================================

        print(
            "======================================"
        )

        print(
            f"Student ID : {student_db_id}"
        )

        print(
            f"Session ID : {session_db_id}"
        )

        print(
            f"Attendance Date : {attendance_date}"
        )

        print(
            f"Attendance Time : {attendance_time}"
        )

        print(
            f"Status : {status}"
        )

        print(
            "SUCCESS : Attendance Saved"
        )

        print(
            "======================================"
        )


        return True


    except Exception as e:

        mysql.connection.rollback()

        print(
            f"ATTENDANCE ERROR : {e}"
        )

        return False


    finally:

        cursor.close()