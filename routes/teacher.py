from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    request,
    flash,
    current_app
)

from extensions import mysql

import os
import uuid

from werkzeug.utils import secure_filename


teachers = Blueprint(
    "teachers",
    __name__,
    url_prefix="/teachers"
)


# =========================================================
# ALLOWED IMAGE EXTENSIONS
# =========================================================

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp"
}


def allowed_file(filename):
    return (
        filename
        and "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# =========================================================
# UPLOAD FOLDER
# =========================================================

def get_upload_folder():

    folder = current_app.config.get("UPLOAD_FOLDER")

    if not folder:
        folder = os.path.join(
            current_app.root_path,
            "static",
            "uploads",
            "teachers"
        )

    os.makedirs(
        folder,
        exist_ok=True
    )

    return folder


# =========================================================
# GENERATE DATABASE ID
#
# IMPORTANT:
# teachers.id is NOT AUTO_INCREMENT
# Therefore we generate a unique integer manually.
# =========================================================

def generate_teacher_db_id(cursor):

    while True:

        new_id = uuid.uuid4().int % 2147483647

        if new_id <= 0:
            continue

        cursor.execute(
            """
            SELECT id
            FROM teachers
            WHERE id=%s
            LIMIT 1
            """,
            (new_id,)
        )

        existing = cursor.fetchone()

        if existing is None:
            return new_id


# =========================================================
# TEACHER LIST
# =========================================================

@teachers.route("/")
def index():

    if "admin_id" not in session:
        return redirect(
            url_for("auth.login")
        )

    cursor = None

    try:

        cursor = mysql.connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                teacher_id,
                full_name,
                email,
                phone,
                department,
                photo
            FROM teachers
            ORDER BY id DESC
            """
        )

        teachers_data = cursor.fetchall()

        return render_template(
            "admin/teachers.html",
            teachers=teachers_data
        )

    except Exception as e:

        current_app.logger.exception(
            "Error loading teachers"
        )

        flash(
            "Unable to load teachers.",
            "danger"
        )

        return redirect(
            url_for("admin.dashboard")
        )

    finally:

        if cursor:
            cursor.close()


# =========================================================
# ADD TEACHER
# =========================================================

@teachers.route(
    "/add",
    methods=["GET", "POST"]
)
def add_teacher():

    if "admin_id" not in session:
        return redirect(
            url_for("auth.login")
        )

    if request.method == "GET":

        return render_template(
            "admin/add_teacher.html"
        )

    cursor = None
    photo_filename = None
    saved_photo_path = None

    try:

        # -------------------------------------------------
        # FORM DATA
        # -------------------------------------------------

        teacher_id = (
            request.form.get("teacher_id")
            or ""
        ).strip()

        full_name = (
            request.form.get("full_name")
            or ""
        ).strip()

        email = (
            request.form.get("email")
            or ""
        ).strip()

        phone = (
            request.form.get("phone")
            or ""
        ).strip()

        department = (
            request.form.get("department")
            or ""
        ).strip()

        photo = request.files.get("photo")


        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not teacher_id:

            flash(
                "Teacher ID is required.",
                "danger"
            )

            return redirect(
                url_for("teachers.add_teacher")
            )


        if not full_name:

            flash(
                "Full name is required.",
                "danger"
            )

            return redirect(
                url_for("teachers.add_teacher")
            )


        if not email:

            flash(
                "Email is required.",
                "danger"
            )

            return redirect(
                url_for("teachers.add_teacher")
            )


        # -------------------------------------------------
        # DATABASE CURSOR
        # -------------------------------------------------

        cursor = mysql.connection.cursor()


        # -------------------------------------------------
        # CHECK TEACHER ID
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT id
            FROM teachers
            WHERE teacher_id=%s
            LIMIT 1
            """,
            (teacher_id,)
        )

        if cursor.fetchone():

            flash(
                "Teacher ID already exists!",
                "danger"
            )

            return redirect(
                url_for("teachers.add_teacher")
            )


        # -------------------------------------------------
        # CHECK EMAIL
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT id
            FROM teachers
            WHERE email=%s
            LIMIT 1
            """,
            (email,)
        )

        if cursor.fetchone():

            flash(
                "Email already exists!",
                "danger"
            )

            return redirect(
                url_for("teachers.add_teacher")
            )


        # -------------------------------------------------
        # PHOTO
        # -------------------------------------------------

        if photo and photo.filename:

            if not allowed_file(
                photo.filename
            ):

                flash(
                    "Invalid image format. "
                    "Use JPG, JPEG, PNG or WEBP.",
                    "danger"
                )

                return redirect(
                    url_for("teachers.add_teacher")
                )


            original_filename = secure_filename(
                photo.filename
            )

            extension = os.path.splitext(
                original_filename
            )[1].lower()


            photo_filename = (
                "teacher_"
                + uuid.uuid4().hex
                + extension
            )


            upload_folder = get_upload_folder()


            saved_photo_path = os.path.join(
                upload_folder,
                photo_filename
            )


            photo.save(
                saved_photo_path
            )


        # -------------------------------------------------
        # GENERATE MANUAL DATABASE ID
        # -------------------------------------------------

        new_db_id = generate_teacher_db_id(
            cursor
        )


        # -------------------------------------------------
        # INSERT TEACHER
        #
        # IMPORTANT:
        # id is explicitly supplied because
        # teachers.id is NOT AUTO_INCREMENT.
        # -------------------------------------------------

        cursor.execute(
            """
            INSERT INTO teachers
            (
                id,
                teacher_id,
                full_name,
                email,
                phone,
                department,
                password,
                photo
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
                new_db_id,
                teacher_id,
                full_name,
                email,
                phone,
                department,
                "teacher123",
                photo_filename
            )
        )


        mysql.connection.commit()


        flash(
            "Teacher added successfully!",
            "success"
        )


        return redirect(
            url_for("teachers.index")
        )


    except Exception as e:

        try:
            mysql.connection.rollback()
        except Exception:
            pass


        # If database insertion failed after photo
        # was saved, remove the unused photo.
        if saved_photo_path:

            try:

                if os.path.exists(
                    saved_photo_path
                ):
                    os.remove(
                        saved_photo_path
                    )

            except Exception:
                pass


        current_app.logger.exception(
            "Error adding teacher"
        )


        flash(
            "Unable to add teacher. "
            "Please check the information and try again.",
            "danger"
        )


        return redirect(
            url_for("teachers.add_teacher")
        )


    finally:

        if cursor:
            cursor.close()


