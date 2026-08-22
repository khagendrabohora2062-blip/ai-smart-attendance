# ============================================================
# ADMIN NOTICE MANAGEMENT
# File:
# routes/admin_notice.py
# ============================================================

import os
from uuid import uuid4

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    current_app
)

from werkzeug.utils import secure_filename


# ============================================================
# BLUEPRINT
# ============================================================

admin_notice = Blueprint(
    "admin_notice",
    __name__,
    url_prefix="/admin/notices"
)


# ============================================================
# ALLOWED FILE TYPES
# ============================================================

ALLOWED_IMAGES = {
    "jpg",
    "jpeg",
    "png",
    "webp"
}

ALLOWED_PDF = {
    "pdf"
}


# ============================================================
# MYSQL CONNECTION
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
        print("ADMIN NOTICE MYSQL ERROR:", repr(e))

    raise RuntimeError(
        "MySQL connection is not initialized."
    )


# ============================================================
# ADMIN AUTH CHECK
# ============================================================

def admin_required():

    return bool(
        session.get("admin_id")
        or session.get("admin_logged_in")
        or session.get("is_admin")
    )


# ============================================================
# FILE EXTENSION CHECK
# ============================================================

def allowed_file(filename, allowed_extensions):

    if not filename:
        return False

    if "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()

    return extension in allowed_extensions


# ============================================================
# UNIQUE FILE NAME
# ============================================================

def make_filename(filename):

    filename = secure_filename(filename)

    extension = ""

    if "." in filename:
        extension = "." + filename.rsplit(".", 1)[1].lower()

    return f"{uuid4().hex}{extension}"


# ============================================================
# NOTICE UPLOAD DIRECTORIES
# ============================================================

def get_notice_upload_paths():

    base_folder = os.path.join(
        current_app.root_path,
        "static",
        "uploads",
        "notices"
    )

    pdf_folder = os.path.join(
        base_folder,
        "pdf"
    )

    os.makedirs(
        base_folder,
        exist_ok=True
    )

    os.makedirs(
        pdf_folder,
        exist_ok=True
    )

    return base_folder, pdf_folder


# ============================================================
# DELETE NOTICE FILE
# ============================================================

def delete_notice_file(filename, file_type="image"):

    if not filename:
        return

    try:

        base_folder, pdf_folder = get_notice_upload_paths()

        if file_type == "pdf":
            folder = pdf_folder
        else:
            folder = base_folder

        file_path = os.path.join(
            folder,
            os.path.basename(filename)
        )

        if os.path.isfile(file_path):
            os.remove(file_path)

    except Exception as e:

        print(
            "NOTICE FILE DELETE ERROR:",
            repr(e)
        )


# ============================================================
# ADMIN NOTICE LIST
# ============================================================

