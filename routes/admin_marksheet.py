from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    session,
    request,
    send_from_directory,
    send_file
)

from extensions import mysql
from werkzeug.utils import secure_filename

import os
import uuid
import io
import mimetypes


# ============================================================
# BLUEPRINT
# ============================================================

admin_marksheet = Blueprint(
    "admin_marksheet",
    __name__,
    url_prefix="/admin/marksheets"
)


# ============================================================
# MARKSHEET UPLOAD FOLDER
# ============================================================

MARKSHEET_UPLOAD_FOLDER = os.path.join(
    "static",
    "uploads",
    "marksheets"
)

os.makedirs(
    MARKSHEET_UPLOAD_FOLDER,
    exist_ok=True
)


# ============================================================
# ALLOWED FILE EXTENSIONS
# ============================================================

ALLOWED_MARKSHEET_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".pdf"
}


# ============================================================
# ADMIN CHECK
# ============================================================

def admin_required():

    return bool(
        session.get("admin_id")
        or session.get("admin_logged_in")
        or session.get("admin")
    )


# ============================================================
# VALIDATE + READ MARKSHEET FILE
# ============================================================

def read_marksheet_file(file):

    if not file or not file.filename:
        raise ValueError(
            "Please select a marksheet file."
        )

    original_name = secure_filename(
        file.filename
    )

    extension = os.path.splitext(
        original_name
    )[1].lower()

    if extension not in ALLOWED_MARKSHEET_EXTENSIONS:
        raise ValueError(
            "Only JPG, JPEG, PNG, WEBP and PDF files are allowed."
        )

    file_data = file.read()

    if not file_data:
        raise ValueError(
            "The selected marksheet file is empty."
        )

    return extension, file_data


# ============================================================
# SAVE PHYSICAL FILE
# ============================================================

def save_marksheet_file(file, file_data=None, extension=None):

    if file_data is None or extension is None:
        extension, file_data = read_marksheet_file(file)

    new_filename = (
        uuid.uuid4().hex
        + extension
    )

    file_path = os.path.join(
        MARKSHEET_UPLOAD_FOLDER,
        new_filename
    )

    with open(file_path, "wb") as output_file:
        output_file.write(file_data)

    return new_filename


# ============================================================
# DELETE PHYSICAL FILE
# ============================================================

def delete_marksheet_file(filename):

    if not filename:
        return

    file_path = os.path.join(
        MARKSHEET_UPLOAD_FOLDER,
        filename
    )

    try:

        if os.path.exists(file_path):
            os.remove(file_path)

    except OSError as e:

        print(
            "MARKSHEET FILE DELETE ERROR:",
            repr(e)
        )


# ============================================================
# MIME TYPE
# ============================================================

def get_marksheet_mimetype(filename):

    extension = os.path.splitext(
        filename or ""
    )[1].lower()

    mime_types = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp"
    }

    return (
        mime_types.get(extension)
        or mimetypes.guess_type(filename or "")[0]
        or "application/octet-stream"
    )


# ============================================================
# GENERATE INTEGER ID
# ============================================================

def generate_marksheet_id(cursor):

    while True:

        new_id = uuid.uuid4().int % 2147483647

        if new_id <= 0:
            continue

        cursor.execute(
            """
            SELECT id
            FROM marksheets
            WHERE id = %s
            LIMIT 1
            """,
            (new_id,)
        )

        existing = cursor.fetchone()

        if not existing:
            return new_id


# ============================================================
# MARKSHEET LIST
# ============================================================

