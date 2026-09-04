# ============================================================
# ADMIN NOTICE MANAGEMENT
# File: routes/admin_notice.py
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
    current_app,
    send_from_directory,
    abort,
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
# ALLOWED FILES
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
# MYSQL
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
# ADMIN AUTHENTICATION
# ============================================================

def admin_required():
    return bool(
        session.get("admin_id")
        or session.get("admin_logged_in")
        or session.get("is_admin")
    )


def require_admin():
    if not admin_required():
        flash(
            "Please login as administrator.",
            "warning"
        )
        return redirect("/admin/login")

    return None


# ============================================================
# FILE HELPERS
# ============================================================

def allowed_file(filename, allowed_extensions):
    if not filename or "." not in filename:
        return False

    extension = filename.rsplit(
        ".",
        1
    )[1].lower()

    return extension in allowed_extensions


def make_filename(filename):
    filename = secure_filename(filename)

    extension = ""

    if "." in filename:
        extension = "." + filename.rsplit(
            ".",
            1
        )[1].lower()

    return f"{uuid4().hex}{extension}"


# ============================================================
# GENERATE NOTICE ID
# ============================================================

def generate_notice_id(cursor):
    while True:

        new_id = uuid4().int % 2147483647

        if new_id <= 0:
            continue

        cursor.execute(
            """
            SELECT id
            FROM notices
            WHERE id = %s
            LIMIT 1
            """,
            (new_id,)
        )

        if not cursor.fetchone():
            return new_id


# ============================================================
# UPLOAD FOLDERS
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
# DELETE PHYSICAL FILE
# ============================================================

def delete_notice_file(
    filename,
    file_type="image"
):

    if not filename:
        return

    try:

        base_folder, pdf_folder = (
            get_notice_upload_paths()
        )

        folder = (
            pdf_folder
            if file_type == "pdf"
            else base_folder
        )

        safe_filename = os.path.basename(
            filename
        )

        file_path = os.path.join(
            folder,
            safe_filename
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

    auth_redirect = require_admin()

    if auth_redirect:
        return auth_redirect

    mysql = get_mysql()
    cursor = mysql.connection.cursor()

    notices = []

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
                updated_at,
                audience
            FROM notices
            ORDER BY created_at DESC
            """
        )

        notices = cursor.fetchall() or []

    except Exception as e:

        print(
            "NOTICE INDEX ERROR:",
            repr(e)
        )

        flash(
            f"Unable to load notices: {str(e)}",
            "danger"
        )

    finally:

        cursor.close()

    return render_template(
        "admin/notices/index.html",
        notices=notices
    )


# ============================================================
# ADD NOTICE
# ============================================================

@admin_notice.route(
    "/add",
    methods=["GET", "POST"]
)
def add():

    auth_redirect = require_admin()

    if auth_redirect:
        return auth_redirect

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    if request.method == "GET":

        return render_template(
            "admin/notices/add.html"
        )

    # --------------------------------------------------------
    # FORM DATA
    # --------------------------------------------------------

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

    audience = request.form.get(
        "audience",
        "Everyone"
    ).strip()

    allowed_audiences = {
        "Everyone",
        "Students",
        "Teachers"
    }

    if audience not in allowed_audiences:
        audience = "Everyone"

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

    # --------------------------------------------------------
    # VALIDATE TITLE
    # --------------------------------------------------------

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

    # ========================================================
    # IMAGE UPLOAD
    # ========================================================

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

        try:

            image_file.save(
                os.path.join(
                    image_folder,
                    image_name
                )
            )

        except Exception as e:

            print(
                "NOTICE IMAGE SAVE ERROR:",
                repr(e)
            )

            flash(
                f"Unable to save image: {str(e)}",
                "danger"
            )

            return render_template(
                "admin/notices/add.html"
            )

    # ========================================================
    # PDF UPLOAD
    # ========================================================

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

        try:

            pdf_file.save(
                os.path.join(
                    pdf_folder,
                    pdf_name
                )
            )

        except Exception as e:

            if image_name:
                delete_notice_file(
                    image_name,
                    "image"
                )

            print(
                "NOTICE PDF SAVE ERROR:",
                repr(e)
            )

            flash(
                f"Unable to save PDF: {str(e)}",
                "danger"
            )

            return render_template(
                "admin/notices/add.html"
            )

    # ========================================================
    # DATABASE INSERT
    # ========================================================

    mysql = get_mysql()
    cursor = mysql.connection.cursor()

    try:

        notice_id = generate_notice_id(
            cursor
        )

        admin_id = (
            session.get("admin_id")
            or session.get("user_id")
        )

        cursor.execute(
            """
            INSERT INTO notices
            (
                id,
                title,
                description,
                image,
                pdf_file,
                target_semester,
                target_department,
                notice_type,
                is_published,
                created_by,
                audience
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
                %s,
                %s,
                %s
            )
            """,
            (
                notice_id,
                title,
                description,
                image_name,
                pdf_name,
                target_semester or None,
                target_department or None,
                notice_type or "General",
                is_published,
                admin_id,
                audience
            )
        )

        mysql.connection.commit()

        flash(
            "Notice added successfully.",
            "success"
        )

        return redirect(
            url_for(
                "admin_notice.index"
            )
        )

    except Exception as e:

        try:
            mysql.connection.rollback()
        except Exception:
            pass

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

        return render_template(
            "admin/notices/add.html"
        )

    finally:

        cursor.close()


# ============================================================
# VIEW NOTICE
# ============================================================

@admin_notice.route(
    "/view/<int:notice_id>",
    methods=["GET"]
)
def view(notice_id):

    auth_redirect = require_admin()

    if auth_redirect:
        return auth_redirect

    mysql = get_mysql()
    cursor = mysql.connection.cursor()

    notice = None

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
                updated_at,
                audience
            FROM notices
            WHERE id = %s
            LIMIT 1
            """,
            (notice_id,)
        )

        notice = cursor.fetchone()

    except Exception as e:

        print(
            "NOTICE VIEW ERROR:",
            repr(e)
        )

        flash(
            f"Unable to view notice: {str(e)}",
            "danger"
        )

        return redirect(
            url_for(
                "admin_notice.index"
            )
        )

    finally:

        cursor.close()

    if not notice:

        flash(
            "Notice not found.",
            "warning"
        )

        return redirect(
            url_for(
                "admin_notice.index"
            )
        )

    return render_template(
        "admin/notices/view.html",
        notice=notice
    )


