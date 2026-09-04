from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    session,
    request,
    send_from_directory
)

from extensions import mysql
from werkzeug.utils import secure_filename

import os
import uuid


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
# SAVE MARKSHEET FILE
# ============================================================

def save_marksheet_file(file):

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

    new_filename = (
        uuid.uuid4().hex
        + extension
    )

    file_path = os.path.join(
        MARKSHEET_UPLOAD_FOLDER,
        new_filename
    )

    file.save(file_path)

    return new_filename


# ============================================================
# DELETE MARKSHEET FILE
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
# GENERATE INTEGER ID
# ============================================================

def generate_marksheet_id(cursor):

    """
    Generates a unique integer ID.

    This works even if marksheets.id
    is NOT AUTO_INCREMENT.
    """

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

        # ----------------------------------------------------
        # IMPORTANT
        #
        # NO subject_id
        # NO theory marks
        # NO practical marks
        # NO full marks
        # NO pass marks
        # NO grade
        # NO created_at
        # NO updated_at
        #
        # Only new marksheets table fields are used.
        # ----------------------------------------------------

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

            # ------------------------------------------------
            # VALIDATE STUDENT
            # ------------------------------------------------

            if not student_db_id:

                flash(
                    "Please select a student.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "admin_marksheet.add"
                    )
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
                    url_for(
                        "admin_marksheet.add"
                    )
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
                    url_for(
                        "admin_marksheet.add"
                    )
                )

            # ------------------------------------------------
            # CHECK EXISTING MARKSHEET
            #
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
                    url_for(
                        "admin_marksheet.add"
                    )
                )

            # ------------------------------------------------
            # SAVE FILE
            # ------------------------------------------------

            uploaded_file_name = save_marksheet_file(
                marksheet_file
            )

            # ------------------------------------------------
            # GENERATE ID
            # ------------------------------------------------

            new_marksheet_id = generate_marksheet_id(
                cursor
            )

            # ------------------------------------------------
            # INSERT
            #
            # IMPORTANT:
            #
            # ONLY:
            # id
            # student_id
            # marksheet_file
            #
            # NOTHING ELSE
            # ------------------------------------------------

            cursor.execute(
                """
                INSERT INTO marksheets
                (
                    id,
                    student_id,
                    marksheet_file
                )
                VALUES
                (
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    new_marksheet_id,
                    student_db_id,
                    uploaded_file_name
                )
            )

            mysql.connection.commit()

            uploaded_file_name = None

            flash(
                "Marksheet uploaded successfully!",
                "success"
            )

            return redirect(
                url_for(
                    "admin_marksheet.index"
                )
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
            url_for(
                "admin_marksheet.add"
            )
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
            url_for(
                "admin_marksheet.add"
            )
        )

    finally:

        cursor.close()


# ============================================================
# VIEW MARKSHEET
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
                marksheet_file
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
            url_for(
                "admin_marksheet.index"
            )
        )

    finally:

        cursor.close()

    # --------------------------------------------------------
    # CHECK DATABASE RECORD
    # --------------------------------------------------------

    if not data:

        flash(
            "Marksheet not found.",
            "warning"
        )

        return redirect(
            url_for(
                "admin_marksheet.index"
            )
        )

    filename = data[0]

    # --------------------------------------------------------
    # CHECK FILE NAME
    # --------------------------------------------------------

    if not filename:

        flash(
            "Marksheet file is missing.",
            "danger"
        )

        return redirect(
            url_for(
                "admin_marksheet.index"
            )
        )

    # --------------------------------------------------------
    # CHECK FILE EXISTS
    # --------------------------------------------------------

    file_path = os.path.join(
        MARKSHEET_UPLOAD_FOLDER,
        filename
    )

    if not os.path.exists(file_path):

        flash(
            "Marksheet file was not found on the server.",
            "danger"
        )

        return redirect(
            url_for(
                "admin_marksheet.index"
            )
        )

    # --------------------------------------------------------
    # SEND FILE
    # --------------------------------------------------------

    return send_from_directory(
        MARKSHEET_UPLOAD_FOLDER,
        filename
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
                url_for(
                    "admin_marksheet.index"
                )
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
            # SAVE NEW FILE
            # ------------------------------------------------

            new_file = save_marksheet_file(
                marksheet_file
            )

            # ------------------------------------------------
            # UPDATE DATABASE
            #
            # Student remains same.
            # Only file changes.
            # ------------------------------------------------

            cursor.execute(
                """
                UPDATE marksheets
                SET
                    marksheet_file = %s
                WHERE id = %s
                """,
                (
                    new_file,
                    marksheet_id
                )
            )

            mysql.connection.commit()

            # ------------------------------------------------
            # DELETE OLD FILE
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
                url_for(
                    "admin_marksheet.index"
                )
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

        # ====================================================
        # GET FILE
        # ====================================================

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
                url_for(
                    "admin_marksheet.index"
                )
            )

        filename = data[0]

        # ====================================================
        # DELETE DATABASE RECORD
        # ====================================================

        cursor.execute(
            """
            DELETE FROM marksheets
            WHERE id = %s
            """,
            (marksheet_id,)
        )

        mysql.connection.commit()

        # ====================================================
        # DELETE PHYSICAL FILE
        # ====================================================

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
        url_for(
            "admin_marksheet.index"
        )
    )