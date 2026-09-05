import os

from io import BytesIO

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    session,
    flash,
    current_app,
    send_file,
    abort
)

from extensions import mysql


# ============================================================
# STUDENT SYLLABUS
# File: routes/student_syllabus.py
# ============================================================

student_syllabus = Blueprint(
    "student_syllabus",
    __name__,
    url_prefix="/student/syllabus"
)


def logged_in():

    return bool(
        session.get("student_db_id")
    )


def safe_filename(filename):

    if not filename:
        return ""

    return os.path.basename(
        str(filename)
        .replace("\\", "/")
        .strip()
    )


# ============================================================
# SYLLABUS LIST
# ============================================================

@student_syllabus.route("/")
def index():

    if not logged_in():

        return redirect(
            url_for("student_auth.login")
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
                department,
                semester,
                section,
                photo
            FROM students
            WHERE id = %s
            LIMIT 1
            """,
            (
                session["student_db_id"],
            )
        )

        student = cursor.fetchone()

        if not student:

            session.clear()

            return redirect(
                url_for("student_auth.login")
            )

        cursor.execute(
            """
            SELECT
                s.id,
                s.department,
                s.semester,
                s.subject_id,
                sub.subject_code,
                sub.subject_name,
                s.title,
                s.description,
                s.file_name,
                s.file_path,
                s.created_at,
                s.updated_at,
                s.file_data

            FROM syllabus s

            LEFT JOIN subjects sub
                ON s.subject_id = sub.id

            WHERE
                LOWER(
                    TRIM(
                        COALESCE(
                            s.department,
                            ''
                        )
                    )
                )
                =
                LOWER(
                    TRIM(
                        COALESCE(
                            %s,
                            ''
                        )
                    )
                )

                AND LOWER(
                    TRIM(
                        COALESCE(
                            s.semester,
                            ''
                        )
                    )
                )
                =
                LOWER(
                    TRIM(
                        COALESCE(
                            %s,
                            ''
                        )
                    )
                )

            ORDER BY
                sub.subject_code ASC,
                s.id DESC
            """,
            (
                student[4],
                student[5]
            )
        )

        syllabuses = cursor.fetchall() or []

        return render_template(
            "student/syllabus/index.html",
            student=student,
            syllabuses=syllabuses
        )

    except Exception as e:

        try:
            mysql.connection.rollback()
        except Exception:
            pass

        print(
            "STUDENT SYLLABUS ERROR:",
            repr(e)
        )

        flash(
            "Unable to load syllabus.",
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
# GET SYLLABUS FILE
# ============================================================

def get_syllabus_file(
    filename
):

    safe_name = safe_filename(
        filename
    )

    if (
        not safe_name
        or not safe_name.lower().endswith(".pdf")
    ):

        return None

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                s.file_name,
                s.file_path,
                s.file_data

            FROM syllabus s

            INNER JOIN students st
                ON st.id = %s

            WHERE
                (
                    s.file_name = %s

                    OR s.file_path = %s

                    OR s.file_path = %s
                )

                AND LOWER(
                    TRIM(
                        COALESCE(
                            s.department,
                            ''
                        )
                    )
                )
                =
                LOWER(
                    TRIM(
                        COALESCE(
                            st.department,
                            ''
                        )
                    )
                )

                AND LOWER(
                    TRIM(
                        COALESCE(
                            s.semester,
                            ''
                        )
                    )
                )
                =
                LOWER(
                    TRIM(
                        COALESCE(
                            st.semester,
                            ''
                        )
                    )
                )

            LIMIT 1
            """,
            (
                session["student_db_id"],
                safe_name,
                str(
                    filename
                )
                .replace(
                    "\\",
                    "/"
                )
                .lstrip("/"),
                "uploads/syllabus/"
                + safe_name
            )
        )

        return cursor.fetchone()

    finally:

        try:
            cursor.close()
        except Exception:
            pass


# ============================================================
# SERVE SYLLABUS
# ============================================================

def serve_syllabus(
    filename,
    download=False
):

    if not logged_in():

        return redirect(
            url_for("student_auth.login")
        )

    row = get_syllabus_file(
        filename
    )

    if not row:

        abort(404)

    actual_filename = (
        safe_filename(row[0])
        or safe_filename(filename)
        or "syllabus.pdf"
    )

    file_data = row[2]

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    if file_data:

        return send_file(
            BytesIO(
                bytes(file_data)
            ),
            mimetype="application/pdf",
            as_attachment=download,
            download_name=actual_filename
        )

    # --------------------------------------------------------
    # OLD PHYSICAL FILE
    # --------------------------------------------------------

    folder = os.path.join(
        current_app.root_path,
        "static",
        "uploads",
        "syllabus"
    )

    path = os.path.join(
        folder,
        actual_filename
    )

    if os.path.isfile(path):

        return send_file(
            path,
            mimetype="application/pdf",
            as_attachment=download,
            download_name=actual_filename
        )

    # --------------------------------------------------------
    # STORED FILE PATH FALLBACK
    # --------------------------------------------------------

    stored_path = str(
        row[1] or ""
    ).replace(
        "\\",
        "/"
    )

    possible_paths = [

        stored_path,

        os.path.join(
            current_app.root_path,
            stored_path
        ),

        os.path.join(
            current_app.root_path,
            "static",
            stored_path
        )

    ]

    for path in possible_paths:

        if os.path.isfile(path):

            return send_file(
                path,
                mimetype="application/pdf",
                as_attachment=download,
                download_name=actual_filename
            )

    flash(
        "Syllabus file is not available. "
        "Please ask the administrator to migrate or re-upload it.",
        "danger"
    )

    return redirect(
        url_for(
            "student_syllabus.index"
        )
    )


# ============================================================
# VIEW
# ============================================================

@student_syllabus.route(
    "/view/<path:filename>"
)
def view(filename):

    return serve_syllabus(
        filename,
        download=False
    )


# ============================================================
# DOWNLOAD
# ============================================================

@student_syllabus.route(
    "/download/<path:filename>"
)
def download(filename):

    return serve_syllabus(
        filename,
        download=True
    )