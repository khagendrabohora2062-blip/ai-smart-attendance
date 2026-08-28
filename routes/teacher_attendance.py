from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_file
)

from extensions import mysql
from datetime import date
from openpyxl import Workbook
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

import io
import uuid


# ============================================================
# TEACHER ATTENDANCE BLUEPRINT
# ============================================================

teacher_attendance = Blueprint(
    "teacher_attendance",
    __name__,
    url_prefix="/teacher/attendance"
)


# ============================================================
# TEACHER LOGIN CHECK
# ============================================================

def teacher_logged_in():
    return "teacher_id" in session


# ============================================================
# GENERATE UNIQUE SESSION ID
# ============================================================

def generate_session_id(cursor):

    while True:

        new_id = uuid.uuid4().int % 2147483647

        if new_id <= 0:
            continue

        cursor.execute(
            """
            SELECT id
            FROM attendance_sessions
            WHERE id = %s
            LIMIT 1
            """,
            (new_id,)
        )

        if not cursor.fetchone():
            return new_id


# ============================================================
# GENERATE UNIQUE ATTENDANCE ID
# IMPORTANT:
# attendance.id IS NOT AUTO_INCREMENT IN YOUR TiDB
# ============================================================

def generate_attendance_id(cursor):

    while True:

        new_id = uuid.uuid4().int % 2147483647

        if new_id <= 0:
            continue

        cursor.execute(
            """
            SELECT id
            FROM attendance
            WHERE id = %s
            LIMIT 1
            """,
            (new_id,)
        )

        if not cursor.fetchone():
            return new_id


# ============================================================
# ATTENDANCE DASHBOARD
# ============================================================

