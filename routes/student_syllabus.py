from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    session,
    flash,
    current_app,
    send_from_directory,
    abort
)

from extensions import mysql
import os


# ==========================================================
# STUDENT SYLLABUS BLUEPRINT
# ==========================================================

student_syllabus = Blueprint(
    "student_syllabus",
    __name__,
    url_prefix="/student/syllabus"
)


# ==========================================================
# STUDENT LOGIN CHECK
# ==========================================================

def student_logged_in():
    return "student_db_id" in session


# ==========================================================
# SYLLABUS UPLOAD FOLDER
# ==========================================================

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


# ==========================================================
# STUDENT SYLLABUS INDEX
# ==========================================================

@student_syllabus.route("/")
def index():

    # ------------------------------------------------------
    # LOGIN CHECK
    # ------------------------------------------------------

    if not student_logged_in():

        flash(
            "Please login first.",
            "warning"
        )

        return redirect(
            url_for("student_auth.login")
        )


    student_db_id = session["student_db_id"]

    cursor = mysql.connection.cursor()


    try:

        # ==================================================
        # GET CURRENT STUDENT INFORMATION
        # ==================================================

        cursor.execute(
            """
            SELECT
                id,
                student_id,
                full_name,
                email,
                department,
                semester,
                section,
                photo
            FROM students
            WHERE id = %s
            LIMIT 1
            """,
            (student_db_id,)
        )

        student = cursor.fetchone()


        # --------------------------------------------------
        # STUDENT NOT FOUND
        # --------------------------------------------------

        if not student:

            cursor.close()

            session.clear()

            flash(
                "Student account not found.",
                "danger"
            )

            return redirect(
                url_for("student_auth.login")
            )


        # ==================================================
        # STUDENT DETAILS
        #
        # student[0] = database id
        # student[1] = student id
        # student[2] = full name
        # student[3] = email
        # student[4] = department
        # student[5] = semester
        # student[6] = section
        # student[7] = photo
        # ==================================================

        department = student[4]
        semester = student[5]


        # ==================================================
        # GET SYLLABUS FOR CURRENT STUDENT
        #
        # IMPORTANT:
        # Only same department + same semester
        # ==================================================

        cursor.execute(
            """
            SELECT
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

            WHERE s.department = %s
            AND s.semester = %s

            ORDER BY
                sub.subject_code ASC,
                s.id DESC
            """,
            (
                department,
                semester
            )
        )

        syllabuses = cursor.fetchall()


    except Exception as e:

        flash(
            f"Syllabus loading error: {e}",
            "danger"
        )

        syllabuses = []


    finally:

        cursor.close()


    # ======================================================
    # RENDER STUDENT SYLLABUS PAGE
    # ======================================================

    return render_template(
        "student/syllabus/index.html",
        student=student,
        syllabuses=syllabuses
    )


# ==========================================================

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

@student_syllabus.route("/view/<path:filename>")
def view(filename):
    if not student_logged_in():
        return redirect(url_for("student_auth.login"))

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


@student_syllabus.route("/download/<path:filename>")
def download(filename):
    if not student_logged_in():
        return redirect(url_for("student_auth.login"))

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
