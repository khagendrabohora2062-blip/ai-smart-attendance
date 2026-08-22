
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


attendance_session = Blueprint(
    "attendance_session",
    __name__,
    url_prefix="/attendance-session"
)


# ============================================================
# Attendance Session List
# ============================================================

@attendance_session.route("/")
def index():

    # --------------------------------------------------------
    # Teacher Login Check
    # --------------------------------------------------------

    if "teacher_id" not in session:
        return redirect(
            url_for("teacher_auth.login")
        )

    cursor = mysql.connection.cursor()

    try:

        # ----------------------------------------------------
        # Get Teacher's Sessions
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                attendance_sessions.id,
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

            ORDER BY attendance_sessions.id DESC
        """, (
            session["teacher_id"],
        ))

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

    if "teacher_id" not in session:
        return redirect(
            url_for("teacher_auth.login")
        )

    cursor = mysql.connection.cursor()

    try:

        # ====================================================
        # GET TEACHER ASSIGNED SUBJECTS
        # ====================================================

        cursor.execute("""
            SELECT
                id,
                subject_name,
                semester,
                department

            FROM subjects

            WHERE teacher_id=%s

            ORDER BY semester, subject_name
        """, (
            session["teacher_id"],
        ))

        subjects = cursor.fetchall()

        # ====================================================
        # POST - CREATE SESSION
        # ====================================================

        if request.method == "POST":

            subject_id = request.form.get("subject_id")

            # ------------------------------------------------
            # Subject Selection Validation
            # ------------------------------------------------

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

            # =================================================
            # VERIFY SUBJECT BELONGS TO CURRENT TEACHER
            # =================================================

            cursor.execute("""
                SELECT
                    id,
                    subject_name,
                    semester,
                    department

                FROM subjects

                WHERE id=%s
                AND teacher_id=%s

                LIMIT 1
            """, (
                subject_id,
                session["teacher_id"]
            ))

            subject = cursor.fetchone()

            # ------------------------------------------------
            # Invalid Subject
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
            subject_name = subject[1]
            semester = subject[2]
            department = subject[3]

            # =================================================
            # DUPLICATE SESSION PROTECTION
            #
            # Same:
            #   Teacher
            #   Subject
            #   Date
            #
            # = Only ONE session per day
            #
            # CLOSED session also counts.
            # =================================================

            cursor.execute("""
                SELECT
                    id,
                    session_status

                FROM attendance_sessions

                WHERE teacher_id=%s
                AND subject_id=%s
                AND session_date=CURDATE()

                LIMIT 1
            """, (
                session["teacher_id"],
                subject_db_id
            ))

            existing_session = cursor.fetchone()

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
            # IMPORTANT
            #
            # DO NOT CLOSE OTHER OPEN SESSIONS HERE.
            #
            # Different subjects can have separate sessions.
            #
            # Example:
            #
            # Mathematics → OPEN
            # DBMS        → OPEN
            # Network     → OPEN
            #
            # Actual closing is handled by
            # teacher_attendance.py
            # =================================================

            # =================================================
            # CREATE NEW ATTENDANCE SESSION
            # =================================================

            cursor.execute("""
                INSERT INTO attendance_sessions
                (
                    subject_id,
                    teacher_id,
                    session_date,
                    start_time,
                    session_status
                )

                VALUES
                (
                    %s,
                    %s,
                    CURDATE(),
                    CURTIME(),
                    'OPEN'
                )
            """, (
                subject_db_id,
                session["teacher_id"]
            ))

            new_session_id = cursor.lastrowid

            # =================================================
            # COMMIT
            # =================================================

            mysql.connection.commit()

            # =================================================
            # SUCCESS MESSAGE
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
        # GET REQUEST
        # ====================================================

        return render_template(
            "teacher/create_session.html",
            subjects=subjects
        )

    except Exception as e:

        # ----------------------------------------------------
        # Rollback on Error
        # ----------------------------------------------------

        mysql.connection.rollback()

        print(
            "ATTENDANCE SESSION CREATE ERROR:",
            str(e)
        )

        flash(
            f"Session Error: {e}",
            "danger"
        )

        return redirect(
            url_for(
                "attendance_session.index"
            )
        )

    finally:

        cursor.close()