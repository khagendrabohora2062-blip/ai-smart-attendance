from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session
)

from extensions import mysql


# ============================================================
# ADMIN AUTH BLUEPRINT
# ============================================================

auth = Blueprint(
    "auth",
    __name__
)


# ============================================================
# ADMIN LOGIN
# ============================================================

@auth.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    # --------------------------------------------------------
    # Already logged in
    # --------------------------------------------------------

    if "admin_id" in session:
        return redirect(
            url_for(
                "admin.dashboard"
            )
        )

    # --------------------------------------------------------
    # POST LOGIN
    # --------------------------------------------------------

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()

        # ----------------------------------------------------
        # Validation
        # ----------------------------------------------------

        if not username or not password:

            flash(
                "Please enter username and password.",
                "warning"
            )

            return redirect(
                url_for(
                    "auth.login"
                )
            )

        cursor = mysql.connection.cursor()

        admin = None

        try:

            # =================================================
            # GET ADMIN
            # =================================================

            cursor.execute(
                """
                SELECT
                    id,
                    full_name,
                    username,
                    profile_photo
                FROM admins
                WHERE username = %s
                AND password = %s
                LIMIT 1
                """,
                (
                    username,
                    password
                )
            )

            admin = cursor.fetchone()

        except Exception as e:

            mysql.connection.rollback()

            flash(
                f"Login error: {e}",
                "danger"
            )

            return redirect(
                url_for(
                    "auth.login"
                )
            )

        finally:
            cursor.close()

        # ----------------------------------------------------
        # Invalid Login
        # ----------------------------------------------------

        if admin is None:

            flash(
                "Invalid Username or Password",
                "danger"
            )

            return redirect(
                url_for(
                    "auth.login"
                )
            )

        # ====================================================
        # REMOVE OTHER ROLE SESSIONS
        # ====================================================

        session.pop(
            "teacher_id",
            None
        )

        session.pop(
            "student_db_id",
            None
        )

        session.pop(
            "student_id",
            None
        )

        session.pop(
            "student_name",
            None
        )

        session.pop(
            "student_email",
            None
        )

        session.pop(
            "student_department",
            None
        )

        session.pop(
            "student_semester",
            None
        )

        session.pop(
            "student_section",
            None
        )

        session.pop(
            "student_photo",
            None
        )

        # ====================================================
        # CREATE ADMIN SESSION
        # ====================================================

        session["admin_id"] = admin[0]

        session["admin_name"] = admin[1]

        session["admin_username"] = admin[2]

        session["admin_profile_photo"] = admin[3]

        session.permanent = True

        # ====================================================
        # LOGIN SUCCESS
        # ====================================================

        # IMPORTANT:
        # No flash message here.
        #
        # So:
        # "Welcome, Administrator!"
        # will NOT appear after login.

        return redirect(
            url_for(
                "admin.dashboard"
            )
        )

    # ========================================================
    # LOGIN PAGE
    # ========================================================

    return render_template(
        "auth/login.html"
    )


# ============================================================
# ADMIN CHANGE PASSWORD
# ============================================================

@auth.route(
    "/change-password",
    methods=["GET", "POST"]
)
def change_password():

    # --------------------------------------------------------
    # ADMIN LOGIN CHECK
    # --------------------------------------------------------

    if "admin_id" not in session:

        flash(
            "Please login first.",
            "warning"
        )

        return redirect(
            url_for(
                "auth.login"
            )
        )

    # --------------------------------------------------------
    # POST CHANGE PASSWORD
    # --------------------------------------------------------

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

        # ====================================================
        # VALIDATION
        # ====================================================

        if (
            not current_password
            or not new_password
            or not confirm_password
        ):

            flash(
                "Please fill in all password fields.",
                "warning"
            )

            return redirect(
                url_for(
                    "auth.change_password"
                )
            )

        # ----------------------------------------------------
        # New Password Match
        # ----------------------------------------------------

        if new_password != confirm_password:

            flash(
                "New password and confirm password do not match.",
                "danger"
            )

            return redirect(
                url_for(
                    "auth.change_password"
                )
            )

        # ----------------------------------------------------
        # Minimum Password Length
        # ----------------------------------------------------

        if len(new_password) < 6:

            flash(
                "New password must be at least 6 characters.",
                "warning"
            )

            return redirect(
                url_for(
                    "auth.change_password"
                )
            )

        # ----------------------------------------------------
        # Prevent Same Password
        # ----------------------------------------------------

        if current_password == new_password:

            flash(
                "New password must be different from current password.",
                "warning"
            )

            return redirect(
                url_for(
                    "auth.change_password"
                )
            )

        cursor = mysql.connection.cursor()

        try:

            # =================================================
            # VERIFY CURRENT PASSWORD
            # =================================================

            cursor.execute(
                """
                SELECT
                    id
                FROM admins
                WHERE id = %s
                AND password = %s
                LIMIT 1
                """,
                (
                    session["admin_id"],
                    current_password
                )
            )

            admin = cursor.fetchone()

            if not admin:

                flash(
                    "Current password is incorrect.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "auth.change_password"
                    )
                )

            # =================================================
            # UPDATE PASSWORD
            # =================================================

            cursor.execute(
                """
                UPDATE admins
                SET password = %s
                WHERE id = %s
                """,
                (
                    new_password,
                    session["admin_id"]
                )
            )

            mysql.connection.commit()

            # =================================================
            # SUCCESS
            # =================================================

            flash(
                "Password changed successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "admin.dashboard"
                )
            )

        except Exception as e:

            mysql.connection.rollback()

            flash(
                f"Password change error: {e}",
                "danger"
            )

        finally:
            cursor.close()

    # ========================================================
    # CHANGE PASSWORD PAGE
    # ========================================================

    return render_template(
        "auth/change_password.html"
    )


# ============================================================
# ADMIN LOGOUT
# ============================================================

@auth.route(
    "/logout"
)
def logout():

    # --------------------------------------------------------
    # Clear Admin Session
    # --------------------------------------------------------

    session.pop(
        "admin_id",
        None
    )

    session.pop(
        "admin_name",
        None
    )

    session.pop(
        "admin_username",
        None
    )

    session.pop(
        "admin_profile_photo",
        None
    )

    # --------------------------------------------------------
    # IMPORTANT
    # --------------------------------------------------------
    # No flash() here.
    #
    # Therefore after logout:
    #
    # "Logged out successfully."
    #
    # will NOT appear on login page.
    # --------------------------------------------------------

    return redirect(
        url_for(
            "auth.login"
        )
    )