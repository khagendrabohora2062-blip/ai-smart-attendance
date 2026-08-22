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


students = Blueprint(
    "students",
    __name__,
    url_prefix="/students"
)


UPLOAD_FOLDER = os.path.join(
    "static",
    "uploads",
    "students"
)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ======================================================
# Student List
# ======================================================
@students.route("/")
def index():

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT
            id,
            student_id,
            full_name,
            department,
            semester,
            photo
        FROM students
        ORDER BY id DESC
    """)

    student_data = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin/students.html",
        students=student_data
    )


# ======================================================
# Add Student
# ======================================================
@students.route("/add", methods=["GET", "POST"])
def add_student():

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    if request.method == "POST":

        student_id = request.form["student_id"].strip()
        full_name = request.form["full_name"].strip()
        department = request.form["department"].strip()
        semester = request.form["semester"]

        photo_name = None

        photo = request.files.get("photo")

        if photo and photo.filename != "":

            filename = secure_filename(photo.filename)

            ext = os.path.splitext(filename)[1].lower()

            if ext not in [".jpg", ".jpeg", ".png"]:

                flash(
                    "Only JPG, JPEG and PNG files are allowed.",
                    "danger"
                )

                return redirect(
                    url_for("students.add_student")
                )

            photo_name = uuid.uuid4().hex + ext

            photo.save(
                os.path.join(
                    UPLOAD_FOLDER,
                    photo_name
                )
            )

        cursor = mysql.connection.cursor()

        cursor.execute(
            """
            SELECT id
            FROM students
            WHERE student_id=%s
            """,
            (student_id,)
        )

        if cursor.fetchone():

            cursor.close()

            flash(
                "Student ID already exists!",
                "danger"
            )

            return redirect(
                url_for("students.add_student")
            )

        cursor.execute("""
            INSERT INTO students
            (
                student_id,
                full_name,
                department,
                semester,
                photo
            )

            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s
            )
        """,
        (
            student_id,
            full_name,
            department,
            semester,
            photo_name
        ))

        mysql.connection.commit()

        cursor.close()

        flash(
            "Student added successfully!",
            "success"
        )

        return redirect(
            url_for("students.index")
        )

    return render_template(
        "admin/add_student.html"
    )


# ======================================================
# Edit Student
# ======================================================
@students.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_student(id):

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    cursor = mysql.connection.cursor()

    # -------------------------------
    # UPDATE
    # -------------------------------
    if request.method == "POST":

        student_id = request.form["student_id"].strip()
        full_name = request.form["full_name"].strip()
        department = request.form["department"].strip()
        semester = request.form["semester"]

        # Current photo
        cursor.execute(
            """
            SELECT photo
            FROM students
            WHERE id=%s
            """,
            (id,)
        )

        data = cursor.fetchone()

        old_photo = None

        if data:
            old_photo = data[0]

        photo_name = old_photo

        photo = request.files.get("photo")

        if photo and photo.filename != "":

            filename = secure_filename(photo.filename)

            ext = os.path.splitext(filename)[1].lower()

            if ext not in [".jpg", ".jpeg", ".png"]:

                flash(
                    "Only JPG, JPEG and PNG files are allowed.",
                    "danger"
                )

                cursor.close()

                return redirect(
                    url_for("students.edit_student", id=id)
                )

            photo_name = uuid.uuid4().hex + ext

            photo.save(
                os.path.join(
                    UPLOAD_FOLDER,
                    photo_name
                )
            )

            # Delete old image
            if old_photo:

                old_path = os.path.join(
                    UPLOAD_FOLDER,
                    old_photo
                )

                if os.path.exists(old_path):
                    os.remove(old_path)

        cursor.execute(
            """
            UPDATE students

            SET
                student_id=%s,
                full_name=%s,
                department=%s,
                semester=%s,
                photo=%s

            WHERE id=%s
            """,
            (
                student_id,
                full_name,
                department,
                semester,
                photo_name,
                id
            )
        )

        mysql.connection.commit()

        cursor.close()

        flash(
            "Student updated successfully!",
            "success"
        )

        return redirect(
            url_for("students.index")
        )

    # -------------------------------
    # GET
    # -------------------------------

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

        WHERE id=%s
        """,
        (id,)
    )

    student = cursor.fetchone()

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