@admin_marksheet.route("/")
def index():

    if not admin_required():

        flash(
            "Please login as administrator.",
            "warning"
        )

        return redirect(
            url_for("auth.login")
        )

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                m.id,
                m.student_id,
                s.student_id,
                s.full_name,
                s.department,
                s.semester,
                m.marksheet_file,
                m.created_at
            FROM marksheets m

            INNER JOIN students s
                ON s.id = m.student_id

            ORDER BY
                s.semester ASC,
                s.department ASC,
                s.full_name ASC
            """
        )

        marksheets = cursor.fetchall()

        return render_template(
            "admin/marksheets/index.html",
            marksheets=marksheets
        )

    except Exception as e:

        print(
            "MARKSHEET LIST ERROR:",
            repr(e)
        )

        try:
            mysql.connection.rollback()
        except Exception:
            pass

        flash(
            f"Unable to load marksheets: {str(e)}",
            "danger"
        )

        return redirect(
            url_for("admin.dashboard")
        )

    finally:

        cursor.close()


# ============================================================
# ADD / UPLOAD MARKSHEET
# ============================================================

@admin_marksheet.route(
    "/add",
    methods=["GET", "POST"]
)
def add():

    if not admin_required():

        flash(
            "Please login as administrator.",
            "warning"
        )

        return redirect(
            url_for("auth.login")
        )

    cursor = mysql.connection.cursor()

    uploaded_file_name = None

    try:

        # ====================================================
        # POST
        # ====================================================

        if request.method == "POST":

            student_db_id = request.form.get(
                "student_id",
                ""
            ).strip()

            if not student_db_id:

                flash(
                    "Please select a student.",
                    "danger"
                )

                return redirect(
                    url_for("admin_marksheet.add")
                )

            # ------------------------------------------------
            # CHECK STUDENT
            # ------------------------------------------------

            cursor.execute(
                """
                SELECT
                    id,
                    student_id,
                    full_name,
                    department,
                    semester
                FROM students
                WHERE id = %s
                LIMIT 1
                """,
                (student_db_id,)
            )

            student = cursor.fetchone()

            if not student:

                flash(
                    "Selected student was not found.",
                    "danger"
                )

                return redirect(
                    url_for("admin_marksheet.add")
                )

            # ------------------------------------------------
            # GET FILE
            # ------------------------------------------------

            marksheet_file = request.files.get(
                "marksheet_file"
            )

            if (
                not marksheet_file
                or not marksheet_file.filename
            ):

                flash(
                    "Please upload the marksheet.",
                    "danger"
                )

                return redirect(
                    url_for("admin_marksheet.add")
                )

            # ------------------------------------------------
            # ONE MARKSHEET PER STUDENT
            # ------------------------------------------------

            cursor.execute(
                """
                SELECT
                    id
                FROM marksheets
                WHERE student_id = %s
                LIMIT 1
                """,
                (student_db_id,)
            )

            existing = cursor.fetchone()

            if existing:

                flash(
                    "A marksheet already exists for this student. "
                    "Please use Edit/Replace.",
                    "warning"
                )

                return redirect(
                    url_for("admin_marksheet.add")
                )

            # ------------------------------------------------
            # READ FILE ONCE
            # ------------------------------------------------

            extension, file_data = read_marksheet_file(
                marksheet_file
            )

            # ------------------------------------------------
            # GENERATE FILENAME
            # ------------------------------------------------

            uploaded_file_name = (
                uuid.uuid4().hex
                + extension
            )

            # ------------------------------------------------
            # OPTIONAL PHYSICAL BACKUP
            # ------------------------------------------------

            file_path = os.path.join(
                MARKSHEET_UPLOAD_FOLDER,
                uploaded_file_name
            )

            with open(file_path, "wb") as output_file:
                output_file.write(file_data)

            # ------------------------------------------------
            # GENERATE ID
            # ------------------------------------------------

            new_marksheet_id = generate_marksheet_id(
                cursor
            )

            # ------------------------------------------------
            # INSERT DATABASE
            #
            # file_data contains the actual PDF/image bytes.
            # ------------------------------------------------

            cursor.execute(
                """
                INSERT INTO marksheets
                (
                    id,
                    student_id,
                    marksheet_file,
                    file_data
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    new_marksheet_id,
                    student_db_id,
                    uploaded_file_name,
                    file_data
                )
            )

            mysql.connection.commit()

            uploaded_file_name = None

            flash(
                "Marksheet uploaded successfully!",
                "success"
            )

            return redirect(
                url_for("admin_marksheet.index")
            )

        # ====================================================
        # GET STUDENTS
        # ====================================================

        cursor.execute(
            """
            SELECT
                id,
                student_id,
                full_name,
                department,
                semester
            FROM students
            ORDER BY
                semester ASC,
                department ASC,
                full_name ASC
            """
        )

        students = cursor.fetchall()

        return render_template(
            "admin/marksheets/add.html",
            students=students
        )

    except ValueError as e:

        if uploaded_file_name:
            delete_marksheet_file(
                uploaded_file_name
            )

        try:
            mysql.connection.rollback()
        except Exception:
            pass

        flash(
            str(e),
            "danger"
        )

        return redirect(
            url_for("admin_marksheet.add")
        )

    except Exception as e:

        if uploaded_file_name:
            delete_marksheet_file(
                uploaded_file_name
            )

        try:
            mysql.connection.rollback()
        except Exception:
            pass

        print(
            "MARKSHEET UPLOAD ERROR:",
            repr(e)
        )

        flash(
            f"Unable to upload marksheet: {str(e)}",
            "danger"
        )

        return redirect(
            url_for("admin_marksheet.add")
        )

    finally:

        cursor.close()


