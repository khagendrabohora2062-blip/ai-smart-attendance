# ============================================================
# STUDENT ROUTINE
# File: routes/student_routine.py
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


student_routine = Blueprint(
    "student_routine",
    __name__,
    url_prefix="/student/routines"
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
            "STUDENT ROUTINE MYSQL ERROR:",
            repr(e)
        )

    raise RuntimeError(
        "MySQL connection is not initialized."
    )


# ============================================================
# STUDENT LOGIN
# ============================================================

def student_required():

    return bool(
        session.get("student_id")
    )


# ============================================================
# LOGIN REDIRECT
# ============================================================

def student_login_redirect():

    for endpoint in (
        "student_auth.login",
        "student.login",
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
# ROUTINE
# ============================================================

@student_routine.route("/")
def index():

    if not student_required():

        flash(
            "Please login as student.",
            "warning"
        )

        return student_login_redirect()


    mysql = None
    cursor = None


    try:

        mysql = get_mysql()

        cursor = mysql.connection.cursor()


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


        return render_template(
            "student/routine.html",
            routines=routines
        )


    except Exception as e:

        print(
            "STUDENT ROUTINE ERROR:",
            repr(e)
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
            "/student/dashboard"
        )


    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass