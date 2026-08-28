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
    send_from_directory
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
# VIEW SYLLABUS
# ============================================================

@teacher_syllabus.route(
    "/view/<filename>"
)
def view(filename):

    if not teacher_logged_in():

        return redirect(
            url_for("teacher_auth.login")
        )


    folder = get_syllabus_upload_folder()


    return send_from_directory(
        folder,
        filename,
        as_attachment=False
    )


# ============================================================
# DOWNLOAD SYLLABUS
# ============================================================

@teacher_syllabus.route(
    "/download/<filename>"
)
def download(filename):

    if not teacher_logged_in():

        return redirect(
            url_for("teacher_auth.login")
        )


    folder = get_syllabus_upload_folder()


    return send_from_directory(
        folder,
        filename,
        as_attachment=True
    )