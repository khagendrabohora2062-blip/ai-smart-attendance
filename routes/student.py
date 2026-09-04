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
from werkzeug.security import generate_password_hash

import os
import uuid


# ============================================================
# BLUEPRINT
# ============================================================

students = Blueprint(
    "students",
    __name__,
    url_prefix="/students"
)


# ============================================================
# STUDENT PHOTO UPLOAD FOLDER
# ============================================================

UPLOAD_FOLDER = os.path.join(
    "static",
    "uploads",
    "students"
)

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)


# ============================================================
# ALLOWED PHOTO EXTENSIONS
# ============================================================

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp"
}


# ============================================================
# ADMIN CHECK
# ============================================================

def admin_required():
    return "admin_id" in session


# ============================================================
# GENERATE UNIQUE STUDENT DATABASE ID
# ============================================================

def generate_student_db_id(cursor):

    while True:

        new_id = uuid.uuid4().int % 2147483647

        if new_id <= 0:
            continue

        cursor.execute(
            """
            SELECT id
            FROM students
            WHERE id = %s
            LIMIT 1
            """,
            (new_id,)
        )

        if cursor.fetchone() is None:
            return new_id


# ============================================================
# SAVE STUDENT PHOTO
# ============================================================

def save_student_photo(photo):

    if not photo or not photo.filename:
        return None

    filename = secure_filename(
        photo.filename
    )

    ext = os.path.splitext(
        filename
    )[1].lower()

    if ext not in ALLOWED_EXTENSIONS:

        raise ValueError(
            "Only JPG, JPEG, PNG and WEBP files are allowed."
        )

    new_filename = (
        uuid.uuid4().hex + ext
    )

    file_path = os.path.join(
        UPLOAD_FOLDER,
        new_filename
    )

    photo.save(file_path)

    return new_filename


# ============================================================
# DELETE PHOTO FILE
# ============================================================

def delete_photo_file(photo_name):

    if not photo_name:
        return

    file_path = os.path.join(
        UPLOAD_FOLDER,
        photo_name
    )

    try:

        if os.path.exists(file_path):
            os.remove(file_path)

    except OSError:
        pass


# ============================================================
# STUDENT LIST
# ============================================================

@students.route("/")
def index():

    if not admin_required():
        return redirect(
            url_for("auth.login")
        )

    cursor = mysql.connection.cursor()

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


# ============================================================
# ADD STUDENT
# ============================================================

