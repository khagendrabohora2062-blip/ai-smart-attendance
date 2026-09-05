# ============================================================
# STUDENT ROUTINE
# File: routes/student_routine.py
# ============================================================

import os

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    session,
    current_app,
    send_from_directory,
    abort
)

from extensions import mysql


# ============================================================
# BLUEPRINT
# ============================================================

student_routine = Blueprint(
    "student_routine",
    __name__,
    url_prefix="/student/routines"
)


# ============================================================
# MYSQL HELPER
# ============================================================

def get_mysql():

    mysql_instance = current_app.extensions.get("mysql")

    if mysql_instance is not None:
        return mysql_instance

    try:

        from app import mysql as app_mysql

        if app_mysql is not None:
            return app_mysql

    except Exception as e:

        print(
            "STUDENT ROUTINE MYSQL IMPORT ERROR:",
            repr(e)
        )

    raise RuntimeError(
        "MySQL connection is not initialized."
    )


# ============================================================
# STUDENT LOGIN CHECK
# ============================================================

def student_required():

    return bool(
        session.get("student_db_id")
    )


# ============================================================
# STUDENT LOGIN REDIRECT
# ============================================================

def student_login_redirect():

    try:

        return redirect(
            url_for(
                "student_auth.login"
            )
        )

    except Exception:

        return redirect("/student/login")


# ============================================================
# ROUTINE UPLOAD FOLDER
# ============================================================

def get_routine_upload_folder():

    folder = os.path.join(
        current_app.root_path,
        "static",
        "uploads",
        "routines"
    )

    os.makedirs(
        folder,
        exist_ok=True
    )

    return folder


# ============================================================
# SAFE ROUTINE FILENAME
# ============================================================

def safe_routine_filename(filename):

    if not filename:
        return ""

    filename = str(filename)

    filename = filename.replace(
        "\\",
        "/"
    )

    filename = os.path.basename(
        filename
    )

    filename = filename.strip()

    return filename


# ============================================================
# NORMALIZE VALUE
# ============================================================

def normalize_value(value):

    if value is None:
        return ""

    return str(value).strip().lower()


# ============================================================
# NORMALIZE SEMESTER
# ============================================================

def normalize_semester(value):

    if value is None:
        return ""

    value = str(value).strip().lower()

    if not value:
        return ""

    # --------------------------------------------------------
    # Direct numeric semester
    # --------------------------------------------------------

    if value in {
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8"
    }:

        return value

    # --------------------------------------------------------
    # Semester 1 / Semester 1st etc.
    # --------------------------------------------------------

    semester_map = {

        "semester 1": "1",
        "semester 1st": "1",
        "1st semester": "1",

        "semester 2": "2",
        "semester 2nd": "2",
        "2nd semester": "2",

        "semester 3": "3",
        "semester 3rd": "3",
        "3rd semester": "3",

        "semester 4": "4",
        "semester 4th": "4",
        "4th semester": "4",

        "semester 5": "5",
        "semester 5th": "5",
        "5th semester": "5",

        "semester 6": "6",
        "semester 6th": "6",
        "6th semester": "6",

        "semester 7": "7",
        "semester 7th": "7",
        "7th semester": "7",

        "semester 8": "8",
        "semester 8th": "8",
        "8th semester": "8"
    }

    if value in semester_map:
        return semester_map[value]

    # --------------------------------------------------------
    # Extract numeric semester if possible
    # --------------------------------------------------------

    for number in (
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8"
    ):

        if number in value:

            return number

    return value


# ============================================================
# GET CURRENT STUDENT
# ============================================================

