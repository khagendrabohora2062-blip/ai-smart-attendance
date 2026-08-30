# ============================================================
# STUDENT NOTICE
# File: routes/student_notice.py
# ============================================================

import os

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    session,
    current_app,
    send_file
)


student_notice = Blueprint(
    "student_notice",
    __name__,
    url_prefix="/student/notices"
)


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

        print(
            "STUDENT NOTICE MYSQL ERROR:",
            repr(e)
        )

    raise RuntimeError(
        "MySQL connection is not initialized."
    )


# ============================================================
# STUDENT LOGIN
# ============================================================

def student_required():

    return bool(
        session.get("student_id")
    )


# ============================================================
# NOTICE LIST
# ============================================================

@student_notice.route("/")
def index():

    if not student_required():

        flash(
            "Please login as student.",
            "warning"
        )

        return redirect(
            "/student/login"
        )

    mysql = get_mysql()
    cursor = mysql.connection.cursor()

    try:

        logged_student = session.get(
            "student_id"
        )

        # ----------------------------------------------------
        # STUDENT INFO
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                department,
                semester
            FROM students
            WHERE id = %s
               OR student_id = %s
            LIMIT 1
            """,
            (
                logged_student,
                logged_student
            )
        )

        student = cursor.fetchone()

        if not student:

            flash(
                "Student account was not found.",
                "danger"
            )

            return redirect(
                "/student/dashboard"
            )

        department = student[0]
        semester = student[1]

        # ----------------------------------------------------
        # NOTICE QUERY
        #
        # Everyone  -> visible
        # Students  -> visible
        # Teachers   -> hidden
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
                created_at
            FROM notices
            WHERE is_published = 1

              AND (
                    audience IS NULL
                    OR LOWER(TRIM(audience))
                       IN ('everyone', 'students')
                  )

              AND
              (
                    target_semester IS NULL
                    OR TRIM(target_semester) = ''
                    OR LOWER(TRIM(target_semester))
                       =
                       LOWER(TRIM(%s))
              )

              AND
              (
                    target_department IS NULL
                    OR TRIM(target_department) = ''
                    OR LOWER(TRIM(target_department))
                       =
                       LOWER(TRIM(%s))
              )

            ORDER BY created_at DESC
            """,
            (
                semester,
                department
            )
        )

        notices = cursor.fetchall() or []

        return render_template(
            "student/notices.html",
            notices=notices
        )

    except Exception as e:

        print(
            "STUDENT NOTICE ERROR:",
            repr(e)
        )

        flash(
            f"Unable to load notices: {str(e)}",
            "danger"
        )

        return redirect(
            "/student/dashboard"
        )

    finally:
        cursor.close()


# ============================================================
# SINGLE NOTICE
# ============================================================

@student_notice.route(
    "/view/<int:notice_id>"
)
def view(notice_id):

    if not student_required():

        return redirect(
            "/student/login"
        )

    mysql = get_mysql()
    cursor = mysql.connection.cursor()

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
                created_at
            FROM notices
            WHERE id = %s
              AND is_published = 1
              AND (
                    audience IS NULL
                    OR LOWER(TRIM(audience))
                       IN ('everyone', 'students')
                  )
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
                url_for("student_notice.index")
            )

        return render_template(
            "student/notice_view.html",
            notice=notice
        )

    finally:
        cursor.close()


# ============================================================
# DOWNLOAD NOTICE PHOTO
# ============================================================

@student_notice.route(
    "/download/image/<int:notice_id>"
)
def download_image(notice_id):

    if not student_required():

        return redirect(
            "/student/login"
        )

    mysql = get_mysql()
    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                id,
                title,
                image
            FROM notices
            WHERE id = %s
              AND is_published = 1
              AND (
                    audience IS NULL
                    OR LOWER(TRIM(audience))
                       IN ('everyone', 'students')
                  )
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
                url_for("student_notice.index")
            )

        image_name = notice[2]

        if not image_name:

            flash(
                "This notice does not have a photo.",
                "warning"
            )

            return redirect(
                url_for(
                    "student_notice.view",
                    notice_id=notice_id
                )
            )

        image_folder = os.path.join(
            current_app.root_path,
            "static",
            "uploads",
            "notices"
        )

        image_path = os.path.join(
            image_folder,
            os.path.basename(image_name)
        )

        if not os.path.isfile(image_path):

            flash(
                "Notice photo file was not found.",
                "danger"
            )

            return redirect(
                url_for(
                    "student_notice.view",
                    notice_id=notice_id
                )
            )

        extension = os.path.splitext(
            image_name
        )[1].lower()

        download_name = (
            "Notice_"
            + str(notice_id)
            + extension
        )

        return send_file(
            image_path,
            as_attachment=True,
            download_name=download_name
        )

    finally:
        cursor.close()


# ============================================================
# DOWNLOAD NOTICE PDF
# ============================================================

@student_notice.route(
    "/download/pdf/<int:notice_id>"
)
def download_pdf(notice_id):

    if not student_required():

        return redirect(
            "/student/login"
        )

    mysql = get_mysql()
    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                id,
                title,
                pdf_file
            FROM notices
            WHERE id = %s
              AND is_published = 1
              AND (
                    audience IS NULL
                    OR LOWER(TRIM(audience))
                       IN ('everyone', 'students')
                  )
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
                url_for("student_notice.index")
            )

        pdf_name = notice[2]

        if not pdf_name:

            flash(
                "This notice does not have a PDF.",
                "warning"
            )

            return redirect(
                url_for(
                    "student_notice.view",
                    notice_id=notice_id
                )
            )

        pdf_folder = os.path.join(
            current_app.root_path,
            "static",
            "uploads",
            "notices",
            "pdf"
        )

        pdf_path = os.path.join(
            pdf_folder,
            os.path.basename(pdf_name)
        )

        if not os.path.isfile(pdf_path):

            flash(
                "Notice PDF file was not found.",
                "danger"
            )

            return redirect(
                url_for(
                    "student_notice.view",
                    notice_id=notice_id
                )
            )

        download_name = (
            "Notice_"
            + str(notice_id)
            + ".pdf"
        )

        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=download_name
        )

    finally:
        cursor.close()