@admin_notice.route("/")
def index():

    if not admin_required():

        flash(
            "Please login as administrator.",
            "warning"
        )

        return redirect("/admin/login")

    mysql = get_mysql()

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                id,
                title,
                description,
                image,
                pdf_file,
                target_semester,
                target_department,
                notice_type,
                is_published,
                created_at,
                updated_at
            FROM notices
            ORDER BY created_at DESC
            """
        )

        notices = cursor.fetchall()

        return render_template(
            "admin/notices/index.html",
            notices=notices
        )

    except Exception as e:

        print(
            "NOTICE INDEX ERROR:",
            repr(e)
        )

        flash(
            f"Unable to load notices: {str(e)}",
            "danger"
        )

        return render_template(
            "admin/notices/index.html",
            notices=[]
        )

    finally:

        cursor.close()


# ============================================================
# ADD NOTICE
# ============================================================

@admin_notice.route("/add", methods=["GET", "POST"])
def add():

    if not admin_required():

        flash(
            "Please login as administrator.",
            "warning"
        )

        return redirect("/admin/login")

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        target_semester = request.form.get(
            "target_semester",
            ""
        ).strip()

        target_department = request.form.get(
            "target_department",
            ""
        ).strip()

        notice_type = request.form.get(
            "notice_type",
            "General"
        ).strip()

        is_published = (
            1
            if request.form.get("is_published")
            else 0
        )

        image_file = request.files.get(
            "image"
        )

        pdf_file = request.files.get(
            "pdf_file"
        )

        # ----------------------------------------------------
        # TITLE VALIDATION
        # ----------------------------------------------------

        if not title:

            flash(
                "Notice title is required.",
                "danger"
            )

            return render_template(
                "admin/notices/add.html"
            )

        image_name = None
        pdf_name = None

        image_folder, pdf_folder = (
            get_notice_upload_paths()
        )

        # ----------------------------------------------------
        # IMAGE UPLOAD
        # ----------------------------------------------------

        if image_file and image_file.filename:

            if not allowed_file(
                image_file.filename,
                ALLOWED_IMAGES
            ):

                flash(
                    "Only JPG, JPEG, PNG and WEBP images are allowed.",
                    "danger"
                )

                return render_template(
                    "admin/notices/add.html"
                )

            image_name = make_filename(
                image_file.filename
            )

            image_file.save(
                os.path.join(
                    image_folder,
                    image_name
                )
            )

        # ----------------------------------------------------
        # PDF UPLOAD
        # ----------------------------------------------------

        if pdf_file and pdf_file.filename:

            if not allowed_file(
                pdf_file.filename,
                ALLOWED_PDF
            ):

                if image_name:

                    delete_notice_file(
                        image_name,
                        "image"
                    )

                flash(
                    "Only PDF files are allowed.",
                    "danger"
                )

                return render_template(
                    "admin/notices/add.html"
                )

            pdf_name = make_filename(
                pdf_file.filename
            )

            pdf_file.save(
                os.path.join(
                    pdf_folder,
                    pdf_name
                )
            )

        # ----------------------------------------------------
        # DATABASE INSERT
        # ----------------------------------------------------

        mysql = get_mysql()

        cursor = mysql.connection.cursor()

        try:

            admin_id = (
                session.get("admin_id")
                or session.get("user_id")
            )

            cursor.execute(
                """
                INSERT INTO notices
                (
                    title,
                    description,
                    image,
                    pdf_file,
                    target_semester,
                    target_department,
                    notice_type,
                    is_published,
                    created_by
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
                    %s,
                    %s
                )
                """,
                (
                    title,
                    description,
                    image_name,
                    pdf_name,
                    target_semester or None,
                    target_department or None,
                    notice_type or "General",
                    is_published,
                    admin_id
                )
            )

            mysql.connection.commit()

            flash(
                "Notice added successfully.",
                "success"
            )

            return redirect(
                url_for("admin_notice.index")
            )

        except Exception as e:

            mysql.connection.rollback()

            if image_name:

                delete_notice_file(
                    image_name,
                    "image"
                )

            if pdf_name:

                delete_notice_file(
                    pdf_name,
                    "pdf"
                )

            print(
                "NOTICE INSERT ERROR:",
                repr(e)
            )

            flash(
                f"Unable to add notice: {str(e)}",
                "danger"
            )

        finally:

            cursor.close()

    return render_template(
        "admin/notices/add.html"
    )


# ============================================================
# EDIT NOTICE
# ============================================================

@admin_notice.route(
    "/edit/<int:notice_id>",
    methods=["GET", "POST"]
)
def edit(notice_id):

    if not admin_required():

        flash(
            "Please login as administrator.",
            "warning"
        )

        return redirect("/admin/login")

    mysql = get_mysql()

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                id,
                title,
                description,
                image,
                pdf_file,
                target_semester,
                target_department,
                notice_type,
                is_published
            FROM notices
            WHERE id = %s
            LIMIT 1
            """,
            (notice_id,)
        )

        notice = cursor.fetchone()

        if not notice:

            flash(
                "Notice not found.",
                "danger"
            )

            return redirect(
                url_for("admin_notice.index")
            )

        # ====================================================
        # POST
        # ====================================================

        if request.method == "POST":

            title = request.form.get(
                "title",
                ""
            ).strip()

            description = request.form.get(
                "description",
                ""
            ).strip()

            target_semester = request.form.get(
                "target_semester",
                ""
            ).strip()

            target_department = request.form.get(
                "target_department",
                ""
            ).strip()

            notice_type = request.form.get(
                "notice_type",
                "General"
            ).strip()

            is_published = (
                1
                if request.form.get("is_published")
                else 0
            )

            if not title:

                flash(
                    "Notice title is required.",
                    "danger"
                )

                return render_template(
                    "admin/notices/edit.html",
                    notice=notice
                )

            old_image = notice[3]
            old_pdf = notice[4]

            new_image = old_image
            new_pdf = old_pdf

            image_file = request.files.get(
                "image"
            )

            pdf_file = request.files.get(
                "pdf_file"
            )

            image_folder, pdf_folder = (
                get_notice_upload_paths()
            )

            # ------------------------------------------------
            # NEW IMAGE
            # ------------------------------------------------

            if image_file and image_file.filename:

                if not allowed_file(
                    image_file.filename,
                    ALLOWED_IMAGES
                ):

                    flash(
                        "Only JPG, JPEG, PNG and WEBP images are allowed.",
                        "danger"
                    )

                    return render_template(
                        "admin/notices/edit.html",
                        notice=notice
                    )

                new_image = make_filename(
                    image_file.filename
                )

                image_file.save(
                    os.path.join(
                        image_folder,
                        new_image
                    )
                )

            # ------------------------------------------------
            # NEW PDF
            # ------------------------------------------------

            if pdf_file and pdf_file.filename:

                if not allowed_file(
                    pdf_file.filename,
                    ALLOWED_PDF
                ):

                    if new_image != old_image:

                        delete_notice_file(
                            new_image,
                            "image"
                        )

                    flash(
                        "Only PDF files are allowed.",
                        "danger"
                    )

                    return render_template(
                        "admin/notices/edit.html",
                        notice=notice
                    )

                new_pdf = make_filename(
                    pdf_file.filename
                )

                pdf_file.save(
                    os.path.join(
                        pdf_folder,
                        new_pdf
                    )
                )

            # ------------------------------------------------
            # DATABASE UPDATE
            # ------------------------------------------------

            cursor.execute(
                """
                UPDATE notices
                SET
                    title = %s,
                    description = %s,
                    image = %s,
                    pdf_file = %s,
                    target_semester = %s,
                    target_department = %s,
                    notice_type = %s,
                    is_published = %s
                WHERE id = %s
                """,
                (
                    title,
                    description,
                    new_image,
                    new_pdf,
                    target_semester or None,
                    target_department or None,
                    notice_type or "General",
                    is_published,
                    notice_id
                )
            )

            mysql.connection.commit()

            # ------------------------------------------------
            # DELETE OLD FILES
            # ------------------------------------------------

            if new_image != old_image:

                delete_notice_file(
                    old_image,
                    "image"
                )

            if new_pdf != old_pdf:

                delete_notice_file(
                    old_pdf,
                    "pdf"
                )

            flash(
                "Notice updated successfully.",
                "success"
            )

            return redirect(
                url_for("admin_notice.index")
            )

        # ====================================================
        # GET
        # ====================================================

        return render_template(
            "admin/notices/edit.html",
            notice=notice
        )

    except Exception as e:

        mysql.connection.rollback()

        print(
            "NOTICE EDIT ERROR:",
            repr(e)
        )

        flash(
            f"Unable to update notice: {str(e)}",
            "danger"
        )

        return redirect(
            url_for("admin_notice.index")
        )

    finally:

        cursor.close()