# ============================================================
# VIEW MARKSHEET - ADMIN
# ============================================================

@admin_marksheet.route(
    "/view/<int:marksheet_id>"
)
def view(marksheet_id):

    if not admin_required():

        flash(
            "Please login as administrator.",
            "warning"
        )

        return redirect(
            url_for("auth.login")
        )

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                marksheet_file,
                file_data
            FROM marksheets
            WHERE id = %s
            LIMIT 1
            """,
            (marksheet_id,)
        )

        data = cursor.fetchone()

    except Exception as e:

        print(
            "VIEW MARKSHEET ERROR:",
            repr(e)
        )

        flash(
            f"Unable to open marksheet: {str(e)}",
            "danger"
        )

        return redirect(
            url_for("admin_marksheet.index")
        )

    finally:

        cursor.close()

    if not data:

        flash(
            "Marksheet not found.",
            "warning"
        )

        return redirect(
            url_for("admin_marksheet.index")
        )

    filename = data[0]
    file_data = data[1]

    # ========================================================
    # DATABASE BLOB FIRST
    # ========================================================

    if file_data:

        try:

            return send_file(
                io.BytesIO(bytes(file_data)),
                mimetype=get_marksheet_mimetype(filename),
                as_attachment=False,
                download_name=filename
            )

        except Exception as e:

            print(
                "DATABASE MARKSHEET VIEW ERROR:",
                repr(e)
            )

    # ========================================================
    # PHYSICAL FILE FALLBACK
    # ========================================================

    if filename:

        file_path = os.path.join(
            MARKSHEET_UPLOAD_FOLDER,
            filename
        )

        if os.path.isfile(file_path):

            return send_from_directory(
                MARKSHEET_UPLOAD_FOLDER,
                filename,
                as_attachment=False
            )

    flash(
        "Marksheet file is missing.",
        "danger"
    )

    return redirect(
        url_for("admin_marksheet.index")
    )


# ============================================================
# EDIT / REPLACE MARKSHEET
# ============================================================

@admin_marksheet.route(
    "/edit/<int:marksheet_id>",
    methods=["GET", "POST"]
)
def edit(marksheet_id):

    if not admin_required():

        flash(
            "Please login as administrator.",
            "warning"
        )

        return redirect(
            url_for("auth.login")
        )

    cursor = mysql.connection.cursor()

    old_file = None
    new_file = None

    try:

        # ====================================================
        # GET CURRENT MARKSHEET
        # ====================================================

        cursor.execute(
            """
            SELECT
                m.id,
                m.student_id,
                m.marksheet_file,
                s.student_id,
                s.full_name,
                s.department,
                s.semester
            FROM marksheets m

            INNER JOIN students s
                ON s.id = m.student_id

            WHERE m.id = %s

            LIMIT 1
            """,
            (marksheet_id,)
        )

        marksheet = cursor.fetchone()

        if not marksheet:

            flash(
                "Marksheet not found.",
                "warning"
            )

            return redirect(
                url_for("admin_marksheet.index")
            )

        old_file = marksheet[2]

        # ====================================================
        # POST - REPLACE FILE
        # ====================================================

        if request.method == "POST":

            marksheet_file = request.files.get(
                "marksheet_file"
            )

            if (
                not marksheet_file
                or not marksheet_file.filename
            ):

                flash(
                    "Please select a new marksheet file.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "admin_marksheet.edit",
                        marksheet_id=marksheet_id
                    )
                )

            # ------------------------------------------------
            # READ NEW FILE
            # ------------------------------------------------

            extension, file_data = read_marksheet_file(
                marksheet_file
            )

            # ------------------------------------------------
            # GENERATE NEW FILE NAME
            # ------------------------------------------------

            new_file = (
                uuid.uuid4().hex
                + extension
            )

            new_file_path = os.path.join(
                MARKSHEET_UPLOAD_FOLDER,
                new_file
            )

            with open(
                new_file_path,
                "wb"
            ) as output_file:

                output_file.write(
                    file_data
                )

            # ------------------------------------------------
            # UPDATE DATABASE
            # ------------------------------------------------

            cursor.execute(
                """
                UPDATE marksheets
                SET
                    marksheet_file = %s,
                    file_data = %s
                WHERE id = %s
                """,
                (
                    new_file,
                    file_data,
                    marksheet_id
                )
            )

            mysql.connection.commit()

            # ------------------------------------------------
            # DELETE OLD PHYSICAL FILE
            # ------------------------------------------------

            if (
                old_file
                and old_file != new_file
            ):

                delete_marksheet_file(
                    old_file
                )

            new_file = None

            flash(
                "Marksheet replaced successfully!",
                "success"
            )

            return redirect(
                url_for("admin_marksheet.index")
            )

        # ====================================================
        # GET EDIT PAGE
        # ====================================================

        return render_template(
            "admin/marksheets/edit.html",
            marksheet=marksheet
        )

    except ValueError as e:

        if new_file:
            delete_marksheet_file(
                new_file
            )

        try:
            mysql.connection.rollback()
        except Exception:
            pass

        flash(
            str(e),
            "danger"
        )

        return redirect(
            url_for(
                "admin_marksheet.edit",
                marksheet_id=marksheet_id
            )
        )

    except Exception as e:

        if new_file:
            delete_marksheet_file(
                new_file
            )

        try:
            mysql.connection.rollback()
        except Exception:
            pass

        print(
            "EDIT MARKSHEET ERROR:",
            repr(e)
        )

        flash(
            f"Unable to replace marksheet: {str(e)}",
            "danger"
        )

        return redirect(
            url_for(
                "admin_marksheet.edit",
                marksheet_id=marksheet_id
            )
        )

    finally:

        cursor.close()


# ============================================================
# DELETE MARKSHEET
# ============================================================

@admin_marksheet.route(
    "/delete/<int:marksheet_id>",
    methods=["POST", "GET"]
)
def delete(marksheet_id):

    if not admin_required():

        flash(
            "Please login as administrator.",
            "warning"
        )

        return redirect(
            url_for("auth.login")
        )

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                marksheet_file
            FROM marksheets
            WHERE id = %s
            LIMIT 1
            """,
            (marksheet_id,)
        )

        data = cursor.fetchone()

        if not data:

            flash(
                "Marksheet not found.",
                "warning"
            )

            return redirect(
                url_for("admin_marksheet.index")
            )

        filename = data[0]

        # ----------------------------------------------------
        # DELETE DATABASE RECORD
        # ----------------------------------------------------

        cursor.execute(
            """
            DELETE FROM marksheets
            WHERE id = %s
            """,
            (marksheet_id,)
        )

        mysql.connection.commit()

        # ----------------------------------------------------
        # DELETE PHYSICAL FILE
        # ----------------------------------------------------

        if filename:

            delete_marksheet_file(
                filename
            )

        flash(
            "Marksheet deleted successfully.",
            "success"
        )

    except Exception as e:

        try:
            mysql.connection.rollback()
        except Exception:
            pass

        print(
            "DELETE MARKSHEET ERROR:",
            repr(e)
        )

        flash(
            f"Unable to delete marksheet: {str(e)}",
            "danger"
        )

    finally:

        cursor.close()

    return redirect(
        url_for("admin_marksheet.index")
    )