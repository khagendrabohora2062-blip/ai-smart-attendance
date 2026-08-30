from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    request,
    flash,
    send_from_directory
)

from extensions import mysql
from utils.generate_qr import generate_qr
from werkzeug.utils import secure_filename

import os
import uuid


# =========================================================
# BLUEPRINT
# =========================================================

students = Blueprint(
    "students",
    __name__,
    url_prefix="/students"
)


# =========================================================
# UPLOAD FOLDER
# =========================================================

UPLOAD_FOLDER = os.path.join(
    "static",
    "uploads",
    "students"
)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =========================================================
# HELPER: GENERATE UNIQUE INTEGER ID
# =========================================================

def generate_student_db_id(cursor):
    """
    Generates a unique positive integer ID for students.id.

    This is used because the TiDB/MySQL table currently has:
        id INT NOT NULL PRIMARY KEY

    but id is NOT AUTO_INCREMENT.
    """

    while True:
        new_id = uuid.uuid4().int % 2147483647

        # Avoid 0
        if new_id <= 0:
            continue

        cursor.execute(
            """
            SELECT id
            FROM students
            WHERE id=%s
            LIMIT 1
            """,
            (new_id,)
        )

        if cursor.fetchone() is None:
            return new_id


# =========================================================
# HELPER: ALLOWED PHOTO
# =========================================================

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png"
}


def save_student_photo(photo):
    """
    Saves student photo and returns filename.
    Returns None if no photo was uploaded.
    """

    if not photo or not photo.filename:
        return None

    filename = secure_filename(photo.filename)

    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            "Only JPG, JPEG and PNG files are allowed."
        )

    new_filename = uuid.uuid4().hex + ext

    file_path = os.path.join(
        UPLOAD_FOLDER,
        new_filename
    )

    photo.save(file_path)

    return new_filename


# =========================================================
# HELPER: DELETE PHOTO FILE
# =========================================================

def delete_photo_file(photo_name):
    if not photo_name:
        return

    photo_path = os.path.join(
        UPLOAD_FOLDER,
        photo_name
    )

    try:
        if os.path.exists(photo_path):
            os.remove(photo_path)
    except OSError:
        pass


# =========================================================
# STUDENT LIST
# =========================================================