def get_current_student():

    student_db_id = session.get(
        "student_db_id"
    )

    if not student_db_id:
        return None

    mysql_instance = None
    cursor = None

    try:

        mysql_instance = get_mysql()

        cursor = mysql_instance.connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                student_id,
                full_name,
                email,
                phone,
                department,
                semester,
                section,
                photo
            FROM students
            WHERE id = %s
            LIMIT 1
            """,
            (
                student_db_id,
            )
        )

        return cursor.fetchone()

    except Exception as e:

        print(
            "GET CURRENT STUDENT ROUTINE ERROR:",
            repr(e)
        )

        return None

    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass


# ============================================================
# GET ROUTINE
# ============================================================

@student_routine.route("/")
def index():

    # --------------------------------------------------------
    # LOGIN
    # --------------------------------------------------------

    if not student_required():

        flash(
            "Please login as student.",
            "warning"
        )

        return student_login_redirect()

    mysql_instance = None
    cursor = None

    try:

        # ----------------------------------------------------
        # MYSQL
        # ----------------------------------------------------

        mysql_instance = get_mysql()

        cursor = mysql_instance.connection.cursor()

        # ----------------------------------------------------
        # CURRENT STUDENT
        # ----------------------------------------------------

        student_db_id = session.get(
            "student_db_id"
        )

        cursor.execute(
            """
            SELECT
                id,
                student_id,
                full_name,
                email,
                phone,
                department,
                semester,
                section,
                photo
            FROM students
            WHERE id = %s
            LIMIT 1
            """,
            (
                student_db_id,
            )
        )

        student = cursor.fetchone()

        # ----------------------------------------------------
        # STUDENT NOT FOUND
        # ----------------------------------------------------

        if not student:

            session.clear()

            flash(
                "Student account not found. Please login again.",
                "danger"
            )

            return redirect(
                url_for(
                    "student_auth.login"
                )
            )

        # ----------------------------------------------------
        # STUDENT DETAILS
        # ----------------------------------------------------

        student_department = (
            str(student[5]).strip()
            if student[5] is not None
            else ""
        )

        student_semester = (
            str(student[6]).strip()
            if student[6] is not None
            else ""
        )

        normalized_department = normalize_value(
            student_department
        )

        normalized_semester = normalize_semester(
            student_semester
        )

        # ----------------------------------------------------
        # GET ALL ROUTINES
        #
        # We intentionally fetch all routines first.
        # Filtering is done in Python so that:
        #
        # "1"
        # "Semester 1"
        # "Semester 1st"
        #
        # can all match the same semester.
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
                uploaded_at DESC,
                id DESC
            """
        )

        all_routines = cursor.fetchall() or []

        routines = []

        # ----------------------------------------------------
        # FILTER ROUTINES FOR CURRENT STUDENT
        # ----------------------------------------------------

        for routine in all_routines:

            routine_department = (
                str(routine[3]).strip()
                if routine[3] is not None
                else ""
            )

            routine_semester = (
                str(routine[4]).strip()
                if routine[4] is not None
                else ""
            )

            normalized_routine_department = normalize_value(
                routine_department
            )

            normalized_routine_semester = normalize_semester(
                routine_semester
            )

            # ------------------------------------------------
            # DEPARTMENT MATCH
            #
            # Empty department = available to everyone
            # ------------------------------------------------

            department_matches = (

                not normalized_routine_department

                or

                not normalized_department

                or

                normalized_routine_department
                ==
                normalized_department
            )

            # ------------------------------------------------
            # SEMESTER MATCH
            #
            # Empty semester = available to everyone
            # ------------------------------------------------

            semester_matches = (

                not normalized_routine_semester

                or

                not normalized_semester

                or

                normalized_routine_semester
                ==
                normalized_semester
            )

            if (
                department_matches
                and
                semester_matches
            ):

                routines.append(
                    routine
                )

        # ----------------------------------------------------
        # RENDER
        # ----------------------------------------------------

        return render_template(
            "student/routine.html",
            routines=routines,
            student=student,
            student_department=student_department,
            student_semester=student_semester
        )

    except Exception as e:

        print(
            "STUDENT ROUTINE ERROR:",
            repr(e)
        )

        if mysql_instance:

            try:

                mysql_instance.connection.rollback()

            except Exception:

                pass

        flash(
            "Unable to load class routine. Please try again.",
            "danger"
        )

        return redirect(
            url_for(
                "student_auth.dashboard"
            )
        )

    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass


# ============================================================
# VIEW ROUTINE
# ============================================================

@student_routine.route(
    "/view/<path:filename>"
)
def view(filename):

    # --------------------------------------------------------
    # LOGIN
    # --------------------------------------------------------

    if not student_required():

        return student_login_redirect()

    # --------------------------------------------------------
    # SAFE FILENAME
    # --------------------------------------------------------

    safe_name = safe_routine_filename(
        filename
    )

    if not safe_name:

        abort(404)

    # --------------------------------------------------------
    # ONLY ALLOWED IMAGE EXTENSIONS
    # --------------------------------------------------------

    allowed_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp"
    }

    extension = os.path.splitext(
        safe_name
    )[1].lower()

    if extension not in allowed_extensions:

        abort(404)

    # --------------------------------------------------------
    # FILE PATH
    # --------------------------------------------------------

    folder = get_routine_upload_folder()

    file_path = os.path.join(
        folder,
        safe_name
    )

    # --------------------------------------------------------
    # FILE NOT FOUND
    # --------------------------------------------------------

    if not os.path.isfile(file_path):

        return render_template(
            "student/routine.html",
            routines=[],
            student=get_current_student(),
            student_department="",
            student_semester="",
            file_missing=True,
            missing_file=safe_name
        ), 404

    # --------------------------------------------------------
    # SERVE FILE
    # --------------------------------------------------------

    return send_from_directory(
        folder,
        safe_name,
        as_attachment=False
    )


# ============================================================
# DOWNLOAD ROUTINE
# ============================================================

@student_routine.route(
    "/download/<path:filename>"
)
def download(filename):

    # --------------------------------------------------------
    # LOGIN
    # --------------------------------------------------------

    if not student_required():

        return student_login_redirect()

    # --------------------------------------------------------
    # SAFE FILENAME
    # --------------------------------------------------------

    safe_name = safe_routine_filename(
        filename
    )

    if not safe_name:

        abort(404)

    # --------------------------------------------------------
    # ONLY ALLOWED IMAGE EXTENSIONS
    # --------------------------------------------------------

    allowed_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp"
    }

    extension = os.path.splitext(
        safe_name
    )[1].lower()

    if extension not in allowed_extensions:

        abort(404)

    # --------------------------------------------------------
    # FILE PATH
    # --------------------------------------------------------

    folder = get_routine_upload_folder()

    file_path = os.path.join(
        folder,
        safe_name
    )

    # --------------------------------------------------------
    # FILE NOT FOUND
    # --------------------------------------------------------

    if not os.path.isfile(file_path):

        flash(
            "Routine file is missing from the server.",
            "danger"
        )

        return redirect(
            url_for(
                "student_routine.index"
            )
        )

    # --------------------------------------------------------
    # DOWNLOAD
    # --------------------------------------------------------

    return send_from_directory(
        folder,
        safe_name,
        as_attachment=True
    )