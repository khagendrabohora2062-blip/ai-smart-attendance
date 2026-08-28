from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    current_app,
    send_from_directory
)

from extensions import mysql
from werkzeug.utils import secure_filename

import os
import uuid


# ==========================================================
# ADMIN SYLLABUS BLUEPRINT
# ==========================================================

admin_syllabus = Blueprint(
    "admin_syllabus",
    __name__,
    url_prefix="/admin/syllabus"
)


# ==========================================================
# ADMIN LOGIN CHECK
# ==========================================================

def admin_logged_in():
    return "admin_id" in session


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
# ALLOWED FILE
# ==========================================================

def allowed_file(filename):

    if not filename:
        return False

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() == "pdf"
    )


# ==========================================================
# NORMALIZE SEMESTER
#
# Examples:
# 4
# "4"
# "4th"
# "4th Semester"
# "4 Semester"
#
# All become:
# "4"
# ==========================================================

def normalize_semester(value):

    if value is None:
        return ""

    value = str(value).strip().lower()

    if not value:
        return ""

    # Remove common semester words
    value = value.replace("semester", "")
    value = value.replace("sem", "")

    # Remove ordinal suffixes
    value = value.replace("st", "")
    value = value.replace("nd", "")
    value = value.replace("rd", "")
    value = value.replace("th", "")

    # Remove spaces
    value = value.replace(" ", "")

    return value


# ==========================================================
# NORMALIZE DEPARTMENT
# ==========================================================

def normalize_department(value):

    if value is None:
        return ""

    return str(value).strip().lower()


# ==========================================================
# GENERATE UNIQUE SYLLABUS ID
#
# TiDB:
# syllabus.id is NOT AUTO_INCREMENT
#
# Therefore we manually generate a unique integer ID.
# ==========================================================

def generate_syllabus_id(cursor):

    while True:

        # Generate positive INT value
        new_id = uuid.uuid4().int % 2147483647

        if new_id <= 0:
            continue

        cursor.execute(
            """
            SELECT id
            FROM syllabus
            WHERE id = %s
            LIMIT 1
            """,
            (new_id,)
        )

        existing = cursor.fetchone()

        if existing is None:
            return new_id


# ==========================================================
# SYLLABUS INDEX
# ==========================================================

