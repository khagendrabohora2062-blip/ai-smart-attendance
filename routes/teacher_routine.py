# ============================================================
# TEACHER ROUTINE
# File: routes/teacher_routine.py
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


# ============================================================
# BLUEPRINT
# ============================================================

teacher_routine = Blueprint(
    "teacher_routine",
    __name__,
    url_prefix="/teacher/routines"
)


# ============================================================
# MYSQL
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
            "TEACHER ROUTINE MYSQL ERROR:",
            repr(e)
        )

    raise RuntimeError(
        "MySQL connection is not initialized."
    )


# ============================================================
# TEACHER LOGIN
# ============================================================

def teacher_required():

    return bool(
        session.get("teacher_id")
    )


# ============================================================
# LOGIN REDIRECT
# ============================================================

def teacher_login_redirect():

    for endpoint in (
        "teacher_auth.login",
        "teacher.login",
        "auth.login"
    ):

        try:

            return redirect(
                url_for(endpoint)
            )

        except Exception:

            continue

    return redirect("/login")


# ============================================================
# TEACHER ROUTINE
# ============================================================

@teacher_routine.route("/")
def index():

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


        # ----------------------------------------------------
        # CURRENT + RECENT ROUTINES
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                title,
                academic_year,
                department,
                semester,
                description,
                photo,
                is_active,
                uploaded_at
            FROM routine_uploads
            ORDER BY
                is_active DESC,
                uploaded_at DESC
            """
        )

        routines = cursor.fetchall()


        # ----------------------------------------------------
        # TEACHER INFO
        # ----------------------------------------------------

        teacher = None

        teacher_id = session.get(
            "teacher_id"
        )


        try:

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
                    teacher_id,
                    teacher_id
                )
            )

            teacher = cursor.fetchone()

        except Exception as e:

            print(
                "TEACHER INFO ERROR:",
                repr(e)
            )


        # ----------------------------------------------------
        # RENDER
        # ----------------------------------------------------

        return render_template(
            "teacher/routine.html",
            routines=routines,
            teacher=teacher
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


        if mysql:

            try:
                mysql.connection.rollback()
            except Exception:
                pass


        flash(
            f"Unable to load routines: {str(e)}",
            "danger"
        )


        return redirect(
            "/teacher/dashboard"
        )


    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass


# ============================================================
# END
# ============================================================