@students.route(
    "/add",
    methods=["GET", "POST"]
)
def add_student():

    if not admin_required():
        return redirect(
            url_for("auth.login")
        )

    if request.method == "POST":

        student_id = request.form.get(
            "student_id",
            ""
        ).strip()

        full_name = request.form.get(
            "full_name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
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

        section = request.form.get(
            "section",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        email = email if email else None
        phone = phone if phone else None
        section = section if section else None

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not student_id:

            flash(
                "Student ID is required.",
                "danger"
            )

            return redirect(
                url_for(
                    "students.add_student"
                )
            )

        if not full_name:

            flash(
                "Full name is required.",
                "danger"
            )

            return redirect(
                url_for(
                    "students.add_student"
                )
            )

        if not department:

            flash(
                "Department is required.",
                "danger"
            )

            return redirect(
                url_for(
                    "students.add_student"
                )
            )

        if not semester:

            flash(
                "Semester is required.",
                "danger"
            )

            return redirect(
                url_for(
                    "students.add_student"
                )
            )

        cursor = mysql.connection.cursor()

        photo_name = None
        photo_saved = False

        try:

            # ------------------------------------------------
            # DUPLICATE STUDENT ID
            # ------------------------------------------------

            cursor.execute(
                """
                SELECT id
                FROM students
                WHERE student_id = %s
                LIMIT 1
                """,
                (student_id,)
            )

            if cursor.fetchone():

                flash(
                    "Student ID already exists!",
                    "danger"
                )

                return redirect(
                    url_for(
                        "students.add_student"
                    )
                )

            # ------------------------------------------------
            # DUPLICATE EMAIL
            # ------------------------------------------------

            if email:

                cursor.execute(
                    """
                    SELECT id
                    FROM students
                    WHERE email = %s
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
                        url_for(
                            "students.add_student"
                        )
                    )

            # ------------------------------------------------
            # PHOTO
            # ------------------------------------------------

            photo = request.files.get(
                "photo"
            )

            if photo and photo.filename:

                photo_name = save_student_photo(
                    photo
                )

                photo_saved = True

            # ------------------------------------------------
            # GENERATE DB ID
            # ------------------------------------------------

            db_id = generate_student_db_id(
                cursor
            )

            # ------------------------------------------------
            # INSERT STUDENT
            #
            # NO MARKS
            # NO FULL MARKS
            # NO SUBJECT
            # ------------------------------------------------

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
                url_for(
                    "students.index"
                )
            )

        except Exception as e:

            try:
                mysql.connection.rollback()
            except Exception:
                pass

            if photo_saved and photo_name:
                delete_photo_file(
                    photo_name
                )

            flash(
                f"Error adding student: {e}",
                "danger"
            )

            return redirect(
                url_for(
                    "students.add_student"
                )
            )

        finally:

            cursor.close()

    return render_template(
        "admin/add_student.html"
    )


# ============================================================
# EDIT STUDENT
# ============================================================

@students.route(
    "/edit/<int:id>",
    methods=["GET", "POST"]
)
def edit_student(id):

    if not admin_required():
        return redirect(
            url_for("auth.login")
        )

    cursor = mysql.connection.cursor()

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
            WHERE id = %s
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

        if request.method == "POST":

            student_id = request.form.get(
                "student_id",
                ""
            ).strip()

            full_name = request.form.get(
                "full_name",
                ""
            ).strip()

            email = request.form.get(
                "email",
                ""
            ).strip()

            phone = request.form.get(
                "phone",
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

            section = request.form.get(
                "section",
                ""
            ).strip()

            email = email if email else None
            phone = phone if phone else None
            section = section if section else None

            if not student_id or not full_name:

                flash(
                    "Student ID and Full Name are required.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "students.edit_student",
                        id=id
                    )
                )

            # ------------------------------------------------
            # DUPLICATE STUDENT ID
            # ------------------------------------------------

            cursor.execute(
                """
                SELECT id
                FROM students
                WHERE student_id = %s
                  AND id <> %s
                LIMIT 1
                """,
                (
                    student_id,
                    id
                )
            )

            if cursor.fetchone():

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

            # ------------------------------------------------
            # DUPLICATE EMAIL
            # ------------------------------------------------

            if email:

                cursor.execute(
                    """
                    SELECT id
                    FROM students
                    WHERE email = %s
                      AND id <> %s
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
                            "students.edit_student",
                            id=id
                        )
                    )

            old_photo = student[9]

            photo_name = old_photo
            new_photo = None

            photo = request.files.get(
                "photo"
            )

            if photo and photo.filename:

                new_photo = save_student_photo(
                    photo
                )

                photo_name = new_photo

            # ------------------------------------------------
            # UPDATE
            # ------------------------------------------------

            cursor.execute(
                """
                UPDATE students
                SET
                    student_id = %s,
                    full_name = %s,
                    email = %s,
                    phone = %s,
                    department = %s,
                    semester = %s,
                    section = %s,
                    photo = %s
                WHERE id = %s
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

            if new_photo and old_photo:
                delete_photo_file(
                    old_photo
                )

            flash(
                "Student updated successfully!",
                "success"
            )

            return redirect(
                url_for("students.index")
            )

        return render_template(
            "admin/edit_student.html",
            student=student
        )

    except Exception as e:

        try:
            mysql.connection.rollback()
        except Exception:
            pass

        flash(
            f"Error updating student: {e}",
            "danger"
        )

        return redirect(
            url_for("students.index")
        )

    finally:

        cursor.close()


# ============================================================
# DELETE STUDENT
# ============================================================

@students.route(
    "/delete/<int:id>",
    methods=["POST", "GET"]
)
def delete_student(id):

    if not admin_required():
        return redirect(
            url_for("auth.login")
        )

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT photo
            FROM students
            WHERE id = %s
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

        cursor.execute(
            """
            DELETE FROM students
            WHERE id = %s
            """,
            (id,)
        )

        mysql.connection.commit()

        if old_photo:
            delete_photo_file(
                old_photo
            )

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


# ============================================================
# RESET STUDENT PASSWORD
# ============================================================

@students.route(
    "/reset-password/<int:id>",
    methods=["POST"]
)
def reset_student_password(id):

    if not admin_required():
        return redirect(
            url_for("auth.login")
        )

    # --------------------------------------------------------
    # DEFAULT TEMPORARY PASSWORD
    # --------------------------------------------------------
    # The student should change this after logging in.
    temporary_password = "student123"

    cursor = mysql.connection.cursor()

    try:

        # ----------------------------------------------------
        # CHECK STUDENT
        # ----------------------------------------------------
        cursor.execute(
            """
            SELECT
                id,
                student_id,
                full_name
            FROM students
            WHERE id = %s
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

        # ----------------------------------------------------
        # HASH TEMPORARY PASSWORD
        # ----------------------------------------------------
        password_hash = generate_password_hash(
            temporary_password
        )

        # ----------------------------------------------------
        # UPDATE PASSWORD
        # ----------------------------------------------------
        cursor.execute(
            """
            UPDATE students
            SET password = %s
            WHERE id = %s
            """,
            (
                password_hash,
                id
            )
        )

        mysql.connection.commit()

        flash(
            f"Password reset successfully for {student[2]}. Temporary password: {temporary_password}",
            "success"
        )

    except Exception as e:

        try:
            mysql.connection.rollback()
        except Exception:
            pass

        flash(
            f"Unable to reset student password: {e}",
            "danger"
        )

    finally:

        cursor.close()

    return redirect(
        url_for("students.index")
    )


# ============================================================
# REGISTER FACE
# ============================================================

@students.route(
    "/register-face/<int:student_id>"
)
def register_face(student_id):

    if not admin_required():
        return redirect(
            url_for("auth.login")
        )

    return redirect(
        url_for(
            "face.register_face",
            student_id=student_id
        )
    )


# ============================================================
# GENERATE QR
# ============================================================

@students.route(
    "/generate-qr/<int:id>"
)
def generate_student_qr(id):

    if not admin_required():
        return redirect(
            url_for("auth.login")
        )

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT student_id
            FROM students
            WHERE id = %s
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

    student_code = student[0]

    try:

        generate_qr(
            student_code
        )

        flash(
            f"QR Code generated successfully for {student_code}.",
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


# ============================================================
# VIEW QR
# ============================================================

@students.route(
    "/view-qr/<student_id>"
)
def view_qr(student_id):

    if not admin_required():
        return redirect(
            url_for("auth.login")
        )

    qr_folder = os.path.join(
        "static",
        "qr_codes"
    )

    qr_file = (
        f"{student_id}.png"
    )

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


# ============================================================
# CHANGE PHOTO
# ============================================================

@students.route(
    "/change-photo/<int:id>",
    methods=["GET", "POST"]
)
def change_photo(id):

    if not admin_required():
        return redirect(
            url_for("auth.login")
        )

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT photo
            FROM students
            WHERE id = %s
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

        if request.method == "POST":

            photo = request.files.get(
                "photo"
            )

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

            new_photo = save_student_photo(
                photo
            )

            try:

                cursor.execute(
                    """
                    UPDATE students
                    SET photo = %s
                    WHERE id = %s
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

                delete_photo_file(
                    new_photo
                )

                raise

            if old_photo:
                delete_photo_file(
                    old_photo
                )

            flash(
                "Profile photo updated successfully.",
                "success"
            )

            return redirect(
                url_for("students.index")
            )

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


# ============================================================
# REMOVE PHOTO
# ============================================================

@students.route(
    "/remove-photo/<int:id>"
)
def remove_photo(id):

    if not admin_required():
        return redirect(
            url_for("auth.login")
        )

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT photo
            FROM students
            WHERE id = %s
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
                SET photo = NULL
                WHERE id = %s
                """,
                (id,)
            )

            mysql.connection.commit()

            delete_photo_file(
                old_photo
            )

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