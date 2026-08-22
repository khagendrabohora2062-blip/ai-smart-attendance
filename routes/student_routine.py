# ============================================================
# STUDENT ROUTINE
#
# File:
# routes/student_routine.py
# ============================================================

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    session,
    current_app
)

from jinja2 import TemplateNotFound


# ============================================================
# BLUEPRINT
# ============================================================

student_routine = Blueprint(
    "student_routine",
    __name__,
    url_prefix="/student/routines"
)


# ============================================================
# MYSQL HELPER
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
            "STUDENT ROUTINE MYSQL IMPORT ERROR:",
            repr(e)
        )

    raise RuntimeError(
        "MySQL connection is not initialized."
    )


# ============================================================
# STUDENT LOGIN CHECK
# ============================================================

def student_required():

    return bool(
        session.get("student_id")
    )


# ============================================================
# LOGIN REDIRECT
# ============================================================

def student_login_redirect():

    possible_endpoints = [
        "student_auth.login",
        "student.login",
        "auth.login"
    ]

    for endpoint in possible_endpoints:

        try:

            return redirect(
                url_for(endpoint)
            )

        except Exception:

            continue

    return redirect("/login")


# ============================================================
# STUDENT ROUTINE PAGE
# ============================================================

@student_routine.route("/")
def index():

    # --------------------------------------------------------
    # LOGIN CHECK
    # --------------------------------------------------------

    if not student_required():

        flash(
            "Please login as student.",
            "warning"
        )

        return student_login_redirect()


    mysql = None
    cursor = None


    try:

        # ====================================================
        # MYSQL CONNECTION
        # ====================================================

        mysql = get_mysql()

        cursor = mysql.connection.cursor()


        # ====================================================
        # LOGGED-IN STUDENT
        # ====================================================

        logged_student = session.get(
            "student_id"
        )

        print(
            "================================================"
        )

        print(
            "STUDENT ROUTINE SESSION ID:",
            logged_student
        )

        print(
            "================================================"
        )


        # ====================================================
        # FIND STUDENT
        #
        # IMPORTANT:
        # Do NOT use students.name here because your
        # students table does not contain that column.
        # ====================================================

        cursor.execute(
            """
            SELECT
                id,
                student_id,
                department,
                semester,
                section
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


        # ====================================================
        # STUDENT NOT FOUND
        # ====================================================

        if not student:

            flash(
                "Student account was not found.",
                "danger"
            )

            return redirect(
                url_for("student_auth.dashboard")
            )


        # ====================================================
        # STUDENT DATA
        # ====================================================

        student_db_id = student[0]
        student_code = student[1]
        student_department = student[2]
        student_semester = student[3]
        student_section = student[4]


        # ====================================================
        # STUDENT NAME
        #
        # Get from session because students.name does not exist.
        # ====================================================

        student_name = session.get(
            "student_name",
            "Student"
        )


        print(
            "STUDENT DB ID:",
            student_db_id
        )

        print(
            "STUDENT CODE:",
            student_code
        )

        print(
            "STUDENT NAME:",
            student_name
        )

        print(
            "STUDENT DEPARTMENT:",
            student_department
        )

        print(
            "STUDENT SEMESTER:",
            student_semester
        )

        print(
            "STUDENT SECTION:",
            student_section
        )


        # ====================================================
        # GET ROUTINE
        # ====================================================
        #
        # Important:
        #
        # semester can be:
        #       4
        #       4th
        #
        # So we compare numeric value:
        #
        #       CAST(... AS UNSIGNED)
        #
        # This makes 4 and 4th match.
        #
        # ====================================================

        query = """
            SELECT

                r.id,

                r.semester,

                r.department,

                r.section,

                r.day,

                r.start_time,

                r.end_time,

                r.room,

                s.subject_code,

                s.subject_name,

                t.full_name

            FROM routines r

            LEFT JOIN subjects s
                ON r.subject_id = s.id

            LEFT JOIN teachers t
                ON r.teacher_id = t.id

            WHERE 1 = 1
        """


        params = []


        # ====================================================
        # SEMESTER FILTER
        # ====================================================
        #
        # Handles:
        #
        # Student = 4th
        # Routine  = 4
        #
        # Student = 4
        # Routine  = 4th
        #
        # ====================================================

        if student_semester is not None:

            query += """

                AND CAST(r.semester AS UNSIGNED)
                    =
                    CAST(%s AS UNSIGNED)

            """

            params.append(
                student_semester
            )


        # ====================================================
        # DEPARTMENT FILTER
        # ====================================================

        if student_department:

            query += """

                AND LOWER(
                    TRIM(r.department)
                )
                =
                LOWER(
                    TRIM(%s)
                )

            """

            params.append(
                student_department
            )


        # ====================================================
        # SECTION FILTER
        # ====================================================
        #
        # If student's section is NULL:
        #
        #     show routine regardless of section.
        #
        # If student's section exists:
        #
        #     match same section
        #     OR routine section NULL
        #     OR routine section empty
        #
        # ====================================================

        if student_section:

            query += """

                AND (
                    r.section = %s

                    OR r.section IS NULL

                    OR TRIM(r.section) = ''
                )

            """

            params.append(
                student_section
            )


        # ====================================================
        # ORDER BY DAY + TIME
        # ====================================================

        query += """

            ORDER BY

                CASE LOWER(
                    TRIM(r.day)
                )

                    WHEN 'sunday' THEN 1

                    WHEN 'monday' THEN 2

                    WHEN 'tuesday' THEN 3

                    WHEN 'wednesday' THEN 4

                    WHEN 'thursday' THEN 5

                    WHEN 'friday' THEN 6

                    WHEN 'saturday' THEN 7

                    ELSE 8

                END ASC,

                r.start_time ASC

        """


        # ====================================================
        # EXECUTE ROUTINE QUERY
        # ====================================================

        print(
            "STUDENT ROUTINE QUERY PARAMS:",
            params
        )


        cursor.execute(
            query,
            tuple(params)
        )


        routines = cursor.fetchall()


        # ====================================================
        # ROUTINE COUNT
        # ====================================================

        print(
            "STUDENT ROUTINES LOADED:",
            len(routines)
        )


        # ====================================================
        # DEBUG ROUTINE DATA
        # ====================================================

        for routine in routines:

            print(
                "ROUTINE:",
                routine
            )


        # ====================================================
        # TEMPLATE
        # ====================================================

        possible_templates = [

            "student/routine.html",

            "student/routines.html",

            "student_routine.html"

        ]


        for template_name in possible_templates:

            try:

                current_app.jinja_env.get_template(
                    template_name
                )


                return render_template(

                    template_name,

                    routines=routines,

                    student=student,

                    student_name=student_name,

                    student_id=student_code,

                    semester=student_semester,

                    department=student_department,

                    section=student_section

                )


            except TemplateNotFound:

                continue


        # ====================================================
        # NO TEMPLATE FOUND
        # ====================================================

        raise TemplateNotFound(
            "student/routine.html"
        )


    # ========================================================
    # ERROR HANDLING
    # ========================================================

    except Exception as e:

        print(
            "================================================"
        )

        print(
            "STUDENT ROUTINE ERROR:",
            repr(e)
        )

        print(
            "================================================"
        )


        flash(
            f"Unable to load routine: {str(e)}",
            "danger"
        )


        return redirect(
            url_for("student_auth.dashboard")
        )


    # ========================================================
    # CLOSE CURSOR
    # ========================================================

    finally:

        if cursor is not None:

            try:

                cursor.close()

            except Exception:

                pass