@teacher_attendance.route("/")
def index():

    if not teacher_logged_in():
        return redirect(
            url_for("teacher_auth.login")
        )

    cursor = mysql.connection.cursor()

    subjects = []
    sessions = []

    total_sessions = 0
    open_sessions = 0
    total_attendance = 0

    try:

        teacher_id = session["teacher_id"]

        # ====================================================
        # TEACHER SUBJECTS
        # ====================================================

        cursor.execute(
            """
            SELECT
                id,
                subject_code,
                subject_name,
                semester,
                department
            FROM subjects
            WHERE teacher_id = %s
            ORDER BY semester, subject_name
            """,
            (teacher_id,)
        )

        subjects = cursor.fetchall()

        # ====================================================
        # ATTENDANCE SESSIONS
        # ====================================================

        cursor.execute(
            """
            SELECT
                s.id,
                sub.subject_code,
                sub.subject_name,
                s.session_date,
                s.start_time,
                s.end_time,
                s.session_status,

                (
                    SELECT COUNT(*)
                    FROM attendance a
                    WHERE a.session_id = s.id
                ) AS total_attendance,

                (
                    SELECT COUNT(*)
                    FROM attendance a
                    WHERE a.session_id = s.id
                    AND a.status = 'Present'
                ) AS present_count,

                (
                    SELECT COUNT(*)
                    FROM attendance a
                    WHERE a.session_id = s.id
                    AND a.status = 'Absent'
                ) AS absent_count

            FROM attendance_sessions s

            INNER JOIN subjects sub
                ON s.subject_id = sub.id

            WHERE s.teacher_id = %s

            ORDER BY
                s.session_date DESC,
                s.id DESC
            """,
            (teacher_id,)
        )

        sessions = cursor.fetchall()

        # ====================================================
        # TOTAL SESSIONS
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM attendance_sessions
            WHERE teacher_id = %s
            """,
            (teacher_id,)
        )

        result = cursor.fetchone()
        total_sessions = result[0] if result else 0

        # ====================================================
        # OPEN SESSIONS
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM attendance_sessions
            WHERE teacher_id = %s
            AND session_status = 'OPEN'
            """,
            (teacher_id,)
        )

        result = cursor.fetchone()
        open_sessions = result[0] if result else 0

        # ====================================================
        # TOTAL ATTENDANCE
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM attendance a

            INNER JOIN attendance_sessions s
                ON a.session_id = s.id

            WHERE s.teacher_id = %s
            """,
            (teacher_id,)
        )

        result = cursor.fetchone()
        total_attendance = result[0] if result else 0

    except Exception as e:

        mysql.connection.rollback()

        print(
            "ATTENDANCE DASHBOARD ERROR:",
            str(e)
        )

        flash(
            f"Attendance loading error: {e}",
            "danger"
        )

    finally:
        cursor.close()

    return render_template(
        "teacher/attendance/index.html",
        subjects=subjects,
        sessions=sessions,
        total_sessions=total_sessions,
        open_sessions=open_sessions,
        total_attendance=total_attendance
    )


# ============================================================
# OPEN ATTENDANCE SESSION PAGE
# ============================================================

@teacher_attendance.route(
    "/open",
    methods=["GET"]
)
def open_session_page():

    if not teacher_logged_in():
        return redirect(
            url_for("teacher_auth.login")
        )

    cursor = mysql.connection.cursor()

    subjects = []

    try:

        teacher_id = session["teacher_id"]

        cursor.execute(
            """
            SELECT
                id,
                subject_code,
                subject_name,
                semester,
                department
            FROM subjects
            WHERE teacher_id = %s
            ORDER BY semester, subject_name
            """,
            (teacher_id,)
        )

        subjects = cursor.fetchall()

    except Exception as e:

        print(
            "OPEN SESSION PAGE ERROR:",
            str(e)
        )

        flash(
            f"Unable to load subjects: {e}",
            "danger"
        )

    finally:
        cursor.close()

    return render_template(
        "teacher/attendance/open_session.html",
        subjects=subjects
    )


# ============================================================
# CREATE / OPEN ATTENDANCE SESSION
# ============================================================

@teacher_attendance.route(
    "/open",
    methods=["POST"]
)
def open_session():

    if not teacher_logged_in():
        return redirect(
            url_for("teacher_auth.login")
        )

    teacher_id = session["teacher_id"]

    subject_id = request.form.get("subject_id")
    start_time = request.form.get("start_time")
    end_time = request.form.get("end_time")

    # ========================================================
    # VALIDATE SUBJECT
    # ========================================================

    if not subject_id:

        flash(
            "Please select a subject.",
            "danger"
        )

        return redirect(
            url_for(
                "teacher_attendance.open_session_page"
            )
        )

    try:

        subject_id = int(subject_id)

    except (TypeError, ValueError):

        flash(
            "Invalid subject selected.",
            "danger"
        )

        return redirect(
            url_for(
                "teacher_attendance.open_session_page"
            )
        )

    # ========================================================
    # VALIDATE START TIME
    # ========================================================

    if not start_time:

        flash(
            "Please enter start time.",
            "danger"
        )

        return redirect(
            url_for(
                "teacher_attendance.open_session_page"
            )
        )

    cursor = mysql.connection.cursor()

    try:

        # ====================================================
        # VERIFY SUBJECT
        # ====================================================

        cursor.execute(
            """
            SELECT
                id,
                subject_code,
                subject_name,
                semester,
                department
            FROM subjects
            WHERE id = %s
            AND teacher_id = %s
            LIMIT 1
            """,
            (
                subject_id,
                teacher_id
            )
        )

        subject = cursor.fetchone()

        if not subject:

            flash(
                "Invalid subject selected or this subject is not assigned to you.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher_attendance.open_session_page"
                )
            )

        subject_db_id = subject[0]
        subject_name = subject[2]

        # ====================================================
        # CHECK TODAY'S SESSION
        # ====================================================

        cursor.execute(
            """
            SELECT
                id,
                session_status
            FROM attendance_sessions
            WHERE teacher_id = %s
            AND subject_id = %s
            AND session_date = %s
            LIMIT 1
            """,
            (
                teacher_id,
                subject_db_id,
                date.today()
            )
        )

        existing_session = cursor.fetchone()

        if existing_session:

            if existing_session[1] == "OPEN":

                flash(
                    f"{subject_name} already has an OPEN attendance session today.",
                    "warning"
                )

            else:

                flash(
                    f"Attendance session for {subject_name} has already been created today.",
                    "warning"
                )

            return redirect(
                url_for(
                    "teacher_attendance.index"
                )
            )

        # ====================================================
        # GENERATE SESSION ID
        # ====================================================

        new_session_id = generate_session_id(cursor)

        # ====================================================
        # CREATE SESSION
        # ====================================================

        cursor.execute(
            """
            INSERT INTO attendance_sessions
            (
                id,
                teacher_id,
                subject_id,
                session_date,
                start_time,
                end_time,
                session_status
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                'OPEN'
            )
            """,
            (
                new_session_id,
                teacher_id,
                subject_db_id,
                date.today(),
                start_time,
                end_time
            )
        )

        mysql.connection.commit()

        flash(
            f"Attendance session opened for {subject_name}.",
            "success"
        )

    except Exception as e:

        mysql.connection.rollback()

        print(
            "OPEN ATTENDANCE SESSION ERROR:",
            str(e)
        )

        flash(
            f"Error opening attendance session: {e}",
            "danger"
        )

    finally:
        cursor.close()

    return redirect(
        url_for(
            "teacher_attendance.index"
        )
    )


# ============================================================
# CLOSE ATTENDANCE SESSION
# ============================================================

@teacher_attendance.route(
    "/close/<int:session_id>",
    methods=["POST"]
)
def close_session(session_id):

    if not teacher_logged_in():
        return redirect(
            url_for("teacher_auth.login")
        )

    teacher_id = session["teacher_id"]

    cursor = mysql.connection.cursor()

    try:

        # ====================================================
        # GET SESSION DETAILS
        # ====================================================

        cursor.execute(
            """
            SELECT
                s.id,
                s.subject_id,
                s.session_date,
                s.session_status,
                sub.subject_name,
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

        attendance_session = cursor.fetchone()

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

        session_id_db = attendance_session[0]
        subject_id = attendance_session[1]
        session_date = attendance_session[2]
        session_status = attendance_session[3]
        subject_name = attendance_session[4]
        semester = attendance_session[5]
        department = attendance_session[6]

        # ====================================================
        # ALREADY CLOSED
        # ====================================================

        if session_status == "CLOSED":

            flash(
                "Attendance session is already closed.",
                "warning"
            )

            return redirect(
                url_for(
                    "teacher_attendance.index"
                )
            )

        # ====================================================
        # GET ALL ELIGIBLE STUDENTS
        #
        # Same semester + same department
        # ====================================================

        cursor.execute(
            """
            SELECT
                id
            FROM students
            WHERE semester = %s
            AND
            (
                department = %s
                OR
                (
                    department IS NULL
                    AND %s IS NULL
                )
            )
            """,
            (
                semester,
                department,
                department
            )
        )

        students = cursor.fetchall()

        # ====================================================
        # AUTOMATICALLY MARK ABSENT
        #
        # IMPORTANT:
        # attendance.id is NOT AUTO_INCREMENT
        #
        # Therefore generate ID for EVERY absent record.
        # ====================================================

        absent_count = 0

        for student in students:

            student_db_id = student[0]

            # ----------------------------------------------
            # CHECK WHETHER ALREADY MARKED
            # ----------------------------------------------

            cursor.execute(
                """
                SELECT id
                FROM attendance
                WHERE session_id = %s
                AND student_id = %s
                LIMIT 1
                """,
                (
                    session_id_db,
                    student_db_id
                )
            )

            already_marked = cursor.fetchone()

            if already_marked:
                continue

            # ----------------------------------------------
            # GENERATE ATTENDANCE ID
            # ----------------------------------------------

            attendance_id = generate_attendance_id(cursor)

            # ----------------------------------------------
            # INSERT ABSENT
            # ----------------------------------------------

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
                    %s,
                    CURTIME(),
                    'MANUAL',
                    'Absent',
                    'Automatically marked absent when session was closed'
                )
                """,
                (
                    attendance_id,
                    session_id_db,
                    student_db_id,
                    session_date
                )
            )

            absent_count += 1

        # ====================================================
        # CLOSE SESSION
        # ====================================================

        cursor.execute(
            """
            UPDATE attendance_sessions
            SET
                session_status = 'CLOSED',
                end_time = CURTIME()
            WHERE id = %s
            AND teacher_id = %s
            """,
            (
                session_id_db,
                teacher_id
            )
        )

        mysql.connection.commit()

        # ====================================================
        # FINAL COUNTS
        # ====================================================

        cursor.execute(
            """
            SELECT
                COALESCE(
                    SUM(status = 'Present'),
                    0
                ) AS present_count,

                COALESCE(
                    SUM(status = 'Absent'),
                    0
                ) AS absent_count

            FROM attendance

            WHERE session_id = %s
            """,
            (
                session_id_db,
            )
        )

        counts = cursor.fetchone()

        present_count = counts[0] or 0
        final_absent_count = counts[1] or 0

        # ====================================================
        # SUCCESS
        # ====================================================

        flash(
            f"{subject_name} attendance closed successfully. "
            f"Present: {present_count}, "
            f"Absent: {final_absent_count}",
            "success"
        )

    except Exception as e:

        mysql.connection.rollback()

        print(
            "CLOSE ATTENDANCE ERROR:",
            str(e)
        )

        flash(
            f"Error closing attendance session: {e}",
            "danger"
        )

    finally:
        cursor.close()

    return redirect(
        url_for(
            "teacher_attendance.index"
        )
    )


# ============================================================
# DELETE SESSION
# ============================================================

@teacher_attendance.route(
    "/delete/<int:session_id>",
    methods=["POST"]
)
def delete_session(session_id):

    if not teacher_logged_in():
        return redirect(
            url_for("teacher_auth.login")
        )

    teacher_id = session["teacher_id"]

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT id
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

        if not attendance_session:

            flash(
                "Attendance session not found or access denied.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher_attendance.index"
                )
            )

        # ====================================================
        # DELETE ATTENDANCE
        # ====================================================

        cursor.execute(
            """
            DELETE FROM attendance
            WHERE session_id = %s
            """,
            (
                session_id,
            )
        )

        # ====================================================
        # DELETE SESSION
        # ====================================================

        cursor.execute(
            """
            DELETE FROM attendance_sessions
            WHERE id = %s
            AND teacher_id = %s
            """,
            (
                session_id,
                teacher_id
            )
        )

        if cursor.rowcount == 0:

            mysql.connection.rollback()

            flash(
                "Session could not be deleted.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher_attendance.index"
                )
            )

        mysql.connection.commit()

        flash(
            "Attendance session deleted successfully.",
            "success"
        )

    except Exception as e:

        mysql.connection.rollback()

        print(
            "SESSION DELETE ERROR:",
            str(e)
        )

        flash(
            f"Session deletion error: {e}",
            "danger"
        )

    finally:
        cursor.close()

    return redirect(
        url_for(
            "teacher_attendance.index"
        )
    )


# ============================================================
# MANUAL ABSENT
# ============================================================

@teacher_attendance.route(
    "/absent/<int:session_id>/<int:student_id>",
    methods=["POST"]
)
def mark_absent(session_id, student_id):

    if not teacher_logged_in():
        return redirect(
            url_for("teacher_auth.login")
        )

    teacher_id = session["teacher_id"]

    cursor = mysql.connection.cursor()

    try:

        # ====================================================
        # VERIFY SESSION
        # ====================================================

        cursor.execute(
            """
            SELECT
                s.id,
                s.session_status,
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

        attendance_session = cursor.fetchone()

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

        session_status = attendance_session[1]
        session_semester = attendance_session[2]
        session_department = attendance_session[3]

        # ====================================================
        # DO NOT ALLOW AFTER CLOSED
        # ====================================================

        if session_status == "CLOSED":

            flash(
                "This attendance session is already closed.",
                "warning"
            )

            return redirect(
                url_for(
                    "teacher_attendance.report",
                    session_id=session_id
                )
            )

        # ====================================================
        # VERIFY STUDENT
        # ====================================================

        cursor.execute(
            """
            SELECT
                id,
                student_id,
                full_name,
                semester,
                department
            FROM students
            WHERE id = %s
            LIMIT 1
            """,
            (
                student_id,
            )
        )

        student = cursor.fetchone()

        if not student:

            flash(
                "Student not found.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher_attendance.report",
                    session_id=session_id
                )
            )

        student_semester = student[3]
        student_department = student[4]

        same_department = (
            student_department == session_department
        )

        if (
            student_department is None
            and session_department is None
        ):
            same_department = True

        if (
            student_semester != session_semester
            or not same_department
        ):

            flash(
                "This student does not belong to this attendance session.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher_attendance.report",
                    session_id=session_id
                )
            )

        # ====================================================
        # CHECK EXISTING ATTENDANCE
        # ====================================================

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
                student_id
            )
        )

        existing = cursor.fetchone()

        if existing:

            flash(
                f"{student[2]} already has attendance status: {existing[1]}",
                "warning"
            )

            return redirect(
                url_for(
                    "teacher_attendance.report",
                    session_id=session_id
                )
            )

        # ====================================================
        # GENERATE ATTENDANCE ID
        # ====================================================

        attendance_id = generate_attendance_id(cursor)

        # ====================================================
        # INSERT ABSENT
        # ====================================================

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
                'MANUAL',
                'Absent',
                'Marked absent manually by teacher'
            )
            """,
            (
                attendance_id,
                session_id,
                student_id
            )
        )

        mysql.connection.commit()

        flash(
            f"{student[2]} marked Absent.",
            "success"
        )

    except Exception as e:

        mysql.connection.rollback()

        print(
            "MANUAL ABSENT ERROR:",
            str(e)
        )

        flash(
            f"Error marking absent: {e}",
            "danger"
        )

    finally:
        cursor.close()

    return redirect(
        url_for(
            "teacher_attendance.report",
            session_id=session_id
        )
    )


# ============================================================
# ALL REPORTS
# ============================================================

@teacher_attendance.route("/reports")
def reports():

    if not teacher_logged_in():
        return redirect(
            url_for("teacher_auth.login")
        )

    cursor = mysql.connection.cursor()

    reports_data = []

    try:

        teacher_id = session["teacher_id"]

        cursor.execute(
            """
            SELECT
                s.id,
                sub.subject_code,
                sub.subject_name,
                s.session_date,
                s.start_time,
                s.end_time,
                s.session_status,

                (
                    SELECT COUNT(*)
                    FROM attendance a1
                    WHERE a1.session_id = s.id
                ) AS total_attendance,

                (
                    SELECT COUNT(*)
                    FROM attendance a2
                    WHERE a2.session_id = s.id
                    AND a2.status = 'Present'
                ) AS present_count,

                (
                    SELECT COUNT(*)
                    FROM attendance a3
                    WHERE a3.session_id = s.id
                    AND a3.status = 'Absent'
                ) AS absent_count

            FROM attendance_sessions s

            INNER JOIN subjects sub
                ON s.subject_id = sub.id

            WHERE s.teacher_id = %s

            ORDER BY
                s.session_date DESC,
                s.id DESC
            """,
            (
                teacher_id,
            )
        )

        reports_data = cursor.fetchall()

    except Exception as e:

        print(
            "REPORTS LOADING ERROR:",
            str(e)
        )

        flash(
            f"Reports loading error: {e}",
            "danger"
        )

    finally:
        cursor.close()

    return render_template(
        "teacher/reports.html",
        reports=reports_data
    )


# ============================================================
# INDIVIDUAL SESSION REPORT
# ============================================================

@teacher_attendance.route(
    "/report/<int:session_id>"
)
def report(session_id):

    if not teacher_logged_in():
        return redirect(
            url_for("teacher_auth.login")
        )

    teacher_id = session["teacher_id"]

    cursor = mysql.connection.cursor()

    try:

        # ====================================================
        # SESSION INFORMATION
        # ====================================================

        cursor.execute(
            """
            SELECT
                s.id,
                sub.subject_code,
                sub.subject_name,
                s.session_date,
                s.start_time,
                s.end_time,
                s.session_status
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

        session_info = cursor.fetchone()

        if not session_info:

            flash(
                "Attendance session not found.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher_attendance.reports"
                )
            )

        # ====================================================
        # ATTENDANCE RECORDS
        # ====================================================

        cursor.execute(
            """
            SELECT
                students.id,
                students.student_id,
                students.full_name,
                students.department,
                attendance.attendance_date,
                attendance.attendance_time,
                attendance.attendance_method,
                attendance.status,
                attendance.remarks

            FROM attendance

            INNER JOIN students
                ON attendance.student_id = students.id

            WHERE attendance.session_id = %s

            ORDER BY students.full_name ASC
            """,
            (
                session_id,
            )
        )

        records = cursor.fetchall()

        # ====================================================
        # PRESENT
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM attendance
            WHERE session_id = %s
            AND status = 'Present'
            """,
            (
                session_id,
            )
        )

        present = cursor.fetchone()[0]

        # ====================================================
        # ABSENT
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM attendance
            WHERE session_id = %s
            AND status = 'Absent'
            """,
            (
                session_id,
            )
        )

        absent = cursor.fetchone()[0]

        # ====================================================
        # TOTAL ATTENDANCE RECORDS
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM attendance
            WHERE session_id = %s
            """,
            (
                session_id,
            )
        )

        total = cursor.fetchone()[0]

        # ====================================================
        # SUBJECT DETAILS
        # ====================================================

        cursor.execute(
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

        subject_details = cursor.fetchone()

        semester = (
            subject_details[0]
            if subject_details
            else None
        )

        department = (
            subject_details[1]
            if subject_details
            else None
        )

        # ====================================================
        # TOTAL EXPECTED STUDENTS
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM students

            WHERE semester = %s

            AND
            (
                department = %s
                OR
                (
                    department IS NULL
                    AND %s IS NULL
                )
            )
            """,
            (
                semester,
                department,
                department
            )
        )

        total_students = cursor.fetchone()[0]

    except Exception as e:

        mysql.connection.rollback()

        print(
            "REPORT LOADING ERROR:",
            str(e)
        )

        flash(
            f"Report loading error: {e}",
            "danger"
        )

        return redirect(
            url_for(
                "teacher_attendance.reports"
            )
        )

    finally:
        cursor.close()

    return render_template(
        "teacher/attendance/report.html",
        session_info=session_info,
        records=records,
        present=present,
        absent=absent,
        total=total,
        total_students=total_students,
        semester=semester,
        department=department
    )


