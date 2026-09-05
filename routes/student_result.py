from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    flash,
    send_from_directory,
    send_file
)

from extensions import mysql

import os
import io
import mimetypes


# ============================================================
# STUDENT RESULT BLUEPRINT
# ============================================================

student_result = Blueprint(
    "student_result",
    __name__,
    url_prefix="/student/result"
)


# ============================================================
# MARKSHEET FOLDER
# ============================================================

MARKSHEET_FOLDER = os.path.join(
    "static",
    "uploads",
    "marksheets"
)


# ============================================================
# MIME TYPE
# ============================================================

def get_marksheet_mimetype(filename):

    extension = os.path.splitext(
        filename or ""
    )[1].lower()

    mime_types = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp"
    }

    return (
        mime_types.get(extension)
        or mimetypes.guess_type(filename or "")[0]
        or "application/octet-stream"
    )


# ============================================================
# STUDENT RESULT PAGE
# ============================================================

@student_result.route("/")
def index():

    student_db_id = session.get(
        "student_db_id"
    )

    if not student_db_id:

        return redirect(
            url_for(
                "student_auth.login"
            )
        )

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                s.id,
                s.student_id,
                s.full_name,
                s.department,
                s.semester,
                s.photo,

                m.id AS marksheet_id,
                m.marksheet_file,
                m.created_at

            FROM students s

            LEFT JOIN marksheets m
                ON m.student_id = s.id

            WHERE s.id = %s

            ORDER BY
                m.created_at DESC
            """,
            (
                student_db_id,
            )
        )

        rows = cursor.fetchall()

    except Exception as e:

        try:
            mysql.connection.rollback()
        except Exception:
            pass

        print(
            "STUDENT RESULT ERROR:",
            repr(e)
        )

        flash(
            "Unable to load result.",
            "danger"
        )

        rows = []

    finally:

        try:
            cursor.close()
        except Exception:
            pass

    # ========================================================
    # STUDENT NOT FOUND
    # ========================================================

    if not rows:

        flash(
            "Student record not found.",
            "danger"
        )

        return redirect(
            url_for(
                "student_auth.login"
            )
        )

    # ========================================================
    # STUDENT INFORMATION
    # ========================================================

    student = {

        "id": rows[0][0],

        "student_id": rows[0][1],

        "full_name": rows[0][2],

        "department": rows[0][3],

        "semester": rows[0][4],

        "photo": rows[0][5]

    }

    # ========================================================
    # MARKSHEETS LIST
    # ========================================================

    marksheets = []

    for row in rows:

        marksheet_id = row[6]

        marksheet_file = row[7]

        created_at = row[8]

        if marksheet_id and marksheet_file:

            marksheets.append(
                {

                    "id": marksheet_id,

                    "file": marksheet_file,

                    "created_at": created_at

                }
            )

    # ========================================================
    # RENDER
    # ========================================================

    return render_template(
        "student/results.html",
        student=student,
        marksheets=marksheets
    )


# ============================================================
# VIEW / OPEN MARKSHEET
# ============================================================

@student_result.route(
    "/marksheet/<int:marksheet_id>"
)
def view_marksheet(marksheet_id):

    # --------------------------------------------------------
    # LOGIN CHECK
    # --------------------------------------------------------

    student_db_id = session.get(
        "student_db_id"
    )

    if not student_db_id:

        return redirect(
            url_for(
                "student_auth.login"
            )
        )

    cursor = mysql.connection.cursor()

    try:

        # ====================================================
        # GET FILE FROM DATABASE
        #
        # Security:
        # Student can only access their own marksheet.
        # ====================================================

        cursor.execute(
            """
            SELECT
                m.marksheet_file,
                m.file_data

            FROM marksheets m

            WHERE
                m.id = %s
                AND m.student_id = %s

            LIMIT 1
            """,
            (
                marksheet_id,
                student_db_id
            )
        )

        data = cursor.fetchone()

    except Exception as e:

        print(
            "VIEW MARKSHEET ERROR:",
            repr(e)
        )

        try:
            mysql.connection.rollback()
        except Exception:
            pass

        flash(
            "Unable to open marksheet.",
            "danger"
        )

        data = None

    finally:

        try:
            cursor.close()
        except Exception:
            pass

    # ========================================================
    # DATABASE RECORD NOT FOUND
    # ========================================================

    if not data:

        flash(
            "Marksheet not found.",
            "danger"
        )

        return redirect(
            url_for(
                "student_result.index"
            )
        )

    marksheet_file = data[0]
    file_data = data[1]

    # ========================================================
    # METHOD 1
    # DATABASE BLOB
    # ========================================================

    if file_data:

        try:

            response = send_file(
                io.BytesIO(
                    bytes(file_data)
                ),
                mimetype=get_marksheet_mimetype(
                    marksheet_file
                ),
                as_attachment=False,
                download_name=marksheet_file
            )

            # Browser लाई PDF/image inline खोल्न force
            response.headers["Content-Disposition"] = (
                f'inline; filename="{marksheet_file}"'
            )

            # Correct MIME
            response.headers["Content-Type"] = (
                get_marksheet_mimetype(
                    marksheet_file
                )
            )

            return response

        except Exception as e:

            print(
                "DATABASE MARKSHEET VIEW ERROR:",
                repr(e)
            )

    # ========================================================
    # METHOD 2
    # OLD PHYSICAL FILE FALLBACK
    # ========================================================

    if marksheet_file:

        file_path = os.path.join(
            MARKSHEET_FOLDER,
            marksheet_file
        )

        if os.path.isfile(file_path):

            return send_from_directory(
                MARKSHEET_FOLDER,
                marksheet_file,
                as_attachment=False
            )

    # ========================================================
    # FILE NOT AVAILABLE
    # ========================================================

    flash(
        "Marksheet file is missing from the server.",
        "danger"
    )

    return redirect(
        url_for(
            "student_result.index"
        )
    )