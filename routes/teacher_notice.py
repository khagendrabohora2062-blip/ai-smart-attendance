# ============================================================
# TEACHER NOTICE
# File: routes/teacher_notice.py
# ============================================================

import os

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    session,
    current_app,
    send_file
)

from extensions import mysql


teacher_notice = Blueprint(
    "teacher_notice",
    __name__,
    url_prefix="/teacher/notices"
)


# ============================================================
# LOGIN
# ============================================================

def teacher_logged_in():
    return "teacher_id" in session


# ============================================================
# FOLDERS
# ============================================================

def get_notice_image_folder():

    folder = os.path.join(
        current_app.root_path,
        "static",
        "uploads",
        "notices"
    )

    os.makedirs(folder, exist_ok=True)

    return folder


def get_notice_pdf_folder():

    folder = os.path.join(
        current_app.root_path,
        "static",
        "uploads",
        "notices",
        "pdf"
    )

    os.makedirs(folder, exist_ok=True)

    return folder


# ============================================================
# TEACHER NOTICE LIST
# ============================================================

@teacher_notice.route("/")
def index():

    if not teacher_logged_in():

        return redirect(
            url_for("teacher_auth.login")
        )

    teacher_id = session["teacher_id"]

    cursor = mysql.connection.cursor()

    notices = []

    try:

        # ----------------------------------------------------
        # TEACHER DEPARTMENT
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                department
            FROM teachers
            WHERE id = %s
            LIMIT 1
            """,
            (teacher_id,)
        )

        teacher = cursor.fetchone()

        if not teacher:

            session.clear()

            return redirect(
                url_for("teacher_auth.login")
            )

        department = teacher[1]

        # ----------------------------------------------------
        # TEACHER NOTICE
        #
        # audience:
        # Everyone -> visible
        # Teachers  -> visible
        # Students  -> hidden
        #
        # Existing semester/department logic preserved.
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT DISTINCT
                n.id,
                n.title,
                n.description,
                n.image,
                n.pdf_file,
                n.target_semester,
                n.target_department,
                n.notice_type,
                n.created_at
            FROM notices n
            WHERE n.is_published = 1

              AND (
                    n.audience IS NULL
                    OR LOWER(TRIM(n.audience))
                       IN ('everyone', 'teachers')
                  )

              AND
              (
                    (
                        (
                            n.target_department IS NULL
                            OR TRIM(n.target_department) = ''
                        )
                        AND
                        (
                            n.target_semester IS NULL
                            OR TRIM(n.target_semester) = ''
                        )
                    )

                    OR

                    (
                        n.target_department IS NOT NULL
                        AND TRIM(n.target_department) <> ''

                        AND LOWER(TRIM(n.target_department))
                            =
                        LOWER(TRIM(%s))

                        AND
                        (
                            n.target_semester IS NULL
                            OR TRIM(n.target_semester) = ''
                        )
                    )

                    OR

                    (
                        n.target_semester IS NOT NULL
                        AND TRIM(n.target_semester) <> ''

                        AND EXISTS
                        (
                            SELECT 1
                            FROM subjects sub
                            WHERE sub.teacher_id = %s
                              AND LOWER(TRIM(sub.semester))
                                  =
                              LOWER(TRIM(n.target_semester))
                        )

                        AND
                        (
                            n.target_department IS NULL
                            OR TRIM(n.target_department) = ''
                        )
                    )

                    OR

                    (
                        n.target_department IS NOT NULL
                        AND TRIM(n.target_department) <> ''

                        AND LOWER(TRIM(n.target_department))
                            =
                        LOWER(TRIM(%s))

                        AND n.target_semester IS NOT NULL
                        AND TRIM(n.target_semester) <> ''

                        AND EXISTS
                        (
                            SELECT 1
                            FROM subjects sub
                            WHERE sub.teacher_id = %s
                              AND LOWER(TRIM(sub.semester))
                                  =
                              LOWER(TRIM(n.target_semester))
                        )
                    )
              )

            ORDER BY n.created_at DESC
            """,
            (
                department,
                teacher_id,
                department,
                teacher_id
            )
        )

        notices = cursor.fetchall() or []

    except Exception as e:

        print(
            "TEACHER NOTICE ERROR:",
            repr(e)
        )

        notices = []

    finally:
        cursor.close()

    return render_template(
        "teacher/notices.html",
        notices=notices
    )


# ============================================================
# VIEW NOTICE
# ============================================================

@teacher_notice.route(
    "/view/<int:notice_id>"
)
def view(notice_id):

    if not teacher_logged_in():

        return redirect(
            url_for("teacher_auth.login")
        )

    cursor = mysql.connection.cursor()

    notice = None

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
                       IN ('everyone', 'teachers')
                  )
            LIMIT 1
            """,
            (notice_id,)
        )

        notice = cursor.fetchone()

    except Exception as e:

        print(
            "TEACHER NOTICE VIEW ERROR:",
            repr(e)
        )

    finally:
        cursor.close()

    if not notice:

        return redirect(
            url_for("teacher_notice.index")
        )

    return render_template(
        "teacher/notice_view.html",
        notice=notice
    )


# ============================================================
# DOWNLOAD IMAGE
# ============================================================

@teacher_notice.route(
    "/download/image/<int:notice_id>"
)
def download_image(notice_id):

    if not teacher_logged_in():

        return redirect(
            url_for("teacher_auth.login")
        )

    cursor = mysql.connection.cursor()

    result = None

    try:

        cursor.execute(
            """
            SELECT image
            FROM notices
            WHERE id = %s
              AND is_published = 1
              AND (
                    audience IS NULL
                    OR LOWER(TRIM(audience))
                       IN ('everyone', 'teachers')
                  )
            LIMIT 1
            """,
            (notice_id,)
        )

        result = cursor.fetchone()

    except Exception as e:

        print(
            "TEACHER NOTICE IMAGE ERROR:",
            repr(e)
        )

    finally:
        cursor.close()

    if not result or not result[0]:

        return redirect(
            url_for("teacher_notice.index")
        )

    filename = os.path.basename(result[0])

    folder = get_notice_image_folder()

    path = os.path.join(
        folder,
        filename
    )

    if not os.path.isfile(path):

        return redirect(
            url_for("teacher_notice.index")
        )

    return send_file(
        path,
        as_attachment=True,
        download_name=filename
    )


# ============================================================
# DOWNLOAD PDF
# ============================================================

@teacher_notice.route(
    "/download/pdf/<int:notice_id>"
)
def download_pdf(notice_id):

    if not teacher_logged_in():

        return redirect(
            url_for("teacher_auth.login")
        )

    cursor = mysql.connection.cursor()

    result = None

    try:

        cursor.execute(
            """
            SELECT pdf_file
            FROM notices
            WHERE id = %s
              AND is_published = 1
              AND (
                    audience IS NULL
                    OR LOWER(TRIM(audience))
                       IN ('everyone', 'teachers')
                  )
            LIMIT 1
            """,
            (notice_id,)
        )

        result = cursor.fetchone()

    except Exception as e:

        print(
            "TEACHER NOTICE PDF ERROR:",
            repr(e)
        )

    finally:
        cursor.close()

    if not result or not result[0]:

        return redirect(
            url_for("teacher_notice.index")
        )

    filename = os.path.basename(result[0])

    folder = get_notice_pdf_folder()

    path = os.path.join(
        folder,
        filename
    )

    if not os.path.isfile(path):

        return redirect(
            url_for("teacher_notice.index")
        )

    return send_file(
        path,
        as_attachment=True,
        download_name=filename
    )