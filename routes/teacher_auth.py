from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    current_app
)

import os
import time
from werkzeug.utils import secure_filename

from extensions import mysql


# ============================================================
# TEACHER AUTH BLUEPRINT
# ============================================================

teacher_auth = Blueprint(
    "teacher_auth",
    __name__,
    url_prefix="/teacher"
)


# ============================================================
# HELPER
# Check whether teacher is logged in
# ============================================================

def teacher_logged_in():
    return "teacher_id" in session


# ============================================================
# HELPER
# Get current teacher
# ============================================================

def get_current_teacher():

    if "teacher_id" not in session:
        return None

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                id,
                teacher_id,
                full_name,
                email,
                department,
                password,
                profile_photo
            FROM teachers
            WHERE id = %s
            LIMIT 1
            """,
            (session["teacher_id"],)
        )

        return cursor.fetchone()

    except Exception as e:

        print("Get current teacher error:", e)
        return None

    finally:

        cursor.close()


# ============================================================
# HELPER
# Sync teacher session with database
# ============================================================

def sync_teacher_session():

    if "teacher_id" not in session:
        return None

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                id,
                teacher_id,
                full_name,
                email,
                department,
                profile_photo
            FROM teachers
            WHERE id = %s
            LIMIT 1
            """,
            (session["teacher_id"],)
        )

        teacher = cursor.fetchone()

        if not teacher:
            return None

        session["teacher_id"] = teacher[0]
        session["teacher_code"] = teacher[1]
        session["teacher_name"] = teacher[2]
        session["teacher_email"] = teacher[3]
        session["teacher_department"] = teacher[4]

        if teacher[5]:
            session["teacher_profile_photo"] = teacher[5]
        else:
            session.pop("teacher_profile_photo", None)

        return teacher

    except Exception as e:

        print("Teacher session sync error:", e)
        return None

    finally:

        cursor.close()


# ============================================================
# HELPER
# Get subjects of current teacher
# ============================================================