# ============================================================
# EXPORT EXCEL
# ============================================================

@teacher_attendance.route(
    "/export/excel/<int:session_id>"
)
def export_excel(session_id):

    if not teacher_logged_in():
        return redirect(
            url_for("teacher_auth.login")
        )

    teacher_id = session["teacher_id"]

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                s.id,
                sub.subject_code,
                sub.subject_name,
                sub.semester,
                sub.department,
                s.session_date,
                s.start_time,
                s.end_time,
                s.session_status

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

        session_info = cursor.fetchone()

        if not session_info:

            flash(
                "Attendance session not found.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher_attendance.reports"
                )
            )

        cursor.execute(
            """
            SELECT
                students.student_id,
                students.full_name,
                students.department,
                attendance.attendance_date,
                attendance.attendance_time,
                attendance.attendance_method,
                attendance.status,
                attendance.remarks

            FROM attendance

            INNER JOIN students
                ON attendance.student_id = students.id

            WHERE attendance.session_id = %s

            ORDER BY students.full_name
            """,
            (
                session_id,
            )
        )

        rows = cursor.fetchall()

    except Exception as e:

        print(
            "EXCEL EXPORT ERROR:",
            str(e)
        )

        flash(
            f"Excel export error: {e}",
            "danger"
        )

        return redirect(
            url_for(
                "teacher_attendance.report",
                session_id=session_id
            )
        )

    finally:
        cursor.close()

    # ========================================================
    # CREATE EXCEL
    # ========================================================

    workbook = Workbook()

    sheet = workbook.active

    sheet.title = "Attendance Report"

    sheet.append([
        "AI Smart Attendance System"
    ])

    sheet.append([
        "Attendance Report"
    ])

    sheet.append([])

    sheet.append([
        "Subject Code",
        session_info[1]
    ])

    sheet.append([
        "Subject",
        session_info[2]
    ])

    sheet.append([
        "Semester",
        session_info[3]
    ])

    sheet.append([
        "Department",
        session_info[4] or "-"
    ])

    sheet.append([
        "Date",
        str(session_info[5])
    ])

    sheet.append([
        "Start Time",
        str(session_info[6])
    ])

    sheet.append([
        "End Time",
        str(session_info[7])
    ])

    sheet.append([
        "Session Status",
        session_info[8]
    ])

    sheet.append([])

    # ========================================================
    # TABLE HEADERS
    # ========================================================

    sheet.append([
        "Student ID",
        "Student Name",
        "Department",
        "Date",
        "Time",
        "Method",
        "Status",
        "Remarks"
    ])

    # ========================================================
    # RECORDS
    # ========================================================

    for row in rows:

        sheet.append([
            row[0],
            row[1],
            row[2] or "-",
            str(row[3]),
            str(row[4]),
            row[5],
            row[6],
            row[7] or "-"
        ])

    # ========================================================
    # COLUMN WIDTHS
    # ========================================================

    widths = {
        "A": 18,
        "B": 28,
        "C": 20,
        "D": 15,
        "E": 15,
        "F": 20,
        "G": 15,
        "H": 45
    }

    for column, width in widths.items():

        sheet.column_dimensions[
            column
        ].width = width

    sheet.freeze_panes = "A13"

    # ========================================================
    # CREATE FILE
    # ========================================================

    output = io.BytesIO()

    workbook.save(output)

    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name=(
            f"Attendance_Report_{session_id}.xlsx"
        ),
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )


