# ============================================================
# ROUTINE PHOTO MANAGEMENT
# File: routes/routine.py
# ============================================================

import os
import uuid

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

routine = Blueprint(
    "routine",
    __name__,
    url_prefix="/admin/routines"
)


# ============================================================
# MYSQL HELPER
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
        print(
            "ROUTINE MYSQL IMPORT ERROR:",
            repr(e)
        )

    raise RuntimeError(
        "MySQL connection is not initialized."
    )


# ============================================================
# ADMIN CHECK
# ============================================================

def admin_required():

    return bool(
        session.get("admin_id")
    )


# ============================================================
# LOGIN REDIRECT
# ============================================================

def admin_login_redirect():

    try:
        return redirect(
            url_for("auth.login")
        )

    except Exception:
        return redirect("/login")


# ============================================================
# ALLOWED PHOTO TYPES
# ============================================================

ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp"
}


def allowed_photo(filename):

    if not filename:
        return False

    if "." not in filename:
        return False

    extension = (
        filename
        .rsplit(".", 1)[1]
        .lower()
        .strip()
    )

    return extension in ALLOWED_EXTENSIONS


# ============================================================
# PHOTO DIRECTORY
# ============================================================

def get_upload_folder():

    folder = os.path.join(
        current_app.root_path,
        "static",
        "uploads",
        "routines"
    )

    os.makedirs(
        folder,
        exist_ok=True
    )

    return folder


# ============================================================
# SAVE PHOTO
# ============================================================

def save_photo(photo):

    if not photo:
        raise ValueError(
            "Please select a routine photo."
        )

    if not photo.filename:
        raise ValueError(
            "Please select a routine photo."
        )

    if not allowed_photo(
        photo.filename
    ):
        raise ValueError(
            "Invalid photo format. "
            "Only JPG, JPEG, PNG and WEBP are allowed."
        )

    original_name = secure_filename(
        photo.filename
    )

    if not original_name:
        raise ValueError(
            "Invalid photo filename."
        )

    extension = (
        original_name
        .rsplit(".", 1)[1]
        .lower()
    )

    filename = (
        "routine_"
        + uuid.uuid4().hex
        + "."
        + extension
    )

    folder = get_upload_folder()

    path = os.path.join(
        folder,
        filename
    )

    photo.save(path)

    return filename


# ============================================================
# DELETE PHOTO FILE
# ============================================================

def delete_photo(filename):

    if not filename:
        return

    try:

        folder = get_upload_folder()

        path = os.path.join(
            folder,
            os.path.basename(filename)
        )

        if os.path.exists(path):
            os.remove(path)

    except Exception as e:

        print(
            "ROUTINE PHOTO DELETE ERROR:",
            repr(e)
        )


# ============================================================
# GET NEXT ID
# ============================================================

def get_next_id(cursor):

    cursor.execute(
        """
        SELECT COALESCE(MAX(id), 0)
        FROM routine_uploads
        """
    )

    row = cursor.fetchone()

    if not row:
        return 1

    try:
        return int(row[0]) + 1

    except Exception:
        return 1


# ============================================================
# ADMIN ROUTINE PAGE
#
# GET  -> Show routines
# POST -> Upload routine
# ============================================================