# ======================================================
# Delete Student
# ======================================================
@students.route("/delete/<int:id>")
def delete_student(id):

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    cursor = mysql.connection.cursor()

    # Find student photo
    cursor.execute(
        """
        SELECT photo
        FROM students
        WHERE id=%s
        """,
        (id,)
    )

    data = cursor.fetchone()

    if data and data[0]:

        photo_path = os.path.join(
            UPLOAD_FOLDER,
            data[0]
        )

        if os.path.exists(photo_path):
            os.remove(photo_path)

    cursor.execute(
        """
        DELETE FROM students
        WHERE id=%s
        """,
        (id,)
    )

    mysql.connection.commit()

    cursor.close()

    flash(
        "Student deleted successfully!",
        "success"
    )

    return redirect(
        url_for("students.index")
    )


# ======================================================
# Register Face
# ======================================================
@students.route("/register-face/<int:student_id>")
def register_face(student_id):

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    return redirect(
        url_for(
            "face.register_face",
            student_id=student_id
        )
    )


# ======================================================
# Generate QR Code
# ======================================================
@students.route("/generate-qr/<int:id>")
def generate_student_qr(id):

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    cursor = mysql.connection.cursor()

    cursor.execute(
        """
        SELECT student_id
        FROM students
        WHERE id=%s
        """,
        (id,)
    )

    student = cursor.fetchone()

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
            f"QR Generation Error : {e}",
            "danger"
        )

    return redirect(
        url_for("students.index")
    )


# ======================================================
# View QR Code
# ======================================================
@students.route("/view-qr/<student_id>")
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

# ======================================================
# Change Student Photo
# ======================================================
@students.route("/change-photo/<int:id>", methods=["GET", "POST"])
def change_photo(id):

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT photo
        FROM students
        WHERE id=%s
    """, (id,))

    student = cursor.fetchone()

    if not student:

        cursor.close()

        flash(
            "Student not found!",
            "danger"
        )

        return redirect(url_for("students.index"))

    old_photo = student[0]

    if request.method == "POST":

        photo = request.files.get("photo")

        if not photo or photo.filename == "":

            flash(
                "Please select a photo.",
                "warning"
            )

            return redirect(
                url_for("students.change_photo", id=id)
            )

        filename = secure_filename(photo.filename)

        ext = os.path.splitext(filename)[1].lower()

        if ext not in [".jpg", ".jpeg", ".png"]:

            flash(
                "Only JPG, JPEG and PNG are allowed.",
                "danger"
            )

            return redirect(
                url_for("students.change_photo", id=id)
            )

        new_photo = uuid.uuid4().hex + ext

        photo.save(
            os.path.join(
                UPLOAD_FOLDER,
                new_photo
            )
        )

        if old_photo:

            old_path = os.path.join(
                UPLOAD_FOLDER,
                old_photo
            )

            if os.path.exists(old_path):

                os.remove(old_path)

        cursor.execute("""
            UPDATE students
            SET photo=%s
            WHERE id=%s
        """, (new_photo, id))

        mysql.connection.commit()

        cursor.close()

        flash(
            "Profile photo updated successfully.",
            "success"
        )

        return redirect(
            url_for("students.index")
        )

    cursor.close()

    return render_template(
    "admin/change_photo.html",
    id=id,
    photo=old_photo
)
# ======================================================
# Remove Student Photo
# ======================================================
@students.route("/remove-photo/<int:id>")
def remove_photo(id):

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT photo
        FROM students
        WHERE id=%s
    """, (id,))

    student = cursor.fetchone()

    if student and student[0]:

        photo_path = os.path.join(
            UPLOAD_FOLDER,
            student[0]
        )

        if os.path.exists(photo_path):

            os.remove(photo_path)

        cursor.execute("""
            UPDATE students
            SET photo=NULL
            WHERE id=%s
        """, (id,))

        mysql.connection.commit()

    cursor.close()

    flash(
        "Profile photo removed successfully.",
        "success"
    )

    return redirect(
        url_for("students.index")
    )