def get_teacher_subjects():

    if "teacher_id" not in session:
        return []

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                id,
                subject_code,
                subject_name,
                semester,
                department
            FROM subjects
            WHERE teacher_id = %s
            ORDER BY semester ASC, subject_name ASC
            """,
            (session["teacher_id"],)
        )

        return cursor.fetchall() or []

    except Exception as e:

        print("Teacher subjects loading error:", e)
        return []

    finally:

        cursor.close()


# ============================================================
# TEACHER LOGIN
# ============================================================

@teacher_auth.route("/login", methods=["GET", "POST"])
def login():

    # --------------------------------------------------------
    # If teacher is already logged in
    # --------------------------------------------------------

    if "teacher_id" in session:

        teacher = sync_teacher_session()

        if teacher:

            return redirect(
                url_for("teacher_auth.dashboard")
            )

        # Invalid old session
        session.clear()

    # --------------------------------------------------------
    # LOGIN POST
    # --------------------------------------------------------

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()

        # ----------------------------------------------------
        # Validation
        # ----------------------------------------------------

        if not email or not password:

            flash(
                "Please enter email and password.",
                "warning"
            )

            return redirect(
                url_for("teacher_auth.login")
            )

        cursor = mysql.connection.cursor()

        try:

            # ------------------------------------------------
            # Find teacher
            # ------------------------------------------------

            cursor.execute(
                """
                SELECT
                    id,
                    teacher_id,
                    full_name,
                    email,
                    department,
                    password,
                    profile_photo
                FROM teachers
                WHERE email = %s
                LIMIT 1
                """,
                (email,)
            )

            teacher = cursor.fetchone()

        except Exception as e:

            print(
                "Teacher login database error:",
                e
            )

            flash(
                "Unable to login right now.",
                "danger"
            )

            return redirect(
                url_for("teacher_auth.login")
            )

        finally:

            cursor.close()

        # ----------------------------------------------------
        # Teacher not found
        # ----------------------------------------------------

        if teacher is None:

            flash(
                "Invalid email address.",
                "danger"
            )

            return redirect(
                url_for("teacher_auth.login")
            )

        # ----------------------------------------------------
        # Password check
        # ----------------------------------------------------

        if password != teacher[5]:

            flash(
                "Incorrect password.",
                "danger"
            )

            return redirect(
                url_for("teacher_auth.login")
            )

        # ====================================================
        # IMPORTANT
        # Clear previous teacher session completely
        # ====================================================

        session.clear()

        # ====================================================
        # CREATE NEW TEACHER SESSION
        # ====================================================

        session["teacher_id"] = teacher[0]
        session["teacher_code"] = teacher[1]
        session["teacher_name"] = teacher[2]
        session["teacher_email"] = teacher[3]
        session["teacher_department"] = teacher[4]

        # ----------------------------------------------------
        # Profile photo
        # ----------------------------------------------------

        if teacher[6]:

            session["teacher_profile_photo"] = teacher[6]

        # ====================================================
        # IMPORTANT
        # DO NOT SHOW "WELCOME..." MESSAGE
        #
        # This was one of the reasons the old message was
        # appearing on login-related pages.
        # ====================================================

        return redirect(
            url_for("teacher_auth.dashboard")
        )

    # ========================================================
    # LOGIN PAGE
    # ========================================================

    return render_template(
        "teacher/login.html"
    )


# ============================================================
# TEACHER DASHBOARD
# ============================================================

@teacher_auth.route("/dashboard")
def dashboard():

    if not teacher_logged_in():

        return redirect(
            url_for("teacher_auth.login")
        )

    teacher = sync_teacher_session()

    if not teacher:

        session.clear()

        return redirect(
            url_for("teacher_auth.login")
        )

    cursor = mysql.connection.cursor()

    total_subjects = 0
    total_sessions = 0
    today_sessions = 0
    open_sessions = 0

    subject_list = []
    recent_sessions = []

    try:

        # ----------------------------------------------------
        # Total subjects
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM subjects
            WHERE teacher_id = %s
            """,
            (session["teacher_id"],)
        )

        result = cursor.fetchone()

        total_subjects = result[0] if result else 0

        # ----------------------------------------------------
        # Total attendance sessions
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM attendance_sessions
            WHERE teacher_id = %s
            """,
            (session["teacher_id"],)
        )

        result = cursor.fetchone()

        total_sessions = result[0] if result else 0

        # ----------------------------------------------------
        # Today's sessions
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM attendance_sessions
            WHERE teacher_id = %s
            AND session_date = CURDATE()
            """,
            (session["teacher_id"],)
        )

        result = cursor.fetchone()

        today_sessions = result[0] if result else 0

        # ----------------------------------------------------
        # Open sessions
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM attendance_sessions
            WHERE teacher_id = %s
            AND session_status = 'OPEN'
            """,
            (session["teacher_id"],)
        )

        result = cursor.fetchone()

        open_sessions = result[0] if result else 0

        # ----------------------------------------------------
        # Subject list
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                subject_code,
                subject_name,
                semester,
                department
            FROM subjects
            WHERE teacher_id = %s
            ORDER BY semester ASC, subject_name ASC
            """,
            (session["teacher_id"],)
        )

        subject_list = cursor.fetchall() or []

        # ----------------------------------------------------
        # Recent attendance sessions
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                attendance_sessions.id,
                subjects.subject_code,
                subjects.subject_name,
                attendance_sessions.session_date,
                attendance_sessions.start_time,
                attendance_sessions.end_time,
                attendance_sessions.session_status
            FROM attendance_sessions
            INNER JOIN subjects
                ON attendance_sessions.subject_id = subjects.id
            WHERE attendance_sessions.teacher_id = %s
            ORDER BY attendance_sessions.id DESC
            LIMIT 10
            """,
            (session["teacher_id"],)
        )

        recent_sessions = cursor.fetchall() or []

    except Exception as e:

        mysql.connection.rollback()

        print(
            "Dashboard loading error:",
            e
        )

        flash(
            "Dashboard loading error. Please try again.",
            "danger"
        )

    finally:

        cursor.close()

    return render_template(
        "teacher/dashboard.html",
        total_subjects=total_subjects,
        total_sessions=total_sessions,
        today_sessions=today_sessions,
        open_sessions=open_sessions,
        subject_list=subject_list,
        recent_sessions=recent_sessions
    )


# ============================================================
# TEACHER LOGOUT
# ============================================================

@teacher_auth.route("/logout")
def logout():

    # ========================================================
    # IMPORTANT
    #
    # We completely destroy the teacher session.
    #
    # Do NOT use flash("Logged out successfully...")
    # because that message will appear on the login page.
    # ========================================================

    session.clear()

    # --------------------------------------------------------
    # Directly open clean login page
    # --------------------------------------------------------

    return redirect(
        url_for("teacher_auth.login")
    )


# ============================================================
# TEACHER CONTROL PANEL
# ============================================================

@teacher_auth.route("/control-panel")
def control_panel():

    if not teacher_logged_in():

        return redirect(
            url_for("teacher_auth.login")
        )

    teacher = sync_teacher_session()

    if not teacher:

        session.clear()

        return redirect(
            url_for("teacher_auth.login")
        )

    cursor = mysql.connection.cursor()

    subject_list = []
    total_sessions = 0
    open_sessions = 0
    today_sessions = 0

    try:

        # ----------------------------------------------------
        # Current teacher
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                teacher_id,
                full_name,
                email,
                department,
                profile_photo
            FROM teachers
            WHERE id = %s
            LIMIT 1
            """,
            (session["teacher_id"],)
        )

        teacher = cursor.fetchone()

        if teacher is None:

            session.clear()

            return redirect(
                url_for("teacher_auth.login")
            )

        # ----------------------------------------------------
        # Subjects
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                subject_code,
                subject_name,
                semester,
                department
            FROM subjects
            WHERE teacher_id = %s
            ORDER BY semester ASC, subject_name ASC
            """,
            (session["teacher_id"],)
        )

        subject_list = cursor.fetchall() or []

        # ----------------------------------------------------
        # Total sessions
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM attendance_sessions
            WHERE teacher_id = %s
            """,
            (session["teacher_id"],)
        )

        result = cursor.fetchone()

        total_sessions = result[0] if result else 0

        # ----------------------------------------------------
        # Open sessions
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM attendance_sessions
            WHERE teacher_id = %s
            AND session_status = 'OPEN'
            """,
            (session["teacher_id"],)
        )

        result = cursor.fetchone()

        open_sessions = result[0] if result else 0

        # ----------------------------------------------------
        # Today's sessions
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM attendance_sessions
            WHERE teacher_id = %s
            AND session_date = CURDATE()
            """,
            (session["teacher_id"],)
        )

        result = cursor.fetchone()

        today_sessions = result[0] if result else 0

    except Exception as e:

        mysql.connection.rollback()

        print(
            "Control Panel loading error:",
            e
        )

        flash(
            "Control Panel loading error.",
            "danger"
        )

    finally:

        cursor.close()

    return render_template(
        "teacher/control_panel.html",
        teacher=teacher,
        subject_list=subject_list,
        total_sessions=total_sessions,
        open_sessions=open_sessions,
        today_sessions=today_sessions
    )


