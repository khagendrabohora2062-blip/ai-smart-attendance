from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    session,
    flash,
    current_app,
    send_from_directory
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
# VIEW / OPEN SYLLABUS PDF
# ==========================================================

@student_syllabus.route(
    "/view/<filename>"
)
def view(filename):

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


    folder = get_syllabus_upload_folder()


    # ------------------------------------------------------
    # SEND PDF
    #
    # Browser will normally open PDF
    # ------------------------------------------------------

    return send_from_directory(
        folder,
        filename,
        as_attachment=False
    )


# ==========================================================
# DOWNLOAD SYLLABUS PDF
# ==========================================================

@student_syllabus.route(
    "/download/<filename>"
)
def download(filename):

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


    folder = get_syllabus_upload_folder()


    # ------------------------------------------------------
    # DOWNLOAD PDF
    # ------------------------------------------------------

    return send_from_directory(
        folder,
        filename,
        as_attachment=True
    )