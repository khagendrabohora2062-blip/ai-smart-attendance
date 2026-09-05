import os

from io import BytesIO

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    session,
    current_app,
    send_file,
    abort
)

from extensions import mysql


# ============================================================
# STUDENT NOTICE
# File: routes/student_notice.py
# ============================================================

student_notice = Blueprint(
    "student_notice",
    __name__,
    url_prefix="/student/notices"
)


# ============================================================
# LOGIN
# ============================================================

def student_required():

    return bool(
        session.get("student_db_id")
    )


# ============================================================
# GET STUDENT
# ============================================================

def get_student(cursor):

    cursor.execute(
        """
        SELECT
            id,
            student_id,
            full_name,
            department,
            semester,
            section,
            photo
        FROM students
        WHERE id = %s
        LIMIT 1
        """,
        (
            session.get(
                "student_db_id"
            ),
        )
    )

    return cursor.fetchone()


# ============================================================
# VISIBILITY CONDITION
# ============================================================

def visibility_sql():

    return """
        AND (
            n.audience IS NULL
            OR LOWER(TRIM(n.audience))
               IN ('everyone', 'students')
        )

        AND (
            n.target_semester IS NULL
            OR TRIM(n.target_semester) = ''
            OR LOWER(TRIM(n.target_semester))
               =
               LOWER(TRIM(%s))
        )

        AND (
            n.target_department IS NULL
            OR TRIM(n.target_department) = ''
            OR LOWER(TRIM(n.target_department))
               =
               LOWER(TRIM(%s))
        )
    """


# ============================================================
# NOTICE LIST
# ============================================================

@student_notice.route("/")
def index():

    if not student_required():

        return redirect(
            url_for("student_auth.login")
        )

    cursor = mysql.connection.cursor()

    try:

        student = get_student(cursor)

        if not student:

            session.clear()

            return redirect(
                url_for("student_auth.login")
            )

        cursor.execute(
            """
            SELECT
                n.id,
                n.title,
                n.description,
                n.image,
                n.pdf_file,
                n.target_semester,
                n.target_department,
                n.notice_type,
                n.created_at,
                n.image_data,
                n.pdf_data

            FROM notices n

            WHERE n.is_published = 1
            """
            + visibility_sql()
            +
            """
            ORDER BY
                n.created_at DESC
            """,
            (
                student[4],
                student[3]
            )
        )

        notices = cursor.fetchall() or []

        return render_template(
            "student/notices.html",
            notices=notices
        )

    except Exception as e:

        try:
            mysql.connection.rollback()
        except Exception:
            pass

        print(
            "STUDENT NOTICE ERROR:",
            repr(e)
        )

        flash(
            "Unable to load notices.",
            "danger"
        )

        return redirect(
            url_for(
                "student_auth.dashboard"
            )
        )

    finally:

        try:
            cursor.close()
        except Exception:
            pass


# ============================================================
# NOTICE VIEW
# ============================================================

@student_notice.route(
    "/view/<int:notice_id>"
)
def view(notice_id):

    if not student_required():

        return redirect(
            url_for("student_auth.login")
        )

    cursor = mysql.connection.cursor()

    try:

        student = get_student(cursor)

        if not student:

            abort(404)

        cursor.execute(
            """
            SELECT
                n.id,
                n.title,
                n.description,
                n.image,
                n.pdf_file,
                n.target_semester,
                n.target_department,
                n.notice_type,
                n.created_at,
                n.image_data,
                n.pdf_data

            FROM notices n

            WHERE
                n.id = %s
                AND n.is_published = 1
            """
            + visibility_sql()
            +
            """
            LIMIT 1
            """,
            (
                notice_id,
                student[4],
                student[3]
            )
        )

        notice = cursor.fetchone()

        if not notice:

            flash(
                "Notice not found or not available for you.",
                "warning"
            )

            return redirect(
                url_for(
                    "student_notice.index"
                )
            )

        return render_template(
            "student/notice_view.html",
            notice=notice
        )

    finally:

        try:
            cursor.close()
        except Exception:
            pass


# ============================================================
# NOTICE IMAGE
# ============================================================

@student_notice.route(
    "/image/<int:notice_id>"
)
def image(notice_id):

    if not student_required():

        return redirect(
            url_for("student_auth.login")
        )

    cursor = mysql.connection.cursor()

    try:

        student = get_student(cursor)

        if not student:

            abort(404)

        cursor.execute(
            """
            SELECT
                n.image,
                n.image_data

            FROM notices n

            WHERE
                n.id = %s
                AND n.is_published = 1
            """
            + visibility_sql()
            +
            """
            LIMIT 1
            """,
            (
                notice_id,
                student[4],
                student[3]
            )
        )

        row = cursor.fetchone()

    finally:

        try:
            cursor.close()
        except Exception:
            pass

    if not row:

        abort(404)

    filename = os.path.basename(
        str(row[0] or "")
    )

    data = row[1]

    if data:

        extension = (
            os.path.splitext(
                filename
            )[1].lower()
        )

        mimetype_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif"
        }

        mimetype = mimetype_map.get(
            extension,
            "application/octet-stream"
        )

        return send_file(
            BytesIO(bytes(data)),
            mimetype=mimetype,
            as_attachment=False,
            download_name=(
                filename
                or f"notice_{notice_id}{extension}"
            )
        )

    # --------------------------------------------------------
    # OLD FILE
    # --------------------------------------------------------

    path = os.path.join(
        current_app.root_path,
        "static",
        "uploads",
        "notices",
        filename
    )

    if os.path.isfile(path):

        return send_file(
            path,
            as_attachment=False,
            download_name=filename
        )

    abort(404)