# ============================================================
# DELETE NOTICE
# ============================================================

@admin_notice.route(
    "/delete/<int:notice_id>",
    methods=["POST"]
)
def delete(notice_id):

    if not admin_required():

        flash(
            "Please login as administrator.",
            "warning"
        )

        return redirect("/admin/login")

    mysql = get_mysql()

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                image,
                pdf_file
            FROM notices
            WHERE id = %s
            LIMIT 1
            """,
            (notice_id,)
        )

        notice = cursor.fetchone()

        if not notice:

            flash(
                "Notice not found.",
                "danger"
            )

            return redirect(
                url_for("admin_notice.index")
            )

        cursor.execute(
            """
            DELETE FROM notices
            WHERE id = %s
            """,
            (notice_id,)
        )

        mysql.connection.commit()

        # ----------------------------------------------------
        # DELETE IMAGE
        # ----------------------------------------------------

        delete_notice_file(
            notice[0],
            "image"
        )

        # ----------------------------------------------------
        # DELETE PDF
        # ----------------------------------------------------

        delete_notice_file(
            notice[1],
            "pdf"
        )

        flash(
            "Notice deleted successfully.",
            "success"
        )

    except Exception as e:

        mysql.connection.rollback()

        print(
            "NOTICE DELETE ERROR:",
            repr(e)
        )

        flash(
            f"Unable to delete notice: {str(e)}",
            "danger"
        )

    finally:

        cursor.close()

    return redirect(
        url_for("admin_notice.index")
    )


# ============================================================
# TOGGLE PUBLISH / UNPUBLISH
# ============================================================

@admin_notice.route(
    "/toggle/<int:notice_id>",
    methods=["POST"]
)
def toggle_publish(notice_id):

    if not admin_required():

        flash(
            "Please login as administrator.",
            "warning"
        )

        return redirect("/admin/login")

    mysql = get_mysql()

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            UPDATE notices
            SET is_published =
                CASE
                    WHEN is_published = 1 THEN 0
                    ELSE 1
                END
            WHERE id = %s
            """,
            (notice_id,)
        )

        mysql.connection.commit()

        flash(
            "Notice publish status updated.",
            "success"
        )

    except Exception as e:

        mysql.connection.rollback()

        print(
            "NOTICE TOGGLE ERROR:",
            repr(e)
        )

        flash(
            f"Unable to update status: {str(e)}",
            "danger"
        )

    finally:

        cursor.close()

    return redirect(
        url_for("admin_notice.index")
    )