# ============================================================
# TEACHER PROFILE
# ============================================================

@teacher_auth.route(
    "/profile",
    methods=["GET", "POST"]
)
def profile():

    if not teacher_logged_in():

        return redirect(
            url_for("teacher_auth.login")
        )

    sync_teacher_session()

    allowed_extensions = {
        "jpg",
        "jpeg",
        "png",
        "webp"
    }

    upload_folder = os.path.join(
        current_app.root_path,
        "static",
        "uploads",
        "teachers"
    )

    os.makedirs(
        upload_folder,
        exist_ok=True
    )

    # ========================================================
    # POST
    # ========================================================

    if request.method == "POST":

        action = request.form.get(
            "action",
            "upload"
        ).strip().lower()

        # ====================================================
        # DELETE PHOTO
        # ====================================================

        if action == "delete":

            cursor = mysql.connection.cursor()

            try:

                cursor.execute(
                    """
                    SELECT profile_photo
                    FROM teachers
                    WHERE id = %s
                    LIMIT 1
                    """,
                    (session["teacher_id"],)
                )

                current_teacher = cursor.fetchone()

                old_photo = (
                    current_teacher[0]
                    if current_teacher
                    else None
                )

                cursor.execute(
                    """
                    UPDATE teachers
                    SET profile_photo = NULL
                    WHERE id = %s
                    """,
                    (session["teacher_id"],)
                )

                mysql.connection.commit()

                # Delete physical image
                if old_photo:

                    old_path = os.path.join(
                        upload_folder,
                        old_photo
                    )

                    if os.path.exists(old_path):

                        try:
                            os.remove(old_path)
                        except Exception as e:
                            print(
                                "Profile photo delete error:",
                                e
                            )

                session.pop(
                    "teacher_profile_photo",
                    None
                )

                flash(
                    "Profile photo deleted successfully.",
                    "success"
                )

                return redirect(
                    url_for("teacher_auth.profile")
                )

            except Exception as e:

                mysql.connection.rollback()

                flash(
                    "Profile photo delete error.",
                    "danger"
                )

                print(
                    "Profile photo delete error:",
                    e
                )

                return redirect(
                    url_for("teacher_auth.profile")
                )

            finally:

                cursor.close()

        # ====================================================
        # UPLOAD PHOTO
        # ====================================================

        photo = request.files.get(
            "profile_photo"
        )

        if not photo or photo.filename == "":

            flash(
                "Please select a profile photo.",
                "warning"
            )

            return redirect(
                url_for("teacher_auth.profile")
            )

        original_name = secure_filename(
            photo.filename
        )

        if not original_name:

            flash(
                "Invalid image filename.",
                "danger"
            )

            return redirect(
                url_for("teacher_auth.profile")
            )

        extension = os.path.splitext(
            original_name
        )[1].lower().replace(".", "")

        if extension not in allowed_extensions:

            flash(
                "Only JPG, JPEG, PNG and WEBP images are allowed.",
                "danger"
            )

            return redirect(
                url_for("teacher_auth.profile")
            )

        cursor = mysql.connection.cursor()

        file_path = None
        new_filename = None

        try:

            # ------------------------------------------------
            # Current photo
            # ------------------------------------------------

            cursor.execute(
                """
                SELECT profile_photo
                FROM teachers
                WHERE id = %s
                LIMIT 1
                """,
                (session["teacher_id"],)
            )

            current_teacher = cursor.fetchone()

            old_photo = (
                current_teacher[0]
                if current_teacher
                else None
            )

            # ------------------------------------------------
            # Unique filename
            # ------------------------------------------------

            timestamp = int(time.time())

            new_filename = (
                f"teacher_"
                f"{session['teacher_id']}_"
                f"{timestamp}."
                f"{extension}"
            )

            file_path = os.path.join(
                upload_folder,
                new_filename
            )

            # ------------------------------------------------
            # Save
            # ------------------------------------------------

            photo.save(file_path)

            # ------------------------------------------------
            # Database update
            # ------------------------------------------------

            cursor.execute(
                """
                UPDATE teachers
                SET profile_photo = %s
                WHERE id = %s
                """,
                (
                    new_filename,
                    session["teacher_id"]
                )
            )

            mysql.connection.commit()

            session["teacher_profile_photo"] = new_filename

            # ------------------------------------------------
            # Delete old photo
            # ------------------------------------------------

            if old_photo:

                old_path = os.path.join(
                    upload_folder,
                    old_photo
                )

                if (
                    os.path.exists(old_path)
                    and old_photo != new_filename
                ):

                    try:
                        os.remove(old_path)
                    except Exception as e:
                        print(
                            "Old profile photo delete error:",
                            e
                        )

            flash(
                "Profile photo updated successfully.",
                "success"
            )

            return redirect(
                url_for("teacher_auth.profile")
            )

        except Exception as e:

            mysql.connection.rollback()

            if file_path:

                try:

                    if os.path.exists(file_path):
                        os.remove(file_path)

                except Exception:
                    pass

            print(
                "Profile photo upload error:",
                e
            )

            flash(
                "Profile photo upload error.",
                "danger"
            )

            return redirect(
                url_for("teacher_auth.profile")
            )

        finally:

            cursor.close()

    # ========================================================
    # GET PROFILE
    # ========================================================

    cursor = mysql.connection.cursor()

    teacher = None

    try:

        cursor.execute(
            """
            SELECT
                id,
                teacher_id,
                full_name,
                email,
                department,
                profile_photo
            FROM teachers
            WHERE id = %s
            LIMIT 1
            """,
            (session["teacher_id"],)
        )

        teacher = cursor.fetchone()

    except Exception as e:

        mysql.connection.rollback()

        print(
            "Profile loading error:",
            e
        )

        flash(
            "Profile loading error.",
            "danger"
        )

    finally:

        cursor.close()

    if teacher is None:

        session.clear()

        return redirect(
            url_for("teacher_auth.login")
        )

    # --------------------------------------------------------
    # Sync photo
    # --------------------------------------------------------

    if teacher[5]:

        session["teacher_profile_photo"] = teacher[5]

    else:

        session.pop(
            "teacher_profile_photo",
            None
        )

    return render_template(
        "teacher/profile.html",
        teacher=teacher
    )