# ============================================================
# VIEW IMAGE
# ============================================================

@admin_notice.route(
    "/image/<path:filename>",
    methods=["GET"]
)
def view_image(filename):

    if not admin_required():
        abort(403)

    safe_filename = os.path.basename(
        filename
    )

    image_folder, _ = (
        get_notice_upload_paths()
    )

    file_path = os.path.join(
        image_folder,
        safe_filename
    )

    if not os.path.isfile(file_path):
        abort(404)

    return send_from_directory(
        image_folder,
        safe_filename,
        as_attachment=False
    )


# ============================================================
# VIEW PDF
# ============================================================

@admin_notice.route(
    "/pdf/<path:filename>",
    methods=["GET"]
)
def view_pdf(filename):

    if not admin_required():
        abort(403)

    safe_filename = os.path.basename(
        filename
    )

    _, pdf_folder = (
        get_notice_upload_paths()
    )

    file_path = os.path.join(
        pdf_folder,
        safe_filename
    )

    if not os.path.isfile(file_path):
        abort(404)

    return send_from_directory(
        pdf_folder,
        safe_filename,
        as_attachment=False
    )


# ============================================================
# DOWNLOAD PDF
# ============================================================

@admin_notice.route(
    "/download-pdf/<path:filename>",
    methods=["GET"]
)
def download_pdf(filename):

    if not admin_required():
        abort(403)

    safe_filename = os.path.basename(
        filename
    )

    _, pdf_folder = (
        get_notice_upload_paths()
    )

    file_path = os.path.join(
        pdf_folder,
        safe_filename
    )

    if not os.path.isfile(file_path):
        abort(404)

    return send_from_directory(
        pdf_folder,
        safe_filename,
        as_attachment=True,
        download_name=safe_filename
    )


# ============================================================
# EDIT NOTICE
# ============================================================