@routine.route(
    "/",
    methods=["GET", "POST"]
)
def index():

    # --------------------------------------------------------
    # LOGIN
    # --------------------------------------------------------

    if not admin_required():

        flash(
            "Please login as administrator.",
            "warning"
        )

        return admin_login_redirect()


    mysql = None
    cursor = None


    try:

        mysql = get_mysql()

        cursor = mysql.connection.cursor()


        # ====================================================
        # UPLOAD
        # ====================================================

        if request.method == "POST":

            saved_photo = None

            try:

                title = request.form.get(
                    "title",
                    ""
                ).strip()

                academic_year = request.form.get(
                    "academic_year",
                    ""
                ).strip()

                department = request.form.get(
                    "department",
                    ""
                ).strip()

                semester = request.form.get(
                    "semester",
                    ""
                ).strip()

                description = request.form.get(
                    "description",
                    ""
                ).strip()

                is_active = (
                    request.form.get(
                        "is_active"
                    )
                    == "1"
                )


                # ------------------------------------------------
                # TITLE
                # ------------------------------------------------

                if not title:

                    raise ValueError(
                        "Routine title is required."
                    )


                # ------------------------------------------------
                # PHOTO
                # ------------------------------------------------

                photo = request.files.get(
                    "photo"
                )

                saved_photo = save_photo(
                    photo
                )


                # ------------------------------------------------
                # ID
                # ------------------------------------------------

                next_id = get_next_id(
                    cursor
                )


                # ------------------------------------------------
                # CURRENT ROUTINE
                #
                # If this routine is active,
                # deactivate other routines.
                # ------------------------------------------------

                if is_active:

                    cursor.execute(
                        """
                        UPDATE routine_uploads
                        SET is_active = 0
                        """
                    )


                # ------------------------------------------------
                # INSERT
                # ------------------------------------------------

                cursor.execute(
                    """
                    INSERT INTO routine_uploads
                    (
                        id,
                        title,
                        academic_year,
                        department,
                        semester,
                        description,
                        photo,
                        is_active
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
                        next_id,
                        title,
                        academic_year or None,
                        department or None,
                        semester or None,
                        description or None,
                        saved_photo,
                        1 if is_active else 0
                    )
                )


                mysql.connection.commit()


                flash(
                    "Routine photo uploaded successfully.",
                    "success"
                )


                return redirect(
                    url_for("routine.index")
                )


            except ValueError as e:

                if saved_photo:
                    delete_photo(
                        saved_photo
                    )

                try:
                    mysql.connection.rollback()
                except Exception:
                    pass

                flash(
                    str(e),
                    "danger"
                )


            except Exception as e:

                if saved_photo:
                    delete_photo(
                        saved_photo
                    )

                try:
                    mysql.connection.rollback()
                except Exception:
                    pass

                print(
                    "ROUTINE UPLOAD ERROR:",
                    repr(e)
                )

                flash(
                    f"Unable to upload routine: {str(e)}",
                    "danger"
                )


        # ====================================================
        # GET ROUTINES
        # ====================================================

        cursor.execute(
            """
            SELECT
                id,
                title,
                academic_year,
                department,
                semester,
                description,
                photo,
                is_active,
                uploaded_at
            FROM routine_uploads
            ORDER BY
                is_active DESC,
                uploaded_at DESC
            """
        )

        routines = cursor.fetchall()


        # ====================================================
        # RENDER
        # ====================================================

        return render_template(
            "admin/routines.html",
            routines=routines
        )


    except Exception as e:

        if mysql:

            try:
                mysql.connection.rollback()
            except Exception:
                pass

        print(
            "================================================"
        )

        print(
            "ROUTINE LIST ERROR:",
            repr(e)
        )

        print(
            "================================================"
        )

        flash(
            f"Unable to load routines: {str(e)}",
            "danger"
        )

        return redirect(
            url_for("admin.dashboard")
        )


    finally:

        if cursor:

            try:
                cursor.close()

            except Exception:
                pass


# ============================================================
# SET CURRENT ROUTINE
# ============================================================

@routine.route(
    "/set-current/<int:routine_id>",
    methods=["POST"]
)
def set_current(routine_id):

    if not admin_required():

        flash(
            "Please login as administrator.",
            "warning"
        )

        return admin_login_redirect()


    mysql = None
    cursor = None


    try:

        mysql = get_mysql()

        cursor = mysql.connection.cursor()


        cursor.execute(
            """
            SELECT id
            FROM routine_uploads
            WHERE id = %s
            LIMIT 1
            """,
            (routine_id,)
        )

        routine_data = cursor.fetchone()


        if not routine_data:

            flash(
                "Routine not found.",
                "danger"
            )

            return redirect(
                url_for("routine.index")
            )


        # ----------------------------------------------------
        # Deactivate all
        # ----------------------------------------------------

        cursor.execute(
            """
            UPDATE routine_uploads
            SET is_active = 0
            """
        )


        # ----------------------------------------------------
        # Activate selected
        # ----------------------------------------------------

        cursor.execute(
            """
            UPDATE routine_uploads
            SET is_active = 1
            WHERE id = %s
            """,
            (routine_id,)
        )


        mysql.connection.commit()


        flash(
            "Current routine updated successfully.",
            "success"
        )


    except Exception as e:

        if mysql:

            try:
                mysql.connection.rollback()
            except Exception:
                pass

        print(
            "SET CURRENT ROUTINE ERROR:",
            repr(e)
        )

        flash(
            f"Unable to set current routine: {str(e)}",
            "danger"
        )


    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass


    return redirect(
        url_for("routine.index")
    )


# ============================================================
# DELETE ROUTINE
# ============================================================

@routine.route(
    "/delete/<int:routine_id>",
    methods=["POST"]
)
def delete(routine_id):

    if not admin_required():

        flash(
            "Please login as administrator.",
            "warning"
        )

        return admin_login_redirect()


    mysql = None
    cursor = None


    try:

        mysql = get_mysql()

        cursor = mysql.connection.cursor()


        # ----------------------------------------------------
        # Find routine
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT photo
            FROM routine_uploads
            WHERE id = %s
            LIMIT 1
            """,
            (routine_id,)
        )

        row = cursor.fetchone()


        if not row:

            flash(
                "Routine not found.",
                "danger"
            )

            return redirect(
                url_for("routine.index")
            )


        photo = row[0]


        # ----------------------------------------------------
        # Delete database row
        # ----------------------------------------------------

        cursor.execute(
            """
            DELETE FROM routine_uploads
            WHERE id = %s
            """,
            (routine_id,)
        )


        mysql.connection.commit()


        # ----------------------------------------------------
        # Delete photo
        # ----------------------------------------------------

        delete_photo(
            photo
        )


        flash(
            "Routine deleted successfully.",
            "success"
        )


    except Exception as e:

        if mysql:

            try:
                mysql.connection.rollback()
            except Exception:
                pass

        print(
            "DELETE ROUTINE ERROR:",
            repr(e)
        )

        flash(
            f"Unable to delete routine: {str(e)}",
            "danger"
        )


    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass


    return redirect(
        url_for("routine.index")
    )


# ============================================================
# END
# ============================================================