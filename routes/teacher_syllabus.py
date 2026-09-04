# ============================================================
# TEACHER SYLLABUS
# File:
# routes/teacher_syllabus.py
# ============================================================

import os

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    session,
    current_app,
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


        if not teacher:

            session.clear()

            return redirect(
                url_for("teacher_auth.login")
            )


        department = teacher[4]


        # ====================================================
        # GET SYLLABUS
        #
        # Show syllabus for:
        # 1. Teacher's department
        # 2. Teacher's assigned subjects
        #
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
            "TEACHER SYLLABUS ERROR:",
            repr(e)
        )

        syllabuses = []


    finally:

        cursor.close()


    return render_template(
        "teacher/syllabus/index.html",
        teacher=teacher,
        syllabuses=syllabuses
    )


# ============================================================

def _safe_syllabus_filename(filename):
    if not filename:
        return ""
    return os.path.basename(str(filename).replace("\\", "/").strip())


def _find_syllabus_file(filename):
    safe_name = _safe_syllabus_filename(filename)
    if not safe_name:
        return None, None

    folder = get_syllabus_upload_folder()
    physical = os.path.join(folder, safe_name)

    if os.path.isfile(physical):
        return folder, safe_name

    return None, None

# ==========================================================
# VIEW / DOWNLOAD SYLLABUS
# ==========================================================

@teacher_syllabus.route("/view/<path:filename>")
def view(filename):
    if not teacher_logged_in():
        return redirect(url_for("teacher_auth.login"))

    safe_name = _safe_syllabus_filename(filename)
    folder = get_syllabus_upload_folder()

    if not safe_name.lower().endswith(".pdf"):
        abort(404)

    # The database stores paths such as uploads/syllabus/name.pdf,
    # while the real file is in static/uploads/syllabus/name.pdf.
    # Match by basename so both formats work.
    cursor = mysql.connection.cursor()
    try:
        cursor.execute(
            """
            SELECT file_name
            FROM syllabus
            WHERE file_name = %s
               OR file_path = %s
               OR file_path = %s
            LIMIT 1
            """,
            (
                safe_name,
                filename.replace("\\", "/").lstrip("/"),
                "uploads/syllabus/" + safe_name,
            ),
        )
        row = cursor.fetchone()
    finally:
        try:
            cursor.close()
        except Exception:
            pass

    if not row:
        abort(404)

    safe_name = _safe_syllabus_filename(row[0])
    physical = os.path.join(folder, safe_name)

    if not os.path.isfile(physical):
        abort(404)

    return send_from_directory(
        folder,
        safe_name,
        as_attachment=False,
        download_name=safe_name,
    )


@teacher_syllabus.route("/download/<path:filename>")
def download(filename):
    if not teacher_logged_in():
        return redirect(url_for("teacher_auth.login"))

    safe_name = _safe_syllabus_filename(filename)
    folder = get_syllabus_upload_folder()

    if not safe_name.lower().endswith(".pdf"):
        abort(404)

    cursor = mysql.connection.cursor()
    try:
        cursor.execute(
            """
            SELECT file_name
            FROM syllabus
            WHERE file_name = %s
               OR file_path = %s
               OR file_path = %s
            LIMIT 1
            """,
            (
                safe_name,
                filename.replace("\\", "/").lstrip("/"),
                "uploads/syllabus/" + safe_name,
            ),
        )
        row = cursor.fetchone()
    finally:
        try:
            cursor.close()
        except Exception:
            pass

    if not row:
        abort(404)

    safe_name = _safe_syllabus_filename(row[0])
    physical = os.path.join(folder, safe_name)

    if not os.path.isfile(physical):
        abort(404)

    return send_from_directory(
        folder,
        safe_name,
        as_attachment=True,
        download_name=safe_name,
    )
