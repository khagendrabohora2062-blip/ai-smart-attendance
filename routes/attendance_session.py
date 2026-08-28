from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

from extensions import mysql

import uuid


# ============================================================
# Attendance Session Blueprint
# ============================================================

attendance_session = Blueprint(
    "attendance_session",
    __name__,
    url_prefix="/attendance-session"
)


# ============================================================
# Teacher Login Check
# ============================================================

def teacher_logged_in():
    return "teacher_id" in session


# ============================================================
# Generate Unique Attendance Session ID
# ============================================================

def generate_session_id(cursor):
    """
    attendance_sessions.id is currently NOT AUTO_INCREMENT.

    Therefore a unique positive integer ID is generated
    manually before INSERT.
    """

    while True:

        # Generate a positive 32-bit integer
        new_id = uuid.uuid4().int % 2147483647

        # ID must be greater than zero
        if new_id <= 0:
            continue

        cursor.execute(
            """
            SELECT id
            FROM attendance_sessions
            WHERE id=%s
            LIMIT 1
            """,
            (new_id,)
        )

        if cursor.fetchone() is None:
            return new_id


# ============================================================
# Attendance Session List
# ============================================================

@attendance_session.route("/")
def index():

    # --------------------------------------------------------
    # Teacher Login Check
    # --------------------------------------------------------

    if not teacher_logged_in():
        return redirect(
            url_for("teacher_auth.login")
        )

    cursor = mysql.connection.cursor()

    try:

        teacher_id = session["teacher_id"]

        # ----------------------------------------------------
        # Get Teacher's Sessions
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                attendance_sessions.id,
                subjects.subject_code,
                subjects.subject_name,
                subjects.semester,
                subjects.department,
                attendance_sessions.session_date,
                attendance_sessions.start_time,
                attendance_sessions.end_time,
                attendance_sessions.session_status

            FROM attendance_sessions

            INNER JOIN subjects
                ON attendance_sessions.subject_id = subjects.id

            WHERE attendance_sessions.teacher_id=%s

            ORDER BY
                attendance_sessions.session_date DESC,
                attendance_sessions.id DESC
            """,
            (teacher_id,)
        )

        sessions = cursor.fetchall()

    except Exception as e:

        print(
            "ATTENDANCE SESSION LIST ERROR:",
            str(e)
        )

        flash(
            f"Unable to load attendance sessions: {e}",
            "danger"
        )

        sessions = []

    finally:
        cursor.close()

    return render_template(
        "teacher/attendance_sessions.html",
        sessions=sessions
    )


# ============================================================
# Create Attendance Session
# ============================================================

@attendance_session.route(
    "/create",
    methods=["GET", "POST"]
)
def create():

    # --------------------------------------------------------
    # Teacher Login Check
    # --------------------------------------------------------

    if not teacher_logged_in():
        return redirect(
            url_for("teacher_auth.login")
        )

    cursor = mysql.connection.cursor()

    try:

        # ----------------------------------------------------
        # Current Teacher
        # ----------------------------------------------------

        teacher_id = session["teacher_id"]

        # ----------------------------------------------------
        # Get Teacher Assigned Subjects
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                subject_code,
                subject_name,
                semester,
                department

            FROM subjects

            WHERE teacher_id=%s

            ORDER BY
                semester,
                subject_name
            """,
            (teacher_id,)
        )

        subjects = cursor.fetchall()

        # ====================================================
        # POST
        # ====================================================

        if request.method == "POST":

            # ------------------------------------------------
            # Get Subject ID
            # ------------------------------------------------

            subject_id = request.form.get(
                "subject_id"
            )

            if not subject_id:

                flash(
                    "Please select a subject.",
                    "warning"
                )

                return redirect(
                    url_for(
                        "attendance_session.create"
                    )
                )

            # ------------------------------------------------
            # Validate Subject ID
            # ------------------------------------------------

            try:

                subject_id = int(subject_id)

            except (TypeError, ValueError):

                flash(
                    "Invalid subject selected.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "attendance_session.create"
                    )
                )

            # =================================================
            # Verify Subject Belongs To Teacher
            # =================================================

            cursor.execute(
                """
                SELECT
                    id,
                    subject_code,
                    subject_name,
                    semester,
                    department

                FROM subjects

                WHERE id=%s
                AND teacher_id=%s

                LIMIT 1
                """,
                (
                    subject_id,
                    teacher_id
                )
            )

            subject = cursor.fetchone()

            # ------------------------------------------------
            # Subject Not Found
            # ------------------------------------------------

            if not subject:

                flash(
                    "Invalid subject selected or this subject "
                    "is not assigned to you.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "attendance_session.create"
                    )
                )

            # ------------------------------------------------
            # Subject Information
            # ------------------------------------------------

            subject_db_id = subject[0]
            subject_code = subject[1]
            subject_name = subject[2]
            semester = subject[3]
            department = subject[4]

            # =================================================
            # Check Today's Existing Session
            # =================================================

            cursor.execute(
                """
                SELECT
                    id,
                    session_status

                FROM attendance_sessions

                WHERE teacher_id=%s
                AND subject_id=%s
                AND session_date=CURDATE()

                LIMIT 1
                """,
                (
                    teacher_id,
                    subject_db_id
                )
            )

            existing_session = cursor.fetchone()

            # ------------------------------------------------
            # Existing Session Found
            # ------------------------------------------------

            if existing_session:

                existing_session_id = existing_session[0]
                existing_status = existing_session[1]

                if existing_status == "OPEN":

                    flash(
                        f"{subject_name} already has an "
                        f"OPEN attendance session today.",
                        "warning"
                    )

                else:

                    flash(
                        f"Attendance for {subject_name} "
                        f"has already been completed today.",
                        "warning"
                    )

                return redirect(
                    url_for(
                        "attendance_session.index"
                    )
                )

            # =================================================
            # Generate Manual Session ID
            # =================================================

            new_session_id = generate_session_id(
                cursor
            )

            # =================================================
            # Create Attendance Session
            # =================================================

            cursor.execute(
                """
                INSERT INTO attendance_sessions
                (
                    id,
                    subject_id,
                    teacher_id,
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
                    CURDATE(),
                    CURTIME(),
                    NULL,
                    'OPEN'
                )
                """,
                (
                    new_session_id,
                    subject_db_id,
                    teacher_id
                )
            )

            # =================================================
            # Commit
            # =================================================

            mysql.connection.commit()

            # =================================================
            # Success
            # =================================================

            flash(
                f"{subject_name} attendance session "
                f"started successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "attendance_session.index"
                )
            )

        # ====================================================
        # GET
        # ====================================================

        return render_template(
            "teacher/create_session.html",
            subjects=subjects
        )

    except Exception as e:

        # ----------------------------------------------------
        # Rollback
        # ----------------------------------------------------

        mysql.connection.rollback()

        print(
            "ATTENDANCE SESSION CREATE ERROR:",
            str(e)
        )

        flash(
            f"Error opening attendance session: {e}",
            "danger"
        )

        return redirect(
            url_for(
                "attendance_session.index"
            )
        )

    finally:

        cursor.close()


