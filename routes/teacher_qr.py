import uuid

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
# GENERATE UNIQUE ATTENDANCE ID
# ============================================================

def generate_attendance_id(cursor):
    """
    Generate a unique positive integer ID for attendance.

    attendance.id is NOT AUTO_INCREMENT,
    so ID is generated manually.
    """

    while True:

        attendance_id = uuid.uuid4().int % 2147483647

        if attendance_id <= 0:
            continue

        cursor.execute(
            """
            SELECT id
            FROM attendance
            WHERE id = %s
            LIMIT 1
            """,
            (attendance_id,)
        )

        existing = cursor.fetchone()

        if not existing:
            return attendance_id


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

    teacher_id = session["teacher_id"]

    cursor = mysql.connection.cursor()

    try:

        # ====================================================
        # GET ATTENDANCE SESSION
        # ====================================================

        cursor.execute(
            """
            SELECT
                id,
                subject_id,
                session_date,
                session_status
            FROM attendance_sessions
            WHERE id = %s
            AND teacher_id = %s
            LIMIT 1
            """,
            (
                session_id,
                teacher_id
            )
        )

        attendance_session = cursor.fetchone()

    except Exception as e:

        print(
            "QR SESSION DATABASE ERROR:",
            str(e)
        )

        flash(
            f"Unable to load attendance session: {e}",
            "danger"
        )

        return redirect(
            url_for(
                "teacher_attendance.index"
            )
        )

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

    if attendance_session[3] != "OPEN":

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

            cursor.execute(
                """
                SELECT
                    id,
                    student_id,
                    full_name,
                    semester,
                    department
                FROM students
                WHERE student_id = %s
                LIMIT 1
                """,
                (qr_data,)
            )

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


            # =================================================
            # STUDENT INFORMATION
            # =================================================

            student_db_id = student[0]
            student_code = student[1]
            student_name = student[2]
            student_semester = student[3]
            student_department = student[4]


            # =================================================
            # VERIFY STUDENT BELONGS TO THIS SESSION
            # =================================================

            session_cursor = mysql.connection.cursor()

            try:

                session_cursor.execute(
                    """
                    SELECT
                        sub.semester,
                        sub.department
                    FROM attendance_sessions s
                    INNER JOIN subjects sub
                        ON s.subject_id = sub.id
                    WHERE s.id = %s
                    AND s.teacher_id = %s
                    LIMIT 1
                    """,
                    (
                        session_id,
                        teacher_id
                    )
                )

                session_details = session_cursor.fetchone()

            finally:

                session_cursor.close()


            if not session_details:

                return {
                    "success": False,
                    "student_id": student_code,
                    "name": student_name,
                    "message": "Attendance Session Not Found"
                }


            session_semester = session_details[0]
            session_department = session_details[1]


            # =================================================
            # CHECK SEMESTER
            # =================================================

            if student_semester != session_semester:

                return {
                    "success": False,
                    "student_id": student_code,
                    "name": student_name,
                    "message": "Student does not belong to this semester"
                }


            # =================================================
            # CHECK DEPARTMENT
            # =================================================

            same_department = (
                student_department == session_department
            )

            if (
                student_department is None
                and session_department is None
            ):
                same_department = True


            if not same_department:

                return {
                    "success": False,
                    "student_id": student_code,
                    "name": student_name,
                    "message": "Student does not belong to this department"
                }


            # =================================================
            # DUPLICATE ATTENDANCE CHECK
            # =================================================

            cursor.execute(
                """
                SELECT
                    id,
                    status
                FROM attendance
                WHERE session_id = %s
                AND student_id = %s
                LIMIT 1
                """,
                (
                    session_id,
                    student_db_id
                )
            )

            already_marked = cursor.fetchone()


            if already_marked:

                return {
                    "success": False,
                    "student_id": student_code,
                    "name": student_name,
                    "message": "Already Marked"
                }


            # =================================================
            # GENERATE UNIQUE ATTENDANCE ID
            # =================================================

            attendance_id = generate_attendance_id(
                cursor
            )


            # =================================================
            # INSERT QR ATTENDANCE
            # =================================================

            cursor.execute(
                """
                INSERT INTO attendance
                (
                    id,
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
                    CURDATE(),
                    CURTIME(),
                    'QR',
                    'Present',
                    'Attendance marked through QR'
                )
                """,
                (
                    attendance_id,
                    session_id,
                    student_db_id
                )
            )


            # =================================================
            # COMMIT
            # =================================================

            mysql.connection.commit()


            # =================================================
            # SUCCESS
            # =================================================

            print(
                f"QR ATTENDANCE SUCCESS: "
                f"{student_code} - {student_name}"
            )

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
                "message": f"Database Error: {e}"
            }


        finally:

            cursor.close()


    # ========================================================
    # START CAMERA SCANNER
    # ========================================================

    try:

        print(
            f"Starting QR scanner for session: {session_id}"
        )

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