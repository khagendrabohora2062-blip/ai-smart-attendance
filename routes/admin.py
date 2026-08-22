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
import time

from werkzeug.utils import secure_filename


# ==========================================================
# ADMIN BLUEPRINT
# ==========================================================

admin = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
)


# ==========================================================
# HELPER
# ADMIN LOGIN CHECK
# ==========================================================

def admin_logged_in():

    return "admin_id" in session


# ==========================================================
# HELPER
# SYNC ADMIN SESSION
#
# Database बाट latest admin information ल्याएर
# Flask session मा राख्छ।
#
# यसले profile photo navbar/sidebar/profile
# सबै ठाउँमा एउटै photo देखाउन मद्दत गर्छ।
# ==========================================================

def sync_admin_session():

    if "admin_id" not in session:

        return None


    cursor = mysql.connection.cursor()


    try:

        cursor.execute(
            """
            SELECT
                id,
                full_name,
                username,
                email,
                phone,
                photo
            FROM admins
            WHERE id=%s
            LIMIT 1
            """,
            (
                session["admin_id"],
            )
        )


        admin_data = cursor.fetchone()


        if admin_data:

            session["admin_id"] = admin_data[0]

            session["admin_name"] = admin_data[1]

            session["admin_username"] = admin_data[2]

            session["admin_email"] = admin_data[3]

            session["admin_phone"] = admin_data[4]

            # ------------------------------------------
            # IMPORTANT
            # Admin profile photo
            # ------------------------------------------

            if admin_data[5]:

                session["admin_photo"] = admin_data[5]

            else:

                session.pop(
                    "admin_photo",
                    None
                )


        return admin_data


    except Exception as e:

        print(
            "Admin session sync error:",
            e
        )

        return None


    finally:

        cursor.close()


# ==========================================================
# HELPER
# ADMIN UPLOAD FOLDER
# ==========================================================

def get_admin_upload_folder():

    upload_folder = os.path.join(
        current_app.root_path,
        "static",
        "uploads",
        "admins"
    )


    os.makedirs(
        upload_folder,
        exist_ok=True
    )


    return upload_folder


# ==========================================================
# ADMIN DASHBOARD
# ==========================================================

@admin.route("/dashboard")
def dashboard():

    # ------------------------------------------------------
    # LOGIN CHECK
    # ------------------------------------------------------

    if not admin_logged_in():

        return redirect(
            url_for("auth.login")
        )


    # ------------------------------------------------------
    # SYNC ADMIN SESSION
    # ------------------------------------------------------

    sync_admin_session()


    cursor = mysql.connection.cursor()


    try:

        # --------------------------------------------------
        # Total Students
        # --------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM students
            """
        )

        total_students = (
            cursor.fetchone()[0] or 0
        )


        # --------------------------------------------------
        # Total Teachers
        # --------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM teachers
            """
        )

        total_teachers = (
            cursor.fetchone()[0] or 0
        )


        # --------------------------------------------------
        # Total Subjects
        # --------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM subjects
            """
        )

        total_subjects = (
            cursor.fetchone()[0] or 0
        )


        # --------------------------------------------------
        # Today's Attendance
        # --------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM attendance
            WHERE attendance_date=CURDATE()
            """
        )

        today_attendance = (
            cursor.fetchone()[0] or 0
        )


        # --------------------------------------------------
        # Total Feedback
        # --------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM feedback
            """
        )

        total_feedback = (
            cursor.fetchone()[0] or 0
        )


        # --------------------------------------------------
        # Total Contact Messages
        # --------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM contact_messages
            """
        )

        total_messages = (
            cursor.fetchone()[0] or 0
        )


        # --------------------------------------------------
        # Attendance Percentage
        # --------------------------------------------------

        if total_students > 0:

            attendance_percentage = round(
                (
                    today_attendance
                    / total_students
                ) * 100,
                2
            )

        else:

            attendance_percentage = 0


        # --------------------------------------------------
        # Recent Attendance
        # --------------------------------------------------

        cursor.execute(
            """
            SELECT
                students.student_id,
                students.full_name,
                attendance.attendance_time,
                attendance.attendance_method,
                attendance.status

            FROM attendance

            INNER JOIN students
                ON attendance.student_id = students.id

            WHERE attendance.attendance_date=CURDATE()

            ORDER BY attendance.id DESC

            LIMIT 10
            """
        )

        recent_attendance = cursor.fetchall()


        # --------------------------------------------------
        # Attendance Chart
        # --------------------------------------------------

        cursor.execute(
            """
            SELECT
                status,
                COUNT(*)

            FROM attendance

            WHERE attendance_date=CURDATE()

            GROUP BY status
            """
        )

        status_data = cursor.fetchall()


        present = 0
        absent = 0
        late = 0


        for row in status_data:

            if row[0] == "Present":

                present = row[1]


            elif row[0] == "Absent":

                absent = row[1]


            elif row[0] == "Late":

                late = row[1]


        # --------------------------------------------------
        # Latest Feedback
        # --------------------------------------------------

        cursor.execute(
            """
            SELECT
                name,
                rating,
                message,
                created_at

            FROM feedback

            ORDER BY id DESC

            LIMIT 5
            """
        )

        latest_feedback = cursor.fetchall()


        # --------------------------------------------------
        # Latest Contact Messages
        # --------------------------------------------------

        cursor.execute(
            """
            SELECT
                name,
                email,
                subject,
                message

            FROM contact_messages

            ORDER BY id DESC

            LIMIT 5
            """
        )

        latest_messages = cursor.fetchall()


    except Exception as e:

        mysql.connection.rollback()

        flash(
            f"Dashboard loading error: {e}",
            "danger"
        )


        total_students = 0
        total_teachers = 0
        total_subjects = 0
        today_attendance = 0
        total_feedback = 0
        total_messages = 0
        attendance_percentage = 0
        recent_attendance = []
        present = 0
        absent = 0
        late = 0
        latest_feedback = []
        latest_messages = []


    finally:

        cursor.close()


    return render_template(
        "admin/dashboard.html",

        total_students=total_students,

        total_teachers=total_teachers,

        total_subjects=total_subjects,

        today_attendance=today_attendance,

        total_feedback=total_feedback,

        total_messages=total_messages,

        attendance_percentage=attendance_percentage,

        recent_attendance=recent_attendance,

        present=present,

        absent=absent,

        late=late,

        latest_feedback=latest_feedback,

        latest_messages=latest_messages
    )


