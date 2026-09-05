# ============================================================
# TEACHER SYLLABUS
# File:
# routes/teacher_syllabus.py
# ============================================================

import os

from io import BytesIO

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    session,
    current_app,
    send_file,
    send_from_directory,
    abort
)

from extensions import mysql


# ============================================================
# BLUEPRINT
# ============================================================

teacher_syllabus = Blueprint(
    "teacher_syllabus",
    __name__,
    url_prefix="/teacher/syllabus"
)


# ============================================================
# TEACHER LOGIN CHECK
# ============================================================

def teacher_logged_in():

    return "teacher_id" in session


# ============================================================
# SYLLABUS UPLOAD FOLDER
# ============================================================

def get_syllabus_upload_folder():

    folder = os.path.join(
        current_app.root_path,
        "static",
        "uploads",
        "syllabus"
    )

    os.makedirs(
        folder,
        exist_ok=True
    )

    return folder


# ============================================================
# GET SYLLABUS FILE DATA
# ============================================================

def _get_syllabus_file_data(filename):

    if not filename:
        return None, None

    safe_name = os.path.basename(
        str(filename)
        .replace("\\", "/")
        .strip()
    )

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                file_data,
                file_path
            FROM syllabus
            WHERE file_name = %s
            LIMIT 1
            """,
            (safe_name,)
        )

        result = cursor.fetchone()

    finally:

        try:
            cursor.close()
        except Exception:
            pass

    if not result:

        return None, None

    return result[0], result[1]


# ============================================================
# TEACHER SYLLABUS INDEX
# ============================================================

@teacher_syllabus.route("/")
def index():

    # --------------------------------------------------------
    # LOGIN CHECK
    # --------------------------------------------------------

    if not teacher_logged_in():

        return redirect(
            url_for("teacher_auth.login")
        )

    # --------------------------------------------------------
    # SESSION TEACHER ID
    #
    # IMPORTANT:
    # teacher_auth.py stores teachers.id in session.
    # --------------------------------------------------------

    teacher_id = session["teacher_id"]

    cursor = mysql.connection.cursor()

    teacher = None
    syllabuses = []

    try:

        # ====================================================
        # CURRENT TEACHER
        # ====================================================

        cursor.execute(
            """
            SELECT
                id,
                teacher_id,
                full_name,
                email,
                department
            FROM teachers
            WHERE id = %s
            LIMIT 1
            """,
            (teacher_id,)
        )

        teacher = cursor.fetchone()

        # ----------------------------------------------------
        # TEACHER NOT FOUND
        # ----------------------------------------------------

        if not teacher:

            session.clear()

            return redirect(
                url_for("teacher_auth.login")
            )

        # ----------------------------------------------------
        # TEACHER DEPARTMENT
        # ----------------------------------------------------

        department = teacher[4]

        # ====================================================
        # GET SYLLABUS
        #
        # IMPORTANT:
        #
        # subjects.teacher_id stores teachers.id
        # and session["teacher_id"] is also teachers.id.
        #
        # LOWER(TRIM()) is kept from the original project
        # so department formatting does not hide syllabuses.
        # ====================================================

        cursor.execute(
            """
            SELECT DISTINCT
                s.id,
                s.department,
                s.semester,
                s.subject_id,
                sub.subject_code,
                sub.subject_name,
                s.title,
                s.description,
                s.file_name,
                s.file_path,
                s.created_at,
                s.updated_at

            FROM syllabus s

            LEFT JOIN subjects sub
                ON s.subject_id = sub.id

            WHERE
                LOWER(TRIM(s.department))
                =
                LOWER(TRIM(%s))

            AND
                (
                    sub.teacher_id = %s
                    OR sub.teacher_id IS NULL
                )

            ORDER BY
                s.semester ASC,
                sub.subject_code ASC,
                s.id DESC
            """,
            (
                department,
                teacher_id
            )
        )

        syllabuses = cursor.fetchall() or []

    except Exception as e:

        print(
            "TEACHER SYLLABUS MYSQL ERROR:",
            repr(e)
        )

        syllabuses = []

    finally:

        try:
            cursor.close()
        except Exception:
            pass

    # ========================================================
    # TEMPLATE
    # ========================================================

    return render_template(
        "teacher/syllabus/index.html",
        teacher=teacher,
        syllabuses=syllabuses,
        # Keep both names for template compatibility
        syllabi=syllabuses,
        department=teacher[4] if teacher else ""
    )


# ============================================================
# SAFE FILENAME
# ============================================================

def _safe_syllabus_filename(filename):

    if not filename:

        return ""

    return os.path.basename(
        str(filename)
        .replace("\\", "/")
        .strip()
    )


# ============================================================
# VIEW SYLLABUS PDF
# ============================================================

@teacher_syllabus.route("/view/<path:filename>")
def view(filename):

    # --------------------------------------------------------
    # LOGIN CHECK
    # --------------------------------------------------------

    if not teacher_logged_in():

        return redirect(
            url_for("teacher_auth.login")
        )

    # --------------------------------------------------------
    # SAFE FILENAME
    # --------------------------------------------------------

    safe_name = _safe_syllabus_filename(
        filename
    )

    if not safe_name:

        abort(404)

    if not safe_name.lower().endswith(".pdf"):

        abort(404)

    # ========================================================
    # FIRST: GET PDF FROM DATABASE
    #
    # This is the permanent solution for Render.
    # ========================================================

    file_data, file_path = _get_syllabus_file_data(
        safe_name
    )

    if file_data:

        return send_file(
            BytesIO(bytes(file_data)),
            mimetype="application/pdf",
            as_attachment=False,
            download_name=safe_name
        )

    # ========================================================
    # FALLBACK: PHYSICAL FILE
    # ========================================================

    folder = get_syllabus_upload_folder()

    physical = os.path.join(
        folder,
        safe_name
    )

    if os.path.isfile(physical):

        return send_from_directory(
            folder,
            safe_name,
            as_attachment=False,
            download_name=safe_name
        )

    # --------------------------------------------------------
    # TRY DATABASE FILE PATH
    # --------------------------------------------------------

    if file_path:

        physical_path = str(file_path)

        physical_path = physical_path.replace(
            "\\",
            "/"
        )

        # Handle:
        # uploads/syllabus/file.pdf
        # static/uploads/syllabus/file.pdf

        possible_paths = [

            physical_path,

            os.path.join(
                current_app.root_path,
                physical_path
            ),

            os.path.join(
                current_app.root_path,
                "static",
                physical_path
            ),

            os.path.join(
                current_app.root_path,
                "static",
                "uploads",
                "syllabus",
                safe_name
            )
        ]

        for path in possible_paths:

            if os.path.isfile(path):

                return send_file(
                    path,
                    mimetype="application/pdf",
                    as_attachment=False,
                    download_name=safe_name
                )

    # --------------------------------------------------------
    # NOT FOUND
    # --------------------------------------------------------

    abort(404)


# ============================================================
# DOWNLOAD SYLLABUS PDF
# ============================================================

@teacher_syllabus.route("/download/<path:filename>")
def download(filename):

    # --------------------------------------------------------
    # LOGIN CHECK
    # --------------------------------------------------------

    if not teacher_logged_in():

        return redirect(
            url_for("teacher_auth.login")
        )

    # --------------------------------------------------------
    # SAFE FILENAME
    # --------------------------------------------------------

    safe_name = _safe_syllabus_filename(
        filename
    )

    if not safe_name:

        abort(404)

    if not safe_name.lower().endswith(".pdf"):

        abort(404)

    # ========================================================
    # FIRST: DATABASE FILE
    # ========================================================

    file_data, file_path = _get_syllabus_file_data(
        safe_name
    )

    if file_data:

        return send_file(
            BytesIO(bytes(file_data)),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=safe_name
        )

    # ========================================================
    # FALLBACK: PHYSICAL FILE
    # ========================================================

    folder = get_syllabus_upload_folder()

    physical = os.path.join(
        folder,
        safe_name
    )

    if os.path.isfile(physical):

        return send_from_directory(
            folder,
            safe_name,
            as_attachment=True,
            download_name=safe_name
        )

    # --------------------------------------------------------
    # TRY DATABASE FILE PATH
    # --------------------------------------------------------

    if file_path:

        physical_path = str(file_path)

        physical_path = physical_path.replace(
            "\\",
            "/"
        )

        possible_paths = [

            physical_path,

            os.path.join(
                current_app.root_path,
                physical_path
            ),

            os.path.join(
                current_app.root_path,
                "static",
                physical_path
            ),

            os.path.join(
                current_app.root_path,
                "static",
                "uploads",
                "syllabus",
                safe_name
            )
        ]

        for path in possible_paths:

            if os.path.isfile(path):

                return send_file(
                    path,
                    mimetype="application/pdf",
                    as_attachment=True,
                    download_name=safe_name
                )

    # --------------------------------------------------------
    # NOT FOUND
    # --------------------------------------------------------

    abort(404)