# ============================================================
# EXPORT PDF
# ============================================================

@teacher_attendance.route(
    "/export/pdf/<int:session_id>"
)
def export_pdf(session_id):

    if not teacher_logged_in():
        return redirect(
            url_for("teacher_auth.login")
        )

    teacher_id = session["teacher_id"]

    cursor = mysql.connection.cursor()

    try:

        # ====================================================
        # SESSION INFORMATION
        # ====================================================

        cursor.execute(
            """
            SELECT
                s.id,
                sub.subject_code,
                sub.subject_name,
                sub.semester,
                sub.department,
                s.session_date,
                s.start_time,
                s.end_time,
                s.session_status

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

        session_info = cursor.fetchone()

        if not session_info:

            flash(
                "Attendance session not found.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher_attendance.reports"
                )
            )

        # ====================================================
        # ATTENDANCE RECORDS
        # ====================================================

        cursor.execute(
            """
            SELECT
                students.student_id,
                students.full_name,
                students.department,
                attendance.attendance_date,
                attendance.attendance_time,
                attendance.attendance_method,
                attendance.status

            FROM attendance

            INNER JOIN students
                ON attendance.student_id = students.id

            WHERE attendance.session_id = %s

            ORDER BY students.full_name
            """,
            (
                session_id,
            )
        )

        rows = cursor.fetchall()

    except Exception as e:

        print(
            "PDF EXPORT ERROR:",
            str(e)
        )

        flash(
            f"PDF export error: {e}",
            "danger"
        )

        return redirect(
            url_for(
                "teacher_attendance.report",
                session_id=session_id
            )
        )

    finally:
        cursor.close()

    # ========================================================
    # CREATE PDF
    # ========================================================

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        rightMargin=25,
        leftMargin=25,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()

    elements = []

    elements.append(
        Paragraph(
            "<b>AI Smart Attendance System</b>",
            styles["Title"]
        )
    )

    elements.append(
        Spacer(1, 8)
    )

    elements.append(
        Paragraph(
            "<b>Attendance Report</b>",
            styles["Heading2"]
        )
    )

    elements.append(
        Spacer(1, 10)
    )

    elements.append(
        Paragraph(
            f"<b>Subject Code:</b> {session_info[1]}",
            styles["Normal"]
        )
    )

    elements.append(
        Paragraph(
            f"<b>Subject:</b> {session_info[2]}",
            styles["Normal"]
        )
    )

    elements.append(
        Paragraph(
            f"<b>Semester:</b> {session_info[3]}",
            styles["Normal"]
        )
    )

    elements.append(
        Paragraph(
            f"<b>Department:</b> {session_info[4] or '-'}",
            styles["Normal"]
        )
    )

    elements.append(
        Paragraph(
            f"<b>Date:</b> {session_info[5]}",
            styles["Normal"]
        )
    )

    elements.append(
        Paragraph(
            f"<b>Start:</b> {session_info[6]}",
            styles["Normal"]
        )
    )

    elements.append(
        Paragraph(
            f"<b>End:</b> {session_info[7]}",
            styles["Normal"]
        )
    )

    elements.append(
        Paragraph(
            f"<b>Status:</b> {session_info[8]}",
            styles["Normal"]
        )
    )

    elements.append(
        Spacer(1, 15)
    )

    # ========================================================
    # PDF TABLE
    # ========================================================

    data = [
        [
            "Student ID",
            "Student Name",
            "Department",
            "Date",
            "Time",
            "Method",
            "Status"
        ]
    ]

    for row in rows:

        data.append([
            str(row[0]),
            str(row[1]),
            str(row[2] or "-"),
            str(row[3]),
            str(row[4]),
            str(row[5]),
            str(row[6])
        ])

    if len(data) == 1:

        data.append([
            "-",
            "No attendance record",
            "-",
            "-",
            "-",
            "-",
            "-"
        ])

    table = Table(
        data,
        repeatRows=1
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.darkblue
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold"
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER"
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE"
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    7
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, 0),
                    8
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, 0),
                    8
                )
            ]
        )
    )

    elements.append(table)

    doc.build(elements)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=(
            f"Attendance_Report_{session_id}.pdf"
        ),
        mimetype="application/pdf"
    )