@admin_notice.route(
    "/edit/<int:notice_id>",
    methods=["GET", "POST"]
)
def edit(notice_id):

    auth_redirect = require_admin()

    if auth_redirect:
        return auth_redirect

    mysql = get_mysql()
    cursor = mysql.connection.cursor()

    try:

        # ----------------------------------------------------
        # GET CURRENT NOTICE
        # ----------------------------------------------------

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
                audience
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
                url_for(
                    "admin_notice.index"
                )
            )

        # ----------------------------------------------------
        # GET
        # ----------------------------------------------------

        if request.method == "GET":

            return render_template(
                "admin/notices/edit.html",
                notice=notice
            )

        # ----------------------------------------------------
        # POST
        # ----------------------------------------------------

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

        audience = request.form.get(
            "audience",
            "Everyone"
        ).strip()

        if audience not in {
            "Everyone",
            "Students",
            "Teachers"
        }:

            audience = "Everyone"

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

        # ====================================================
        # NEW IMAGE
        # ====================================================

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

        # ====================================================
        # NEW PDF
        # ====================================================

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

        # ====================================================
        # UPDATE DATABASE
        # ====================================================

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
                is_published = %s,
                audience = %s
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
                audience,
                notice_id
            )
        )

        mysql.connection.commit()

        # ----------------------------------------------------
        # DELETE OLD FILES
        # ----------------------------------------------------

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
            url_for(
                "admin_notice.index"
            )
        )

    except Exception as e:

        try:
            mysql.connection.rollback()
        except Exception:
            pass

        print(
            "NOTICE EDIT ERROR:",
            repr(e)
        )

        flash(
            f"Unable to update notice: {str(e)}",
            "danger"
        )

        return redirect(
            url_for(
                "admin_notice.index"
            )
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

    auth_redirect = require_admin()

    if auth_redirect:
        return auth_redirect

    mysql = get_mysql()
    cursor = mysql.connection.cursor()

    try:

        # ----------------------------------------------------
        # GET FILE NAMES
        # ----------------------------------------------------

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
                "warning"
            )

            return redirect(
                url_for(
                    "admin_notice.index"
                )
            )

        # ----------------------------------------------------
        # DELETE DATABASE RECORD
        # ----------------------------------------------------

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

        if notice[0]:

            delete_notice_file(
                notice[0],
                "image"
            )

        # ----------------------------------------------------
        # DELETE PDF
        # ----------------------------------------------------

        if notice[1]:

            delete_notice_file(
                notice[1],
                "pdf"
            )

        flash(
            "Notice deleted successfully.",
            "success"
        )

    except Exception as e:

        try:
            mysql.connection.rollback()
        except Exception:
            pass

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
        url_for(
            "admin_notice.index"
        )
    )


# ============================================================
# TOGGLE PUBLISH
# ============================================================

@admin_notice.route(
    "/toggle/<int:notice_id>",
    methods=["POST"]
)
def toggle_publish(notice_id):

    auth_redirect = require_admin()

    if auth_redirect:
        return auth_redirect

    mysql = get_mysql()
    cursor = mysql.connection.cursor()

    try:

        # ----------------------------------------------------
        # CHECK NOTICE EXISTS
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT is_published
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
                "warning"
            )

            return redirect(
                url_for(
                    "admin_notice.index"
                )
            )

        # ----------------------------------------------------
        # TOGGLE STATUS
        # ----------------------------------------------------

        current_status = int(
            notice[0] or 0
        )

        new_status = (
            0
            if current_status == 1
            else 1
        )

        cursor.execute(
            """
            UPDATE notices
            SET is_published = %s
            WHERE id = %s
            """,
            (
                new_status,
                notice_id
            )
        )

        mysql.connection.commit()

        if new_status == 1:

            flash(
                "Notice published successfully.",
                "success"
            )

        else:

            flash(
                "Notice unpublished successfully.",
                "warning"
            )

    except Exception as e:

        try:
            mysql.connection.rollback()
        except Exception:
            pass

        print(
            "NOTICE TOGGLE ERROR:",
            repr(e)
        )

        flash(
            f"Unable to update notice status: {str(e)}",
            "danger"
        )

    finally:

        cursor.close()

    return redirect(
        url_for(
            "admin_notice.index"
        )
    )