@students.route("/")
def index():

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                id,
                student_id,
                full_name,
                department,
                semester,
                photo
            FROM students
            ORDER BY id DESC
            """
        )

        student_data = cursor.fetchall()

    except Exception as e:

        flash(
            f"Unable to load students: {e}",
            "danger"
        )

        student_data = []

    finally:
        cursor.close()

    return render_template(
        "admin/students.html",
        students=student_data
    )


# =========================================================
# ADD STUDENT
# =========================================================

@students.route("/add", methods=["GET", "POST"])
def add_student():

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    if request.method == "POST":

        student_id = request.form.get(
            "student_id",
            ""
        ).strip()

        full_name = request.form.get(
            "full_name",
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

        photo_name = None
        photo_saved = False

        # ---------------------------------------------
        # BASIC VALIDATION
        # ---------------------------------------------

        if not student_id:
            flash(
                "Student ID is required.",
                "danger"
            )

            return redirect(
                url_for("students.add_student")
            )

        if not full_name:
            flash(
                "Full name is required.",
                "danger"
            )

            return redirect(
                url_for("students.add_student")
            )

        if not department:
            flash(
                "Department is required.",
                "danger"
            )

            return redirect(
                url_for("students.add_student")
            )

        if not semester:
            flash(
                "Semester is required.",
                "danger"
            )

            return redirect(
                url_for("students.add_student")
            )

        cursor = mysql.connection.cursor()

        try:

            # -----------------------------------------
            # CHECK DUPLICATE STUDENT ID
            # -----------------------------------------

            cursor.execute(
                """
                SELECT id
                FROM students
                WHERE student_id=%s
                LIMIT 1
                """,
                (student_id,)
            )

            existing_student = cursor.fetchone()

            if existing_student:

                flash(
                    "Student ID already exists!",
                    "danger"
                )

                return redirect(
                    url_for("students.add_student")
                )

            # -----------------------------------------
            # CHECK DUPLICATE EMAIL IF FORM HAS EMAIL
            # -----------------------------------------

            email = request.form.get(
                "email",
                ""
            ).strip()

            if email:

                cursor.execute(
                    """
                    SELECT id
                    FROM students
                    WHERE email=%s
                    LIMIT 1
                    """,
                    (email,)
                )

                existing_email = cursor.fetchone()

                if existing_email:

                    flash(
                        "Email already exists!",
                        "danger"
                    )

                    return redirect(
                        url_for("students.add_student")
                    )

            else:
                email = None

            # -----------------------------------------
            # OTHER OPTIONAL FIELDS
            # -----------------------------------------

            phone = request.form.get(
                "phone",
                ""
            ).strip()

            phone = phone if phone else None

            section = request.form.get(
                "section",
                ""
            ).strip()

            section = section if section else None

            password = request.form.get(
                "password",
                ""
            )

            if not password:
                password = ""

            # -----------------------------------------
            # SAVE PHOTO
            # -----------------------------------------

            photo = request.files.get("photo")

            if photo and photo.filename:

                try:

                    photo_name = save_student_photo(
                        photo
                    )

                    photo_saved = True

                except ValueError as e:

                    flash(
                        str(e),
                        "danger"
                    )

                    return redirect(
                        url_for(
                            "students.add_student"
                        )
                    )

            # -----------------------------------------
            # GENERATE DATABASE PRIMARY KEY
            # -----------------------------------------

            db_id = generate_student_db_id(
                cursor
            )

            # -----------------------------------------
            # INSERT STUDENT
            # -----------------------------------------

            cursor.execute(
                """
                INSERT INTO students
                (
                    id,
                    student_id,
                    full_name,
                    email,
                    phone,
                    department,
                    semester,
                    section,
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
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    db_id,
                    student_id,
                    full_name,
                    email,
                    phone,
                    department,
                    semester,
                    section,
                    password,
                    photo_name
                )
            )

            mysql.connection.commit()

            flash(
                "Student added successfully!",
                "success"
            )

            return redirect(
                url_for("students.index")
            )

        except Exception as e:

            # -----------------------------------------
            # ROLLBACK DATABASE
            # -----------------------------------------

            try:
                mysql.connection.rollback()
            except Exception:
                pass

            # -----------------------------------------
            # REMOVE PHOTO IF DATABASE INSERT FAILED
            # -----------------------------------------

            if photo_saved and photo_name:
                delete_photo_file(photo_name)

            flash(
                f"Error adding student: {e}",
                "danger"
            )

            return redirect(
                url_for("students.add_student")
            )

        finally:
            cursor.close()

    return render_template(
        "admin/add_student.html"
    )


# =========================================================
# EDIT STUDENT
# =========================================================

