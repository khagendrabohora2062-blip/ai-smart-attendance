# ============================================================
# TEACHER ROUTINE
#
# File:
# routes/teacher_routine.py
# ============================================================

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    session,
    current_app
)

from jinja2 import TemplateNotFound


# ============================================================
# BLUEPRINT
# ============================================================

teacher_routine = Blueprint(
    "teacher_routine",
    __name__,
    url_prefix="/teacher/routines"
)


# ============================================================
# MYSQL HELPER
# ============================================================

def get_mysql():

    mysql = current_app.extensions.get("mysql")

    if mysql is not None:
        return mysql

    try:

        from app import mysql as app_mysql

        if app_mysql is not None:
            return app_mysql

    except Exception as e:

        print(
            "TEACHER ROUTINE MYSQL IMPORT ERROR:",
            repr(e)
        )

    raise RuntimeError(
        "MySQL connection is not initialized."
    )


# ============================================================
# TEACHER LOGIN CHECK
# ============================================================

def teacher_required():

    return bool(
        session.get("teacher_id")
    )


# ============================================================
# LOGIN REDIRECT
# ============================================================

def teacher_login_redirect():

    possible_endpoints = [
        "teacher_auth.login",
        "teacher.login",
        "auth.login"
    ]

    for endpoint in possible_endpoints:

        try:

            return redirect(
                url_for(endpoint)
            )

        except Exception:
            continue

    return redirect("/login")


# ============================================================
# ROUTINE PAGE
# ============================================================

@teacher_routine.route("/")
def index():

    # --------------------------------------------------------
    # LOGIN CHECK
    # --------------------------------------------------------

    if not teacher_required():

        flash(
            "Please login as teacher.",
            "warning"
        )

        return teacher_login_redirect()


    mysql = None
    cursor = None

    try:

        mysql = get_mysql()

        cursor = mysql.connection.cursor()


        # ====================================================
        # GET LOGGED-IN TEACHER
        # ====================================================

        logged_teacher = session.get("teacher_id")


        print(
            "TEACHER ROUTINE SESSION:",
            logged_teacher
        )


        # ====================================================
        # FIND TEACHER DATABASE ID
        # ====================================================

        cursor.execute(
            """
            SELECT
                id,
                teacher_id,
                full_name,
                department
            FROM teachers
            WHERE id = %s
               OR teacher_id = %s
            LIMIT 1
            """,
            (
                logged_teacher,
                logged_teacher
            )
        )

        teacher = cursor.fetchone()


        if not teacher:

            flash(
                "Teacher account was not found.",
                "danger"
            )

            return redirect("/teacher/dashboard")


        teacher_db_id = teacher[0]


        # ====================================================
        # GET TEACHER ROUTINE
        # ====================================================

        cursor.execute(
            """
            SELECT

                r.id,

                r.semester,

                r.department,

                r.section,

                r.day,

                r.start_time,

                r.end_time,

                r.room,

                r.subject_id,

                s.subject_code,

                s.subject_name

            FROM routines r

            LEFT JOIN subjects s
                ON r.subject_id = s.id

            WHERE r.teacher_id = %s

            ORDER BY

                r.semester ASC,

                r.department ASC,

                CASE r.day

                    WHEN 'Sunday' THEN 1
                    WHEN 'Monday' THEN 2
                    WHEN 'Tuesday' THEN 3
                    WHEN 'Wednesday' THEN 4
                    WHEN 'Thursday' THEN 5
                    WHEN 'Friday' THEN 6
                    WHEN 'Saturday' THEN 7

                    ELSE 8

                END ASC,

                r.start_time ASC
            """,
            (
                teacher_db_id,
            )
        )

        routines = cursor.fetchall()


        print(
            "TEACHER ROUTINES LOADED:",
            len(routines)
        )


        # ====================================================
        # GET DISTINCT SEMESTERS
        # ====================================================

        cursor.execute(
            """
            SELECT DISTINCT
                r.semester

            FROM routines r

            WHERE r.teacher_id = %s

            ORDER BY
                r.semester ASC
            """,
            (
                teacher_db_id,
            )
        )

        semesters = cursor.fetchall()


        # ====================================================
        # GET DISTINCT DEPARTMENTS
        # ====================================================

        cursor.execute(
            """
            SELECT DISTINCT
                TRIM(r.department)

            FROM routines r

            WHERE r.teacher_id = %s

              AND r.department IS NOT NULL

              AND TRIM(r.department) <> ''

            ORDER BY
                TRIM(r.department) ASC
            """,
            (
                teacher_db_id,
            )
        )

        departments = cursor.fetchall()


        # ====================================================
        # TEMPLATE
        # ====================================================

        possible_templates = [

            "teacher/routine.html",

            "teacher/routines.html",

            "teacher_routine.html"

        ]


        for template_name in possible_templates:

            try:

                current_app.jinja_env.get_template(
                    template_name
                )

                return render_template(
                    template_name,

                    routines=routines,

                    semesters=semesters,

                    departments=departments,

                    teacher=teacher

                )

            except TemplateNotFound:

                continue


        raise TemplateNotFound(
            "teacher/routine.html"
        )


    except Exception as e:

        print(
            "================================================"
        )

        print(
            "TEACHER ROUTINE ERROR:",
            repr(e)
        )

        print(
            "================================================"
        )

        flash(
            f"Unable to load routine: {str(e)}",
            "danger"
        )

        return redirect("/teacher/dashboard")


    finally:

        if cursor is not None:

            try:
                cursor.close()

            except Exception:
                pass