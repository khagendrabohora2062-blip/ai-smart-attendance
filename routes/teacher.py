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



# ==========================================
# Allowed Extensions
# ==========================================

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp"
}



def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )




# ==========================================
# Upload Folder
# ==========================================

def get_upload_folder():

    folder = current_app.config.get(
        "UPLOAD_FOLDER"
    )

    if not folder:

        folder = os.path.join(
            current_app.root_path,
            "static",
            "uploads"
        )

    os.makedirs(
        folder,
        exist_ok=True
    )

    return folder




# ==========================================
# Teacher List
# ==========================================

@teachers.route("/")
def index():

    if "admin_id" not in session:
        return redirect(
            url_for("auth.login")
        )


    cursor = mysql.connection.cursor()


    cursor.execute("""
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
    """)


    teachers_data = cursor.fetchall()


    cursor.close()



    return render_template(
        "admin/teachers.html",
        teachers=teachers_data
    )





# ==========================================
# Add Teacher
# ==========================================

@teachers.route(
    "/add",
    methods=["GET","POST"]
)

def add_teacher():


    if "admin_id" not in session:

        return redirect(
            url_for("auth.login")
        )



    if request.method == "POST":


        teacher_id = request.form.get(
            "teacher_id"
        ).strip()


        full_name = request.form.get(
            "full_name"
        ).strip()


        email = request.form.get(
            "email"
        ).strip()


        phone = request.form.get(
            "phone"
        ).strip()



        department = request.form.get(
            "department"
        ).strip()



        photo = request.files.get(
            "photo"
        )



        cursor = mysql.connection.cursor()



        cursor.execute("""
            SELECT id
            FROM teachers
            WHERE teacher_id=%s
        """,
        (teacher_id,)
        )


        if cursor.fetchone():

            cursor.close()

            flash(
                "Teacher ID already exists!",
                "danger"
            )

            return redirect(
                url_for(
                    "teachers.add_teacher"
                )
            )




        cursor.execute("""
            SELECT id
            FROM teachers
            WHERE email=%s
        """,
        (email,)
        )



        if cursor.fetchone():

            cursor.close()

            flash(
                "Email already exists!",
                "danger"
            )

            return redirect(
                url_for(
                    "teachers.add_teacher"
                )
            )




        # -----------------------------
        # Empty Photo
        # -----------------------------

        photo_filename = None




        # -----------------------------
        # Upload Photo
        # -----------------------------


        if photo and photo.filename:


            if not allowed_file(
                photo.filename
            ):

                cursor.close()

                flash(
                    "Invalid image format!",
                    "danger"
                )

                return redirect(
                    url_for(
                        "teachers.add_teacher"
                    )
                )



            ext = photo.filename.rsplit(
                ".",
                1
            )[1].lower()



            photo_filename = (
                "teacher_"
                + uuid.uuid4().hex
                + "."
                + ext
            )



            path = os.path.join(
                get_upload_folder(),
                photo_filename
            )


            photo.save(path)




        cursor.execute("""
            INSERT INTO teachers
            (
                teacher_id,
                full_name,
                email,
                phone,
                department,
                password,
                photo
            )

            VALUES
            (%s,%s,%s,%s,%s,%s,%s)

        """,
        (
            teacher_id,
            full_name,
            email,
            phone,
            department,
            "teacher123",
            photo_filename
        ))



        mysql.connection.commit()

        cursor.close()



        flash(
            "Teacher added successfully!",
            "success"
        )



        return redirect(
            url_for(
                "teachers.index"
            )
        )




    return render_template(
        "admin/add_teacher.html"
    )
# ==========================================
# Edit Teacher
# ==========================================

@teachers.route(
    "/edit/<int:id>",
    methods=["GET", "POST"]
)
def edit_teacher(id):

    if "admin_id" not in session:
        return redirect(
            url_for("auth.login")
        )


    cursor = mysql.connection.cursor()



    if request.method == "POST":


        teacher_id = request.form.get(
            "teacher_id"
        ).strip()


        full_name = request.form.get(
            "full_name"
        ).strip()


        email = request.form.get(
            "email"
        ).strip()


        phone = request.form.get(
            "phone"
        ).strip()


        department = request.form.get(
            "department"
        ).strip()



        photo = request.files.get(
            "photo"
        )


        remove_photo = request.form.get(
            "remove_photo"
        )



        # Get old photo

        cursor.execute("""
            SELECT photo
            FROM teachers
            WHERE id=%s
        """,
        (id,)
        )


        old_data = cursor.fetchone()



        if not old_data:

            cursor.close()

            flash(
                "Teacher not found!",
                "danger"
            )

            return redirect(
                url_for(
                    "teachers.index"
                )
            )



        old_photo = old_data[0]

        photo_filename = old_photo




        # ==================================
        # Remove Existing Photo
        # ==================================

        if remove_photo == "1":


            if old_photo:


                old_path = os.path.join(
                    get_upload_folder(),
                    old_photo
                )


                if os.path.exists(old_path):

                    os.remove(
                        old_path
                    )


            photo_filename = None





        # ==================================
        # Upload New Photo
        # ==================================

        if photo and photo.filename:



            if not allowed_file(
                photo.filename
            ):

                cursor.close()

                flash(
                    "Invalid image format!",
                    "danger"
                )

                return redirect(
                    url_for(
                        "teachers.edit_teacher",
                        id=id
                    )
                )



            extension = photo.filename.rsplit(
                ".",
                1
            )[1].lower()



            new_photo = (
                "teacher_"
                + uuid.uuid4().hex
                + "."
                + extension
            )



            new_path = os.path.join(
                get_upload_folder(),
                new_photo
            )



            photo.save(
                new_path
            )



            # delete old photo

            if old_photo:


                old_path = os.path.join(
                    get_upload_folder(),
                    old_photo
                )


                if os.path.exists(old_path):

                    os.remove(
                        old_path
                    )



            photo_filename = new_photo





        cursor.execute("""
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
        ))



        mysql.connection.commit()

        cursor.close()



        flash(
            "Teacher updated successfully!",
            "success"
        )



        return redirect(
            url_for(
                "teachers.index"
            )
        )





    # GET DATA


    cursor.execute("""
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

    """,
    (id,)
    )


    teacher = cursor.fetchone()


    cursor.close()



    return render_template(
        "admin/edit_teacher.html",
        teacher=teacher
    )






# ==========================================
# Delete Teacher
# ==========================================


@teachers.route(
    "/delete/<int:id>"
)

def delete_teacher(id):


    if "admin_id" not in session:

        return redirect(
            url_for("auth.login")
        )



    cursor = mysql.connection.cursor()



    cursor.execute("""
        SELECT photo
        FROM teachers
        WHERE id=%s
    """,
    (id,)
    )


    teacher = cursor.fetchone()



    if teacher:


        photo = teacher[0]



        if photo:


            photo_path = os.path.join(
                get_upload_folder(),
                photo
            )



            if os.path.exists(
                photo_path
            ):

                os.remove(
                    photo_path
                )




    cursor.execute("""
        DELETE FROM teachers

        WHERE id=%s

    """,
    (id,)
    )



    mysql.connection.commit()

    cursor.close()



    flash(
        "Teacher deleted successfully!",
        "success"
    )



    return redirect(
        url_for(
            "teachers.index"
        )
    )
@teachers.route("/remove-photo/<int:id>")
def remove_photo(id):

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    cursor = mysql.connection.cursor()

    cursor.execute("""
        UPDATE teachers
        SET photo=NULL
        WHERE id=%s
    """, (id,))

    mysql.connection.commit()

    cursor.close()

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