@students.route(
    "/edit/<int:id>",
    methods=["GET", "POST"]
)
def edit_student(id):

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    cursor = mysql.connection.cursor()

    # =====================================================
    # UPDATE
    # =====================================================

    if request.method == "POST":

        student_id = request.form.get(
            "student_id",
            ""
        ).strip()

        full_name = request.form.get(
            "full_name",
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

        email = request.form.get(
            "email",
            ""
        ).strip()

        email = email if email else None

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        phone = phone if phone else None

        section = request.form.get(
            "section",
            ""
        ).strip()

        section = section if section else None

        old_photo = None
        new_photo_name = None
        new_photo_saved = False

        try:

            # -----------------------------------------
            # GET CURRENT STUDENT
            # -----------------------------------------

            cursor.execute(
                """
                SELECT
                    id,
                    student_id,
                    full_name,
                    email,
                    phone,
                    department,
                    semester,
                    section,
                    password,
                    photo
                FROM students
                WHERE id=%s
                LIMIT 1
                """,
                (id,)
            )

            current_student = cursor.fetchone()

            if not current_student:

                flash(
                    "Student not found!",
                    "danger"
                )

                return redirect(
                    url_for("students.index")
                )

            old_photo = current_student[9]

            # -----------------------------------------
            # VALIDATION
            # -----------------------------------------

            if not student_id:
                flash(
                    "Student ID is required.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "students.edit_student",
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
                        "students.edit_student",
                        id=id
                    )
                )

            # -----------------------------------------
            # CHECK DUPLICATE STUDENT ID
            # EXCLUDING CURRENT STUDENT
            # -----------------------------------------

            cursor.execute(
                """
                SELECT id
                FROM students
                WHERE student_id=%s
                AND id<>%s
                LIMIT 1
                """,
                (
                    student_id,
                    id
                )
            )

            duplicate_student_id = cursor.fetchone()

            if duplicate_student_id:

                flash(
                    "Student ID already exists!",
                    "danger"
                )

                return redirect(
                    url_for(
                        "students.edit_student",
                        id=id
                    )
                )

            # -----------------------------------------
            # CHECK DUPLICATE EMAIL
            # -----------------------------------------

            if email:

                cursor.execute(
                    """
                    SELECT id
                    FROM students
                    WHERE email=%s
                    AND id<>%s
                    LIMIT 1
                    """,
                    (
                        email,
                        id
                    )
                )

                duplicate_email = cursor.fetchone()

                if duplicate_email:

                    flash(
                        "Email already exists!",
                        "danger"
                    )

                    return redirect(
                        url_for(
                            "students.edit_student",
                            id=id
                        )
                    )

            # -----------------------------------------
            # PHOTO
            # -----------------------------------------

            photo_name = old_photo

            photo = request.files.get("photo")

            if photo and photo.filename:

                try:

                    new_photo_name = save_student_photo(
                        photo
                    )

                    new_photo_saved = True

                    photo_name = new_photo_name

                except ValueError as e:

                    flash(
                        str(e),
                        "danger"
                    )

                    return redirect(
                        url_for(
                            "students.edit_student",
                            id=id
                        )
                    )

            # -----------------------------------------
            # UPDATE
            # -----------------------------------------

            cursor.execute(
                """
                UPDATE students
                SET
                    student_id=%s,
                    full_name=%s,
                    email=%s,
                    phone=%s,
                    department=%s,
                    semester=%s,
                    section=%s,
                    photo=%s
                WHERE id=%s
                """,
                (
                    student_id,
                    full_name,
                    email,
                    phone,
                    department,
                    semester,
                    section,
                    photo_name,
                    id
                )
            )

            mysql.connection.commit()

            # -----------------------------------------
            # DELETE OLD PHOTO AFTER SUCCESSFUL COMMIT
            # -----------------------------------------

            if (
                new_photo_saved
                and old_photo
                and old_photo != photo_name
            ):
                delete_photo_file(old_photo)

            flash(
                "Student updated successfully!",
                "success"
            )

            return redirect(
                url_for("students.index")
            )

        except Exception as e:

            try:
                mysql.connection.rollback()
            except Exception:
                pass

            if new_photo_saved and new_photo_name:
                delete_photo_file(
                    new_photo_name
                )

            flash(
                f"Error updating student: {e}",
                "danger"
            )

            return redirect(
                url_for(
                    "students.edit_student",
                    id=id
                )
            )

        finally:
            cursor.close()

    # =====================================================
    # GET
    # =====================================================

    try:

        cursor.execute(
            """
            SELECT
                id,
                student_id,
                full_name,
                email,
                phone,
                department,
                semester,
                section,
                password,
                photo
            FROM students
            WHERE id=%s
            LIMIT 1
            """,
            (id,)
        )

        student = cursor.fetchone()

    except Exception as e:

        flash(
            f"Error loading student: {e}",
            "danger"
        )

        student = None

    finally:
        cursor.close()

    if not student:

        flash(
            "Student not found!",
            "danger"
        )

        return redirect(
            url_for("students.index")
        )

    return render_template(
        "admin/edit_student.html",
        student=student
    )


# =========================================================
# DELETE STUDENT
# =========================================================

@students.route("/delete/<int:id>")
def delete_student(id):

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    cursor = mysql.connection.cursor()

    try:

        # ---------------------------------------------
        # GET PHOTO
        # ---------------------------------------------

        cursor.execute(
            """
            SELECT photo
            FROM students
            WHERE id=%s
            LIMIT 1
            """,
            (id,)
        )

        data = cursor.fetchone()

        if not data:

            flash(
                "Student not found!",
                "danger"
            )

            return redirect(
                url_for("students.index")
            )

        old_photo = data[0]

        # ---------------------------------------------
        # DELETE DATABASE RECORD
        # ---------------------------------------------

        cursor.execute(
            """
            DELETE FROM students
            WHERE id=%s
            """,
            (id,)
        )

        mysql.connection.commit()

        # ---------------------------------------------
        # DELETE PHOTO AFTER DATABASE SUCCESS
        # ---------------------------------------------

        if old_photo:
            delete_photo_file(old_photo)

        flash(
            "Student deleted successfully!",
            "success"
        )

    except Exception as e:

        try:
            mysql.connection.rollback()
        except Exception:
            pass

        flash(
            f"Error deleting student: {e}",
            "danger"
        )

    finally:
        cursor.close()

    return redirect(
        url_for("students.index")
    )


# =========================================================
# REGISTER FACE
# =========================================================