# ============================================================
# TEACHER SETTINGS
# ============================================================

@teacher_auth.route(
    "/settings",
    methods=["GET", "POST"]
)
def settings():

    if not teacher_logged_in():

        return redirect(
            url_for("teacher_auth.login")
        )

    sync_teacher_session()

    cursor = mysql.connection.cursor()

    teacher = None

    try:

        # ----------------------------------------------------
        # Current teacher
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                teacher_id,
                full_name,
                email,
                department,
                password,
                profile_photo
            FROM teachers
            WHERE id = %s
            LIMIT 1
            """,
            (session["teacher_id"],)
        )

        teacher = cursor.fetchone()

        if teacher is None:

            session.clear()

            return redirect(
                url_for("teacher_auth.login")
            )

        # ====================================================
        # POST
        # ====================================================

        if request.method == "POST":

            current_email = teacher[3]
            current_password = teacher[5]

            new_email = request.form.get(
                "new_email",
                ""
            ).strip()

            old_password = request.form.get(
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

            # ------------------------------------------------
            # Email
            # ------------------------------------------------

            if not new_email:

                new_email = current_email

            email_changed = (
                new_email.lower()
                != current_email.lower()
            )

            # ------------------------------------------------
            # Password
            # ------------------------------------------------

            password_changed = (
                bool(old_password)
                or bool(new_password)
                or bool(confirm_password)
            )

            # ------------------------------------------------
            # Nothing changed
            # ------------------------------------------------

            if (
                not email_changed
                and not password_changed
            ):

                flash(
                    "No changes were made.",
                    "info"
                )

                return redirect(
                    url_for("teacher_auth.settings")
                )

            # =================================================
            # EMAIL VALIDATION
            # =================================================

            if email_changed:

                if (
                    "@" not in new_email
                    or "." not in new_email
                ):

                    flash(
                        "Please enter a valid email address.",
                        "danger"
                    )

                    return redirect(
                        url_for("teacher_auth.settings")
                    )

                cursor.execute(
                    """
                    SELECT id
                    FROM teachers
                    WHERE email = %s
                    AND id != %s
                    LIMIT 1
                    """,
                    (
                        new_email,
                        session["teacher_id"]
                    )
                )

                if cursor.fetchone():

                    flash(
                        "This email address is already being used by another teacher.",
                        "danger"
                    )

                    return redirect(
                        url_for("teacher_auth.settings")
                    )

            # =================================================
            # PASSWORD VALIDATION
            # =================================================

            if password_changed:

                if not old_password:

                    flash(
                        "Enter your current password to change password.",
                        "danger"
                    )

                    return redirect(
                        url_for("teacher_auth.settings")
                    )

                if old_password != current_password:

                    flash(
                        "Current password is incorrect.",
                        "danger"
                    )

                    return redirect(
                        url_for("teacher_auth.settings")
                    )

                if not new_password:

                    flash(
                        "Enter a new password.",
                        "danger"
                    )

                    return redirect(
                        url_for("teacher_auth.settings")
                    )

                if len(new_password) < 6:

                    flash(
                        "New password must be at least 6 characters.",
                        "warning"
                    )

                    return redirect(
                        url_for("teacher_auth.settings")
                    )

                if new_password != confirm_password:

                    flash(
                        "New password and confirm password do not match.",
                        "danger"
                    )

                    return redirect(
                        url_for("teacher_auth.settings")
                    )

            # =================================================
            # UPDATE DATABASE
            # =================================================

            if email_changed and not password_changed:

                cursor.execute(
                    """
                    UPDATE teachers
                    SET email = %s
                    WHERE id = %s
                    """,
                    (
                        new_email,
                        session["teacher_id"]
                    )
                )

            elif password_changed and not email_changed:

                cursor.execute(
                    """
                    UPDATE teachers
                    SET password = %s
                    WHERE id = %s
                    """,
                    (
                        new_password,
                        session["teacher_id"]
                    )
                )

            else:

                cursor.execute(
                    """
                    UPDATE teachers
                    SET
                        email = %s,
                        password = %s
                    WHERE id = %s
                    """,
                    (
                        new_email,
                        new_password,
                        session["teacher_id"]
                    )
                )

            mysql.connection.commit()

            # ------------------------------------------------
            # Update session
            # ------------------------------------------------

            session["teacher_email"] = new_email

            flash(
                "Settings updated successfully.",
                "success"
            )

            return redirect(
                url_for("teacher_auth.settings")
            )

    except Exception as e:

        mysql.connection.rollback()

        print(
            "Settings error:",
            e
        )

        flash(
            "Settings update error.",
            "danger"
        )

    finally:

        cursor.close()

    return render_template(
        "teacher/settings.html",
        teacher=teacher
    )