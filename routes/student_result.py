from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    flash,
    send_from_directory
)

from extensions import mysql
import os


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
# STUDENT RESULT PAGE
# ============================================================

@student_result.route("/")
def index():

    # --------------------------------------------------------
    # LOGIN CHECK
    # IMPORTANT:
    # student_db_id = students table primary key
    # student_id = student's visible ID such as 09
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
        # GET STUDENT + UPLOADED MARKSHEETS
        # ====================================================

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
    # RENDER PAGE
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
        # GET MARKSHEET
        # Security:
        # Student can only access their own marksheet
        # ====================================================

        cursor.execute(
            """
            SELECT
                m.marksheet_file

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
    # MARKSHEET NOT FOUND
    # ========================================================

    if not data or not data[0]:

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


    # ========================================================
    # FILE CHECK
    # ========================================================

    if not os.path.exists(
        os.path.join(
            MARKSHEET_FOLDER,
            marksheet_file
        )
    ):

        flash(
            "Marksheet file is missing from the server.",
            "danger"
        )

        return redirect(
            url_for(
                "student_result.index"
            )
        )


    # ========================================================
    # OPEN FILE
    # ========================================================

    return send_from_directory(
        MARKSHEET_FOLDER,
        marksheet_file,
        as_attachment=False
    )