# ==========================================================
# ADMIN PROFILE
# ==========================================================

@admin.route(
    "/profile",
    methods=["GET", "POST"]
)
def profile():

    # ------------------------------------------------------
    # LOGIN CHECK
    # ------------------------------------------------------

    if not admin_logged_in():

        return redirect(
            url_for("auth.login")
        )


    # ------------------------------------------------------
    # SYNC SESSION
    # ------------------------------------------------------

    sync_admin_session()


    cursor = mysql.connection.cursor()


    try:

        # ==================================================
        # UPDATE ADMIN INFORMATION
        # ==================================================

        if request.method == "POST":

            full_name = request.form.get(
                "full_name",
                ""
            ).strip()


            username = request.form.get(
                "username",
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


            password = request.form.get(
                "password",
                ""
            ).strip()


            confirm_password = request.form.get(
                "confirm_password",
                ""
            ).strip()


            # ------------------------------------------------
            # Basic Validation
            # ------------------------------------------------

            if (
                not full_name
                or not username
                or not email
            ):

                flash(
                    "Full name, username and email are required.",
                    "danger"
                )

                return redirect(
                    url_for("admin.profile")
                )


            # ------------------------------------------------
            # Username Duplicate Check
            # ------------------------------------------------

            cursor.execute(
                """
                SELECT id
                FROM admins
                WHERE username=%s
                AND id!=%s
                LIMIT 1
                """,
                (
                    username,
                    session["admin_id"]
                )
            )


            if cursor.fetchone():

                flash(
                    "Username already exists.",
                    "danger"
                )

                return redirect(
                    url_for("admin.profile")
                )


            # ------------------------------------------------
            # Email Duplicate Check
            # ------------------------------------------------

            cursor.execute(
                """
                SELECT id
                FROM admins
                WHERE email=%s
                AND id!=%s
                LIMIT 1
                """,
                (
                    email,
                    session["admin_id"]
                )
            )


            if cursor.fetchone():

                flash(
                    "Email already exists.",
                    "danger"
                )

                return redirect(
                    url_for("admin.profile")
                )


            # ------------------------------------------------
            # Password Update
            # ------------------------------------------------

            if password:

                if password != confirm_password:

                    flash(
                        "Passwords do not match.",
                        "danger"
                    )

                    return redirect(
                        url_for("admin.profile")
                    )


                cursor.execute(
                    """
                    UPDATE admins

                    SET
                        full_name=%s,
                        username=%s,
                        email=%s,
                        phone=%s,
                        password=%s

                    WHERE id=%s
                    """,
                    (
                        full_name,
                        username,
                        email,
                        phone,
                        password,
                        session["admin_id"]
                    )
                )


            else:

                cursor.execute(
                    """
                    UPDATE admins

                    SET
                        full_name=%s,
                        username=%s,
                        email=%s,
                        phone=%s

                    WHERE id=%s
                    """,
                    (
                        full_name,
                        username,
                        email,
                        phone,
                        session["admin_id"]
                    )
                )


            mysql.connection.commit()


            # ------------------------------------------------
            # Update Session
            # ------------------------------------------------

            session["admin_name"] = full_name

            session["admin_username"] = username

            session["admin_email"] = email

            session["admin_phone"] = phone


            flash(
                "Profile updated successfully.",
                "success"
            )


            return redirect(
                url_for("admin.profile")
            )


        # ==================================================
        # LOAD ADMIN PROFILE
        # ==================================================

        cursor.execute(
            """
            SELECT
                id,
                full_name,
                username,
                email,
                phone,
                photo,
                created_at

            FROM admins

            WHERE id=%s

            LIMIT 1
            """,
            (
                session["admin_id"],
            )
        )


        admin_data = cursor.fetchone()


    except Exception as e:

        mysql.connection.rollback()

        admin_data = None

        flash(
            f"Profile loading error: {e}",
            "danger"
        )


    finally:

        cursor.close()


    # ------------------------------------------------------
    # Admin Not Found
    # ------------------------------------------------------

    if not admin_data:

        session.clear()

        flash(
            "Admin account not found.",
            "danger"
        )

        return redirect(
            url_for("auth.login")
        )


    # ------------------------------------------------------
    # IMPORTANT
    # Sync photo after loading profile
    # ------------------------------------------------------

    if admin_data[5]:

        session["admin_photo"] = admin_data[5]

    else:

        session.pop(
            "admin_photo",
            None
        )


    return render_template(
        "admin/profile.html",
        admin=admin_data
    )


# ==========================================================
# UPLOAD ADMIN PROFILE PHOTO
# ==========================================================

@admin.route(
    "/upload-photo",
    methods=["POST"]
)
def upload_photo():

    # ------------------------------------------------------
    # LOGIN CHECK
    # ------------------------------------------------------

    if not admin_logged_in():

        return redirect(
            url_for("auth.login")
        )


    # ------------------------------------------------------
    # File Check
    # ------------------------------------------------------

    if "photo" not in request.files:

        flash(
            "No photo selected.",
            "danger"
        )

        return redirect(
            url_for("admin.profile")
        )


    file = request.files["photo"]


    if not file or file.filename == "":

        flash(
            "Please select an image.",
            "warning"
        )

        return redirect(
            url_for("admin.profile")
        )


    # ======================================================
    # ALLOWED EXTENSIONS
    # ======================================================

    allowed_extensions = {
        "jpg",
        "jpeg",
        "png",
        "gif",
        "webp"
    }


    original_filename = secure_filename(
        file.filename
    )


    if "." not in original_filename:

        flash(
            "Invalid image file.",
            "danger"
        )

        return redirect(
            url_for("admin.profile")
        )


    extension = (
        original_filename
        .rsplit(".", 1)[1]
        .lower()
    )


    if extension not in allowed_extensions:

        flash(
            "Only JPG, JPEG, PNG, GIF and WEBP images are allowed.",
            "danger"
        )

        return redirect(
            url_for("admin.profile")
        )


    # ======================================================
    # UPLOAD FOLDER
    # ======================================================

    upload_folder = get_admin_upload_folder()


    # ======================================================
    # GET OLD PHOTO
    # ======================================================

    cursor = mysql.connection.cursor()

    old_photo = None

    upload_path = None


    try:

        cursor.execute(
            """
            SELECT photo
            FROM admins
            WHERE id=%s
            LIMIT 1
            """,
            (
                session["admin_id"],
            )
        )


        admin_data = cursor.fetchone()


        if admin_data:

            old_photo = admin_data[0]


        # ==================================================
        # UNIQUE FILE NAME
        # ==================================================

        timestamp = int(
            time.time()
        )


        filename = (
            f"admin_"
            f"{session['admin_id']}_"
            f"{timestamp}."
            f"{extension}"
        )


        upload_path = os.path.join(
            upload_folder,
            filename
        )


        # ==================================================
        # SAVE NEW PHOTO
        # ==================================================

        file.save(
            upload_path
        )


        # ==================================================
        # UPDATE DATABASE
        # ==================================================

        cursor.execute(
            """
            UPDATE admins

            SET photo=%s

            WHERE id=%s
            """,
            (
                filename,
                session["admin_id"]
            )
        )


        mysql.connection.commit()


        # ==================================================
        # UPDATE SESSION
        #
        # This is the important part.
        # Navbar + Sidebar + Profile immediately
        # use the new photo.
        # ==================================================

        session["admin_photo"] = filename


        # ==================================================
        # DELETE OLD PHOTO
        # ==================================================

        if old_photo:

            old_path = os.path.join(
                upload_folder,
                old_photo
            )


            if (
                os.path.exists(old_path)
                and old_photo != filename
            ):

                try:

                    os.remove(old_path)

                except Exception as delete_error:

                    print(
                        "Old admin photo delete error:",
                        delete_error
                    )


        flash(
            "Profile photo updated successfully.",
            "success"
        )


        return redirect(
            url_for("admin.profile")
        )


    except Exception as e:

        mysql.connection.rollback()


        # --------------------------------------------------
        # Delete newly uploaded file if DB update failed
        # --------------------------------------------------

        if upload_path:

            try:

                if os.path.exists(upload_path):

                    os.remove(upload_path)

            except Exception:

                pass


        flash(
            f"Profile photo upload error: {e}",
            "danger"
        )


        return redirect(
            url_for("admin.profile")
        )


    finally:

        cursor.close()


# ==========================================================
# DELETE ADMIN PROFILE PHOTO
# ==========================================================

@admin.route(
    "/delete-photo",
    methods=["POST"]
)
def delete_photo():

    # ------------------------------------------------------
    # LOGIN CHECK
    # ------------------------------------------------------

    if not admin_logged_in():

        return redirect(
            url_for("auth.login")
        )


    cursor = mysql.connection.cursor()


    try:

        # --------------------------------------------------
        # Get Current Photo
        # --------------------------------------------------

        cursor.execute(
            """
            SELECT photo
            FROM admins
            WHERE id=%s
            LIMIT 1
            """,
            (
                session["admin_id"],
            )
        )


        admin_data = cursor.fetchone()


        old_photo = None


        if admin_data:

            old_photo = admin_data[0]


        # --------------------------------------------------
        # Remove Photo From Database
        # --------------------------------------------------

        cursor.execute(
            """
            UPDATE admins

            SET photo=NULL

            WHERE id=%s
            """,
            (
                session["admin_id"],
            )
        )


        mysql.connection.commit()


        # --------------------------------------------------
        # Remove Photo From Session
        # --------------------------------------------------

        session.pop(
            "admin_photo",
            None
        )


        # --------------------------------------------------
        # Delete Physical File
        # --------------------------------------------------

        if old_photo:

            upload_folder = get_admin_upload_folder()


            old_path = os.path.join(
                upload_folder,
                old_photo
            )


            if os.path.exists(old_path):

                try:

                    os.remove(old_path)

                except Exception as delete_error:

                    print(
                        "Admin photo delete error:",
                        delete_error
                    )


        flash(
            "Profile photo deleted successfully.",
            "success"
        )


    except Exception as e:

        mysql.connection.rollback()

        flash(
            f"Profile photo delete error: {e}",
            "danger"
        )


    finally:

        cursor.close()


    return redirect(
        url_for("admin.profile")
    )


# ==========================================================
# CHANGE PASSWORD
# ==========================================================

@admin.route(
    "/change-password",
    methods=["GET", "POST"]
)
def change_password():

    # ------------------------------------------------------
    # LOGIN CHECK
    # ------------------------------------------------------

    if not admin_logged_in():

        return redirect(
            url_for("auth.login")
        )


    # ------------------------------------------------------
    # Sync Session
    # ------------------------------------------------------

    sync_admin_session()


    if request.method == "POST":

        current_password = request.form.get(
            "current_password",
            ""
        ).strip()


        new_password = request.form.get(
            "new_password",
            ""
        ).strip()


        confirm_password = request.form.get(
            "confirm_password",
            ""
        ).strip()


        cursor = mysql.connection.cursor()


        try:

            cursor.execute(
                """
                SELECT password

                FROM admins

                WHERE id=%s

                LIMIT 1
                """,
                (
                    session["admin_id"],
                )
            )


            admin_data = cursor.fetchone()


            if not admin_data:

                flash(
                    "Admin account not found.",
                    "danger"
                )

                return redirect(
                    url_for("auth.login")
                )


            if admin_data[0] != current_password:

                flash(
                    "Current password is incorrect.",
                    "danger"
                )

                return redirect(
                    url_for("admin.change_password")
                )


            if not new_password:

                flash(
                    "New password is required.",
                    "warning"
                )

                return redirect(
                    url_for("admin.change_password")
                )


            if len(new_password) < 6:

                flash(
                    "New password must be at least 6 characters.",
                    "warning"
                )

                return redirect(
                    url_for("admin.change_password")
                )


            if new_password != confirm_password:

                flash(
                    "New password and confirm password do not match.",
                    "danger"
                )

                return redirect(
                    url_for("admin.change_password")
                )


            cursor.execute(
                """
                UPDATE admins

                SET password=%s

                WHERE id=%s
                """,
                (
                    new_password,
                    session["admin_id"]
                )
            )


            mysql.connection.commit()


            flash(
                "Password changed successfully.",
                "success"
            )


            return redirect(
                url_for("admin.profile")
            )


        except Exception as e:

            mysql.connection.rollback()

            flash(
                f"Password change error: {e}",
                "danger"
            )


        finally:

            cursor.close()


    return render_template(
        "admin/change_password.html"
    )


# ==========================================================
# FEEDBACK MANAGEMENT
# ==========================================================

@admin.route("/feedback")
def feedback():

    if not admin_logged_in():

        return redirect(
            url_for("auth.login")
        )


    sync_admin_session()


    cursor = mysql.connection.cursor()


    try:

        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                rating,
                message,
                created_at

            FROM feedback

            ORDER BY id DESC
            """
        )


        feedbacks = cursor.fetchall()


    finally:

        cursor.close()


    return render_template(
        "admin/feedback.html",
        feedbacks=feedbacks
    )


# ==========================================================
# DELETE FEEDBACK
# ==========================================================

@admin.route(
    "/feedback/delete/<int:id>"
)
def delete_feedback(id):

    if not admin_logged_in():

        return redirect(
            url_for("auth.login")
        )


    sync_admin_session()


    cursor = mysql.connection.cursor()


    try:

        cursor.execute(
            """
            DELETE FROM feedback

            WHERE id=%s
            """,
            (
                id,
            )
        )


        mysql.connection.commit()


        flash(
            "Feedback deleted successfully.",
            "success"
        )


    except Exception as e:

        mysql.connection.rollback()

        flash(
            f"Feedback delete error: {e}",
            "danger"
        )


    finally:

        cursor.close()


    return redirect(
        url_for("admin.feedback")
    )


# ==========================================================
# CONTACT MESSAGES
# ==========================================================

@admin.route("/contact-messages")
def contact_messages():

    if not admin_logged_in():

        return redirect(
            url_for("auth.login")
        )


    sync_admin_session()


    cursor = mysql.connection.cursor()


    try:

        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                subject,
                message

            FROM contact_messages

            ORDER BY id DESC
            """
        )


        messages = cursor.fetchall()


    finally:

        cursor.close()


    return render_template(
        "admin/contact_messages.html",
        messages=messages
    )


# ==========================================================
# DELETE CONTACT MESSAGE
# ==========================================================

@admin.route(
    "/contact-messages/delete/<int:id>"
)
def delete_contact_message(id):

    if not admin_logged_in():

        return redirect(
            url_for("auth.login")
        )


    sync_admin_session()


    cursor = mysql.connection.cursor()


    try:

        cursor.execute(
            """
            DELETE FROM contact_messages

            WHERE id=%s
            """,
            (
                id,
            )
        )


        mysql.connection.commit()


        flash(
            "Message deleted successfully.",
            "success"
        )


    except Exception as e:

        mysql.connection.rollback()

        flash(
            f"Message delete error: {e}",
            "danger"
        )


    finally:

        cursor.close()


    return redirect(
        url_for("admin.contact_messages")
    )