# =========================================================
# EDIT TEACHER
# =========================================================

@teachers.route(
    "/edit/<int:id>",
    methods=["GET", "POST"]
)
def edit_teacher(id):

    if "admin_id" not in session:
        return redirect(
            url_for("auth.login")
        )

    cursor = None

    try:

        cursor = mysql.connection.cursor()


        # -------------------------------------------------
        # GET CURRENT TEACHER
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                teacher_id,
                full_name,
                email,
                phone,
                department,
                photo
            FROM teachers
            WHERE id=%s
            LIMIT 1
            """,
            (id,)
        )

        teacher = cursor.fetchone()


        if not teacher:

            flash(
                "Teacher not found!",
                "danger"
            )

            return redirect(
                url_for("teachers.index")
            )


        # -------------------------------------------------
        # GET REQUEST
        # -------------------------------------------------

        if request.method == "GET":

            return render_template(
                "admin/edit_teacher.html",
                teacher=teacher
            )


        # -------------------------------------------------
        # FORM DATA
        # -------------------------------------------------

        teacher_id = (
            request.form.get("teacher_id")
            or ""
        ).strip()

        full_name = (
            request.form.get("full_name")
            or ""
        ).strip()

        email = (
            request.form.get("email")
            or ""
        ).strip()

        phone = (
            request.form.get("phone")
            or ""
        ).strip()

        department = (
            request.form.get("department")
            or ""
        ).strip()

        photo = request.files.get("photo")

        remove_photo = (
            request.form.get("remove_photo")
            or ""
        )


        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not teacher_id:

            flash(
                "Teacher ID is required.",
                "danger"
            )

            return redirect(
                url_for(
                    "teachers.edit_teacher",
                    id=id
                )
            )


        if not full_name:

            flash(
                "Full name is required.",
                "danger"
            )

            return redirect(
                url_for(
                    "teachers.edit_teacher",
                    id=id
                )
            )


        if not email:

            flash(
                "Email is required.",
                "danger"
            )

            return redirect(
                url_for(
                    "teachers.edit_teacher",
                    id=id
                )
            )


        # -------------------------------------------------
        # DUPLICATE TEACHER ID
        # Exclude current teacher.
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT id
            FROM teachers
            WHERE teacher_id=%s
              AND id<>%s
            LIMIT 1
            """,
            (
                teacher_id,
                id
            )
        )

        if cursor.fetchone():

            flash(
                "Teacher ID already exists!",
                "danger"
            )

            return redirect(
                url_for(
                    "teachers.edit_teacher",
                    id=id
                )
            )


        # -------------------------------------------------
        # DUPLICATE EMAIL
        # Exclude current teacher.
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT id
            FROM teachers
            WHERE email=%s
              AND id<>%s
            LIMIT 1
            """,
            (
                email,
                id
            )
        )

        if cursor.fetchone():

            flash(
                "Email already exists!",
                "danger"
            )

            return redirect(
                url_for(
                    "teachers.edit_teacher",
                    id=id
                )
            )


        # -------------------------------------------------
        # OLD PHOTO
        # -------------------------------------------------

        old_photo = teacher[6]

        photo_filename = old_photo

        old_photo_path = None
        new_photo_path = None


        # -------------------------------------------------
        # REMOVE PHOTO
        # -------------------------------------------------

        if remove_photo == "1":

            photo_filename = None

            if old_photo:

                old_photo_path = os.path.join(
                    get_upload_folder(),
                    old_photo
                )


        # -------------------------------------------------
        # NEW PHOTO
        # -------------------------------------------------

        if photo and photo.filename:

            if not allowed_file(
                photo.filename
            ):

                flash(
                    "Invalid image format. "
                    "Use JPG, JPEG, PNG or WEBP.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "teachers.edit_teacher",
                        id=id
                    )
                )


            original_filename = secure_filename(
                photo.filename
            )


            extension = os.path.splitext(
                original_filename
            )[1].lower()


            new_photo = (
                "teacher_"
                + uuid.uuid4().hex
                + extension
            )


            new_photo_path = os.path.join(
                get_upload_folder(),
                new_photo
            )


            photo.save(
                new_photo_path
            )


            photo_filename = new_photo


            # Old photo will be deleted after
            # successful database update.

            if old_photo:

                old_photo_path = os.path.join(
                    get_upload_folder(),
                    old_photo
                )


        # -------------------------------------------------
        # UPDATE TEACHER
        # -------------------------------------------------

        cursor.execute(
            """
            UPDATE teachers
            SET
                teacher_id=%s,
                full_name=%s,
                email=%s,
                phone=%s,
                department=%s,
                photo=%s
            WHERE id=%s
            """,
            (
                teacher_id,
                full_name,
                email,
                phone,
                department,
                photo_filename,
                id
            )
        )


        mysql.connection.commit()


        # -------------------------------------------------
        # DELETE OLD PHOTO AFTER SUCCESSFUL UPDATE
        # -------------------------------------------------

        if old_photo_path:

            try:

                if os.path.exists(
                    old_photo_path
                ):
                    os.remove(
                        old_photo_path
                    )

            except Exception:

                current_app.logger.warning(
                    "Could not delete old teacher photo: %s",
                    old_photo_path
                )


        flash(
            "Teacher updated successfully!",
            "success"
        )


        return redirect(
            url_for("teachers.index")
        )


    except Exception as e:

        try:
            mysql.connection.rollback()
        except Exception:
            pass


        current_app.logger.exception(
            "Error updating teacher"
        )


        flash(
            "Unable to update teacher. "
            "Please check the information and try again.",
            "danger"
        )


        return redirect(
            url_for(
                "teachers.edit_teacher",
                id=id
            )
        )


    finally:

        if cursor:
            cursor.close()


# RESET TEACHER PASSWORD
# =========================================================

@teachers.route(
    "/reset-password/<int:id>",
    methods=["POST"]
)
def reset_teacher_password(id):

    if "admin_id" not in session:
        return redirect(
            url_for("auth.login")
        )

    # --------------------------------------------------------
    # DEFAULT TEMPORARY PASSWORD
    # --------------------------------------------------------
    # Existing teacher login checks password directly,
    # so keep the same format as the existing teacher system.
    temporary_password = "teacher123"

    cursor = None

    try:

        cursor = mysql.connection.cursor()

        # ----------------------------------------------------
        # CHECK TEACHER
        # ----------------------------------------------------
        cursor.execute(
            """
            SELECT
                id,
                teacher_id,
                full_name
            FROM teachers
            WHERE id=%s
            LIMIT 1
            """,
            (id,)
        )

        teacher = cursor.fetchone()

        if not teacher:

            flash(
                "Teacher not found!",
                "danger"
            )

            return redirect(
                url_for("teachers.index")
            )

        # ----------------------------------------------------
        # RESET PASSWORD
        # ----------------------------------------------------
        cursor.execute(
            """
            UPDATE teachers
            SET password=%s
            WHERE id=%s
            """,
            (
                temporary_password,
                id
            )
        )

        mysql.connection.commit()

        flash(
            f"Password reset successfully for {teacher[2]}. Temporary password: {temporary_password}",
            "success"
        )

    except Exception as e:

        try:
            mysql.connection.rollback()
        except Exception:
            pass

        current_app.logger.exception(
            "Error resetting teacher password"
        )

        flash(
            f"Unable to reset teacher password: {e}",
            "danger"
        )

    finally:

        if cursor:
            cursor.close()

    return redirect(
        url_for("teachers.index")
    )
        # -------------------------------------------------
        # =========================================================
# DELETE TEACHER
# =========================================================

@teachers.route(
    "/delete/<int:id>",
    methods=["GET", "POST"]
)
def delete_teacher(id):

    if "admin_id" not in session:
        return redirect(
            url_for("auth.login")
        )

    cursor = None

    try:

        cursor = mysql.connection.cursor()


        # -------------------------------------------------
        # GET TEACHER PHOTO
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT photo
            FROM teachers
            WHERE id=%s
            LIMIT 1
            """,
            (id,)
        )

        teacher = cursor.fetchone()


        if not teacher:

            flash(
                "Teacher not found!",
                "danger"
            )

            return redirect(
                url_for("teachers.index")
            )


        photo = teacher[0]

             # =========================================================