# ============================================================
# DOWNLOAD NOTICE IMAGE
# ============================================================

@student_notice.route(
    "/download/image/<int:notice_id>"
)
def download_image(notice_id):

    if not student_required():

        return redirect(
            url_for("student_auth.login")
        )

    cursor = mysql.connection.cursor()

    try:

        student = get_student(cursor)

        if not student:

            abort(404)

        cursor.execute(
            """
            SELECT
                n.image,
                n.image_data

            FROM notices n

            WHERE
                n.id = %s
                AND n.is_published = 1
            """
            + visibility_sql()
            +
            """
            LIMIT 1
            """,
            (
                notice_id,
                student[4],
                student[3]
            )
        )

        row = cursor.fetchone()

    finally:

        try:
            cursor.close()
        except Exception:
            pass

    if not row:

        abort(404)

    filename = os.path.basename(
        str(row[0] or "")
    )

    data = row[1]

    if data:

        return send_file(
            BytesIO(bytes(data)),
            mimetype="application/octet-stream",
            as_attachment=True,
            download_name=(
                filename
                or f"Notice_{notice_id}"
            )
        )

    path = os.path.join(
        current_app.root_path,
        "static",
        "uploads",
        "notices",
        filename
    )

    if os.path.isfile(path):

        return send_file(
            path,
            as_attachment=True,
            download_name=filename
        )

    flash(
        "Notice photo is not available.",
        "danger"
    )

    return redirect(
        url_for(
            "student_notice.view",
            notice_id=notice_id
        )
    )


# ============================================================
# NOTICE PDF VIEW
# ============================================================

@student_notice.route(
    "/pdf/<int:notice_id>"
)
def pdf(notice_id):

    if not student_required():

        return redirect(
            url_for("student_auth.login")
        )

    cursor = mysql.connection.cursor()

    try:

        student = get_student(cursor)

        if not student:

            abort(404)

        cursor.execute(
            """
            SELECT
                n.pdf_file,
                n.pdf_data

            FROM notices n

            WHERE
                n.id = %s
                AND n.is_published = 1
            """
            + visibility_sql()
            +
            """
            LIMIT 1
            """,
            (
                notice_id,
                student[4],
                student[3]
            )
        )

        row = cursor.fetchone()

    finally:

        try:
            cursor.close()
        except Exception:
            pass

    if not row:

        abort(404)

    filename = os.path.basename(
        str(row[0] or "")
    )

    data = row[1]

    if not filename:

        filename = (
            f"Notice_{notice_id}.pdf"
        )

    if data:

        return send_file(
            BytesIO(bytes(data)),
            mimetype="application/pdf",
            as_attachment=False,
            download_name=filename
        )

    path = os.path.join(
        current_app.root_path,
        "static",
        "uploads",
        "notices",
        "pdf",
        filename
    )

    if os.path.isfile(path):

        return send_file(
            path,
            mimetype="application/pdf",
            as_attachment=False,
            download_name=filename
        )

    flash(
        "Notice PDF is not available.",
        "danger"
    )

    return redirect(
        url_for(
            "student_notice.view",
            notice_id=notice_id
        )
    )


# ============================================================
# DOWNLOAD NOTICE PDF
# ============================================================

@student_notice.route(
    "/download/pdf/<int:notice_id>"
)
def download_pdf(notice_id):

    if not student_required():

        return redirect(
            url_for("student_auth.login")
        )

    cursor = mysql.connection.cursor()

    try:

        student = get_student(cursor)

        if not student:

            abort(404)

        cursor.execute(
            """
            SELECT
                n.pdf_file,
                n.pdf_data

            FROM notices n

            WHERE
                n.id = %s
                AND n.is_published = 1
            """
            + visibility_sql()
            +
            """
            LIMIT 1
            """,
            (
                notice_id,
                student[4],
                student[3]
            )
        )

        row = cursor.fetchone()

    finally:

        try:
            cursor.close()
        except Exception:
            pass

    if not row:

        abort(404)

    filename = os.path.basename(
        str(row[0] or "")
    )

    data = row[1]

    if not filename:

        filename = (
            f"Notice_{notice_id}.pdf"
        )

    if data:

        return send_file(
            BytesIO(bytes(data)),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename
        )

    path = os.path.join(
        current_app.root_path,
        "static",
        "uploads",
        "notices",
        "pdf",
        filename
    )

    if os.path.isfile(path):

        return send_file(
            path,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename
        )

    flash(
        "Notice PDF is not available.",
        "danger"
    )

    return redirect(
        url_for(
            "student_notice.view",
            notice_id=notice_id
        )
    )