# ============================================================
# Close Attendance Session
# ============================================================

@attendance_session.route(
    "/close/<int:session_id>",
    methods=["POST"]
)
def close(session_id):

    # --------------------------------------------------------
    # Teacher Login Check
    # --------------------------------------------------------

    if not teacher_logged_in():
        return redirect(
            url_for("teacher_auth.login")
        )

    cursor = mysql.connection.cursor()

    try:

        teacher_id = session["teacher_id"]

        # ====================================================
        # Find Session
        # ====================================================

        cursor.execute(
            """
            SELECT
                id,
                subject_id,
                session_status

            FROM attendance_sessions

            WHERE id=%s
            AND teacher_id=%s

            LIMIT 1
            """,
            (
                session_id,
                teacher_id
            )
        )

        attendance = cursor.fetchone()

        # ----------------------------------------------------
        # Session Not Found
        # ----------------------------------------------------

        if not attendance:

            flash(
                "Attendance session not found.",
                "danger"
            )

            return redirect(
                url_for(
                    "attendance_session.index"
                )
            )

        # ====================================================
        # Check Session Status
        # ====================================================

        current_status = attendance[2]

        if current_status == "CLOSED":

            flash(
                "This attendance session is already closed.",
                "warning"
            )

            return redirect(
                url_for(
                    "attendance_session.index"
                )
            )

        # ====================================================
        # Close Session
        # ====================================================

        cursor.execute(
            """
            UPDATE attendance_sessions

            SET
                end_time=CURTIME(),
                session_status='CLOSED'

            WHERE id=%s
            AND teacher_id=%s
            """,
            (
                session_id,
                teacher_id
            )
        )

        mysql.connection.commit()

        flash(
            "Attendance session closed successfully.",
            "success"
        )

    except Exception as e:

        mysql.connection.rollback()

        print(
            "ATTENDANCE SESSION CLOSE ERROR:",
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
            "attendance_session.index"
        )
    )