@students.route(
    "/register-face/<int:student_id>"
)
def register_face(student_id):

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    return redirect(
        url_for(
            "face.register_face",
            student_id=student_id
        )
    )


# =========================================================
# GENERATE QR CODE
# =========================================================

@students.route(
    "/generate-qr/<int:id>"
)
def generate_student_qr(id):

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT student_id
            FROM students
            WHERE id=%s
            LIMIT 1
            """,
            (id,)
        )

        student = cursor.fetchone()

    finally:
        cursor.close()

    if not student:

        flash(
            "Student not found!",
            "danger"
        )

        return redirect(
            url_for("students.index")
        )

    student_id = student[0]

    try:

        generate_qr(student_id)

        flash(
            f"QR Code generated successfully for {student_id}.",
            "success"
        )

    except Exception as e:

        flash(
            f"QR Generation Error: {e}",
            "danger"
        )

    return redirect(
        url_for("students.index")
    )


# =========================================================
# VIEW QR CODE
# =========================================================

@students.route(
    "/view-qr/<student_id>"
)
def view_qr(student_id):

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    qr_folder = os.path.join(
        "static",
        "qr_codes"
    )

    qr_file = f"{student_id}.png"

    qr_path = os.path.join(
        qr_folder,
        qr_file
    )

    if not os.path.exists(qr_path):

        flash(
            "QR Code not found. Generate QR first.",
            "warning"
        )

        return redirect(
            url_for("students.index")
        )

    return send_from_directory(
        qr_folder,
        qr_file
    )


# =========================================================
# CHANGE STUDENT PHOTO
# =========================================================

@students.route(
    "/change-photo/<int:id>",
    methods=["GET", "POST"]
)
def change_photo(id):

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT photo
            FROM students
            WHERE id=%s
            LIMIT 1
            """,
            (id,)
        )

        student = cursor.fetchone()

        if not student:

            flash(
                "Student not found!",
                "danger"
            )

            return redirect(
                url_for("students.index")
            )

        old_photo = student[0]

        # ---------------------------------------------
        # POST
        # ---------------------------------------------

        if request.method == "POST":

            photo = request.files.get("photo")

            if not photo or not photo.filename:

                flash(
                    "Please select a photo.",
                    "warning"
                )

                return redirect(
                    url_for(
                        "students.change_photo",
                        id=id
                    )
                )

            try:

                new_photo = save_student_photo(
                    photo
                )

            except ValueError as e:

                flash(
                    str(e),
                    "danger"
                )

                return redirect(
                    url_for(
                        "students.change_photo",
                        id=id
                    )
                )

            try:

                cursor.execute(
                    """
                    UPDATE students
                    SET photo=%s
                    WHERE id=%s
                    """,
                    (
                        new_photo,
                        id
                    )
                )

                mysql.connection.commit()

            except Exception:

                try:
                    mysql.connection.rollback()
                except Exception:
                    pass

                delete_photo_file(new_photo)

                raise

            # Delete old photo only after successful DB update
            if old_photo:
                delete_photo_file(old_photo)

            flash(
                "Profile photo updated successfully.",
                "success"
            )

            return redirect(
                url_for("students.index")
            )

        # ---------------------------------------------
        # GET
        # ---------------------------------------------

        return render_template(
            "admin/change_photo.html",
            id=id,
            photo=old_photo
        )

    except Exception as e:

        flash(
            f"Photo update error: {e}",
            "danger"
        )

        return redirect(
            url_for("students.index")
        )

    finally:
        cursor.close()


# =========================================================
# REMOVE STUDENT PHOTO
# =========================================================

@students.route(
    "/remove-photo/<int:id>"
)
def remove_photo(id):

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT photo
            FROM students
            WHERE id=%s
            LIMIT 1
            """,
            (id,)
        )

        student = cursor.fetchone()

        if not student:

            flash(
                "Student not found!",
                "danger"
            )

            return redirect(
                url_for("students.index")
            )

        old_photo = student[0]

        if old_photo:

            cursor.execute(
                """
                UPDATE students
                SET photo=NULL
                WHERE id=%s
                """,
                (id,)
            )

            mysql.connection.commit()

            delete_photo_file(old_photo)

            flash(
                "Profile photo removed successfully.",
                "success"
            )

        else:

            flash(
                "Student does not have a profile photo.",
                "warning"
            )

    except Exception as e:

        try:
            mysql.connection.rollback()
        except Exception:
            pass

        flash(
            f"Error removing photo: {e}",
            "danger"
        )

    finally:
        cursor.close()

    return redirect(
        url_for("students.index")
    )