@admin_syllabus.route("/")
def index():

    # ------------------------------------------------------
    # LOGIN CHECK
    # ------------------------------------------------------

    if not admin_logged_in():

        return redirect(
            url_for("auth.login")
        )

    cursor = mysql.connection.cursor()

    syllabuses = []
    subjects = []

    try:

        # ==================================================
        # LOAD SYLLABUS
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

            ORDER BY
                s.id DESC
            """
        )

        syllabuses = cursor.fetchall()


        # ==================================================
        # LOAD SUBJECTS
        #
        # JavaScript can filter:
        # department + semester
        # ==================================================

        cursor.execute(
            """
            SELECT
                id,
                subject_code,
                subject_name,
                semester,
                department

            FROM subjects

            ORDER BY
                department ASC,
                subject_code ASC
            """
        )

        subjects = cursor.fetchall()


    except Exception as e:

        flash(
            f"Syllabus loading error: {e}",
            "danger"
        )

    finally:

        try:
            cursor.close()
        except Exception:
            pass


    # ======================================================
    # RENDER PAGE
    # ======================================================

    return render_template(
        "admin/syllabus/index.html",
        syllabuses=syllabuses,
        subjects=subjects
    )


# ==========================================================
# UPLOAD SYLLABUS
# ==========================================================

@admin_syllabus.route(
    "/upload",
    methods=["POST"]
)
def upload():

    # ------------------------------------------------------
    # LOGIN CHECK
    # ------------------------------------------------------

    if not admin_logged_in():

        return redirect(
            url_for("auth.login")
        )


    # ======================================================
    # FORM DATA
    # ======================================================

    department = request.form.get(
        "department",
        ""
    ).strip()

    semester = request.form.get(
        "semester",
        ""
    ).strip()

    subject_id = request.form.get(
        "subject_id",
        ""
    ).strip()

    title = request.form.get(
        "title",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    pdf_file = request.files.get(
        "file"
    )


    # ======================================================
    # BASIC VALIDATION
    # ======================================================

    if not department:

        flash(
            "Please select a department.",
            "warning"
        )

        return redirect(
            url_for("admin_syllabus.index")
        )


    if not semester:

        flash(
            "Please select a semester.",
            "warning"
        )

        return redirect(
            url_for("admin_syllabus.index")
        )


    if not subject_id:

        flash(
            "Please select a subject.",
            "warning"
        )

        return redirect(
            url_for("admin_syllabus.index")
        )


    if not title:

        flash(
            "Syllabus title is required.",
            "warning"
        )

        return redirect(
            url_for("admin_syllabus.index")
        )


    if not pdf_file or not pdf_file.filename:

        flash(
            "Please select a PDF syllabus file.",
            "warning"
        )

        return redirect(
            url_for("admin_syllabus.index")
        )


    if not allowed_file(pdf_file.filename):

        flash(
            "Only PDF files are allowed.",
            "danger"
        )

        return redirect(
            url_for("admin_syllabus.index")
        )


    # ======================================================
    # VERIFY SUBJECT
    # ======================================================

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                id,
                subject_code,
                subject_name,
                semester,
                department

            FROM subjects

            WHERE id = %s

            LIMIT 1
            """,
            (subject_id,)
        )

        subject = cursor.fetchone()


        # --------------------------------------------------
        # SUBJECT NOT FOUND
        # --------------------------------------------------

        if not subject:

            flash(
                "Selected subject was not found.",
                "danger"
            )

            return redirect(
                url_for("admin_syllabus.index")
            )


        # --------------------------------------------------
        # SUBJECT DATA
        # --------------------------------------------------

        subject_db_id = subject[0]
        subject_code = subject[1]
        subject_name = subject[2]
        subject_semester = subject[3]
        subject_department = subject[4]


        # ==================================================
        # NORMALIZED VALUES
        # ==================================================

        selected_semester = normalize_semester(
            semester
        )

        database_semester = normalize_semester(
            subject_semester
        )

        selected_department = normalize_department(
            department
        )

        database_department = normalize_department(
            subject_department
        )


        # ==================================================
        # SEMESTER VALIDATION
        # ==================================================

        if selected_semester != database_semester:

            flash(
                (
                    "Selected semester does not match "
                    f"the subject semester. "
                    f"Selected: {semester}, "
                    f"Subject: {subject_semester}"
                ),
                "danger"
            )

            return redirect(
                url_for("admin_syllabus.index")
            )


        # ==================================================
        # DEPARTMENT VALIDATION
        # ==================================================

        if selected_department != database_department:

            flash(
                (
                    "Selected department does not match "
                    f"the subject department. "
                    f"Selected: {department}, "
                    f"Subject: {subject_department}"
                ),
                "danger"
            )

            return redirect(
                url_for("admin_syllabus.index")
            )


    except Exception as e:

        flash(
            f"Subject validation error: {e}",
            "danger"
        )

        return redirect(
            url_for("admin_syllabus.index")
        )

    finally:

        try:
            cursor.close()
        except Exception:
            pass


    # ======================================================
    # SAVE PDF
    # ======================================================

    original_name = secure_filename(
        pdf_file.filename
    )

    # Keep PDF extension
    unique_name = (
        str(uuid.uuid4())
        + ".pdf"
    )


    upload_folder = (
        get_syllabus_upload_folder()
    )


    file_path = os.path.join(
        upload_folder,
        unique_name
    )


    # ======================================================
    # DATABASE + FILE
    # ======================================================

    cursor = None

    try:

        # ==================================================
        # SAVE PHYSICAL PDF
        # ==================================================

        pdf_file.save(
            file_path
        )


        # ==================================================
        # OPEN DATABASE CURSOR
        # ==================================================

        cursor = mysql.connection.cursor()


        # ==================================================
        # GENERATE MANUAL ID
        #
        # IMPORTANT FOR TiDB
        # ==================================================

        syllabus_id = generate_syllabus_id(
            cursor
        )


        # ==================================================
        # DATABASE INSERT
        #
        # IMPORTANT:
        # id is explicitly inserted.
        #
        # This fixes:
        #
        # Field 'id' doesn't have a default value
        # ==================================================

        cursor.execute(
            """
            INSERT INTO syllabus
            (
                id,
                department,
                semester,
                subject_id,
                title,
                description,
                file_name,
                file_path
            )

            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                syllabus_id,

                subject_department,

                subject_semester,

                subject_db_id,

                title,

                description,

                unique_name,

                os.path.join(
                    "uploads",
                    "syllabus",
                    unique_name
                ).replace("\\", "/")
            )
        )


        # ==================================================
        # COMMIT
        # ==================================================

        mysql.connection.commit()


        # ==================================================
        # CLOSE CURSOR
        # ==================================================

        cursor.close()
        cursor = None


        # ==================================================
        # SUCCESS MESSAGE
        # ==================================================

        flash(
            (
                f"Syllabus uploaded successfully "
                f"for {subject_code} - {subject_name}."
            ),
            "success"
        )


    except Exception as e:

        # --------------------------------------------------
        # ROLLBACK DATABASE
        # --------------------------------------------------

        try:
            mysql.connection.rollback()
        except Exception:
            pass


        # --------------------------------------------------
        # CLOSE CURSOR
        # --------------------------------------------------

        try:

            if cursor:
                cursor.close()

        except Exception:
            pass


        # --------------------------------------------------
        # DELETE PDF IF DATABASE INSERT FAILED
        # --------------------------------------------------

        if os.path.exists(file_path):

            try:
                os.remove(file_path)

            except Exception:
                pass


        # --------------------------------------------------
        # ERROR MESSAGE
        # --------------------------------------------------

        flash(
            f"Syllabus upload error: {e}",
            "danger"
        )


    # ======================================================
    # REDIRECT
    # ======================================================

    return redirect(
        url_for(
            "admin_syllabus.index"
        )
    )


# ==========================================================
# VIEW / DOWNLOAD SYLLABUS
# ==========================================================

@admin_syllabus.route(
    "/file/<filename>"
)
def file(filename):

    # ------------------------------------------------------
    # LOGIN CHECK
    # ------------------------------------------------------

    if not admin_logged_in():

        return redirect(
            url_for("auth.login")
        )


    folder = (
        get_syllabus_upload_folder()
    )


    return send_from_directory(
        folder,
        filename
    )


# ==========================================================
# DELETE SYLLABUS
# ==========================================================

@admin_syllabus.route(
    "/delete/<int:id>",
    methods=["POST"]
)
def delete(id):

    # ------------------------------------------------------
    # LOGIN CHECK
    # ------------------------------------------------------

    if not admin_logged_in():

        return redirect(
            url_for("auth.login")
        )


    cursor = mysql.connection.cursor()

    try:

        # ==================================================
        # GET SYLLABUS FILE
        # ==================================================

        cursor.execute(
            """
            SELECT
                file_name

            FROM syllabus

            WHERE id = %s

            LIMIT 1
            """,
            (id,)
        )

        syllabus = cursor.fetchone()


        # --------------------------------------------------
        # NOT FOUND
        # --------------------------------------------------

        if not syllabus:

            flash(
                "Syllabus not found.",
                "warning"
            )

            return redirect(
                url_for(
                    "admin_syllabus.index"
                )
            )


        file_name = syllabus[0]


        # ==================================================
        # DELETE DATABASE RECORD
        # ==================================================

        cursor.execute(
            """
            DELETE FROM syllabus

            WHERE id = %s
            """,
            (id,)
        )


        mysql.connection.commit()


        # ==================================================
        # DELETE PHYSICAL PDF
        # ==================================================

        if file_name:

            folder = (
                get_syllabus_upload_folder()
            )

            physical_file = os.path.join(
                folder,
                file_name
            )


            if os.path.exists(
                physical_file
            ):

                try:

                    os.remove(
                        physical_file
                    )

                except Exception:
                    pass


        # ==================================================
        # SUCCESS MESSAGE
        # ==================================================

        flash(
            "Syllabus deleted successfully.",
            "success"
        )


    except Exception as e:

        # --------------------------------------------------
        # ROLLBACK
        # --------------------------------------------------

        try:

            mysql.connection.rollback()

        except Exception:
            pass


        # --------------------------------------------------
        # ERROR MESSAGE
        # --------------------------------------------------

        flash(
            f"Syllabus delete error: {e}",
            "danger"
        )


    finally:

        try:
            cursor.close()
        except Exception:
            pass


    return redirect(
        url_for(
            "admin_syllabus.index"
        )
    )