# DELETE TEACHER
        # -------------------------------------------------

        cursor.execute(
            """
            DELETE FROM teachers
            WHERE id=%s
            """,
            (id,)
        )


        mysql.connection.commit()


        # -------------------------------------------------
        # DELETE PHOTO
        # -------------------------------------------------

        if photo:

            photo_path = os.path.join(
                get_upload_folder(),
                photo
            )

            try:

                if os.path.exists(
                    photo_path
                ):
                    os.remove(
                        photo_path
                    )

            except Exception:

                current_app.logger.warning(
                    "Could not delete teacher photo: %s",
                    photo_path
                )


        flash(
            "Teacher deleted successfully!",
            "success"
        )


        return redirect(
            url_for("teachers.index")
        )


    except Exception as e:

        try:
            mysql.connection.rollback()
        except Exception:
            pass


        current_app.logger.exception(
            "Error deleting teacher"
        )


        flash(
            "Unable to delete teacher.",
            "danger"
        )


        return redirect(
            url_for("teachers.index")
        )


    finally:

        if cursor:
            cursor.close()


# =========================================================
# REMOVE TEACHER PHOTO
# =========================================================

@teachers.route(
    "/remove-photo/<int:id>",
    methods=["GET", "POST"]
)
def remove_photo(id):

    if "admin_id" not in session:
        return redirect(
            url_for("auth.login")
        )

    cursor = None

    try:

        cursor = mysql.connection.cursor()


        # -------------------------------------------------
        # GET CURRENT PHOTO
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT photo
            FROM teachers
            WHERE id=%s
            LIMIT 1
            """,
            (id,)
        )

        teacher = cursor.fetchone()


        if not teacher:

            flash(
                "Teacher not found!",
                "danger"
            )

            return redirect(
                url_for("teachers.index")
            )


        old_photo = teacher[0]


        # -------------------------------------------------
        # REMOVE PHOTO FROM DATABASE
        # -------------------------------------------------

        cursor.execute(
            """
            UPDATE teachers
            SET photo=NULL
            WHERE id=%s
            """,
            (id,)
        )


        mysql.connection.commit()


        # -------------------------------------------------
        # DELETE PHOTO FILE
        # -------------------------------------------------

        if old_photo:

            photo_path = os.path.join(
                get_upload_folder(),
                old_photo
            )

            try:

                if os.path.exists(
                    photo_path
                ):
                    os.remove(
                        photo_path
                    )

            except Exception:

                current_app.logger.warning(
                    "Could not delete photo: %s",
                    photo_path
                )


        flash(
            "Teacher photo removed successfully!",
            "success"
        )


        return redirect(
            url_for(
                "teachers.edit_teacher",
                id=id
            )
        )


    except Exception as e:

        try:
            mysql.connection.rollback()
        except Exception:
            pass


        current_app.logger.exception(
            "Error removing teacher photo"
        )


        flash(
            "Unable to remove teacher photo.",
            "danger"
        )


        return redirect(
            url_for(
                "teachers.edit_teacher",
                id=id
            )
        )


    finally:

        if cursor:
            cursor.close()