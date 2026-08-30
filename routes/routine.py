
# ============================================================
# ROUTINE MANAGEMENT
# File: routes/routine.py
# ============================================================

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    current_app,
    jsonify
)

from jinja2 import TemplateNotFound


# ============================================================
# BLUEPRINT
# ============================================================

routine = Blueprint(
    "routine",
    __name__,
    url_prefix="/admin/routines"
)


# ============================================================
# MYSQL CONNECTION HELPER
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
        print("MYSQL IMPORT ERROR:", repr(e))

    raise RuntimeError(
        "MySQL connection is not initialized."
    )


# ============================================================
# ADMIN ACCESS CHECK
# ============================================================

def admin_required():
    return bool(session.get("admin_id"))


# ============================================================
# LOGIN REDIRECT
# ============================================================

def admin_login_redirect():
    try:
        return redirect(url_for("auth.login"))
    except Exception:
        return redirect("/login")


# ============================================================
# SAFE INTEGER PARSER
# ============================================================

def parse_positive_int(value, field_name):
    if value is None:
        raise ValueError(
            f"{field_name} is required."
        )

    value = str(value).strip()

    if not value:
        raise ValueError(
            f"{field_name} is required."
        )

    if value.lower() in (
        "?",
        "none",
        "null",
        "undefined"
    ):
        raise ValueError(
            f"Invalid {field_name}: {value}"
        )

    try:
        number = int(value)
    except (ValueError, TypeError):
        raise ValueError(
            f"Invalid {field_name}: {value}"
        )

    if number <= 0:
        raise ValueError(
            f"{field_name} must be a positive integer."
        )

    return number


# ============================================================
# SEMESTER PARSER
#
# Supports:
#   1
#   2
#   ...
#   8
#
# And:
#   1st
#   2nd
#   3rd
#   4th
#   5th
#   6th
#   7th
#   8th
# ============================================================

SEMESTER_MAP = {
    "1st": 1,
    "2nd": 2,
    "3rd": 3,
    "4th": 4,
    "5th": 5,
    "6th": 6,
    "7th": 7,
    "8th": 8,

    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
}


def parse_semester(value):
    if value is None:
        raise ValueError(
            "Semester is required."
        )

    value = str(value).strip().lower()

    if not value:
        raise ValueError(
            "Semester is required."
        )

    if value in (
        "?",
        "none",
        "null",
        "undefined"
    ):
        raise ValueError(
            f"Invalid semester: {value}"
        )

    # Direct mapping for 1st - 8th and 1 - 8
    if value in SEMESTER_MAP:
        return SEMESTER_MAP[value]

    # Also support values such as:
    # "1st semester"
    # "Semester 1"
    # "semester 4th"
    normalized = (
        value
        .replace("semester", "")
        .replace("sem", "")
        .strip()
    )

    if normalized in SEMESTER_MAP:
        return SEMESTER_MAP[normalized]

    # Final integer attempt
    try:
        semester = int(value)
    except (ValueError, TypeError):
        raise ValueError(
            f"Invalid semester: {value}"
        )

    if semester < 1 or semester > 8:
        raise ValueError(
            "Semester must be between 1st and 8th."
        )

    return semester


# ============================================================
# SEMESTER LABEL
# ============================================================

def semester_label(value):
    try:
        semester = parse_semester(value)
    except Exception:
        return str(value)

    labels = {
        1: "1st",
        2: "2nd",
        3: "3rd",
        4: "4th",
        5: "5th",
        6: "6th",
        7: "7th",
        8: "8th"
    }

    return labels.get(
        semester,
        str(semester)
    )


# ============================================================
# VALID DAYS
# ============================================================

VALID_DAYS = [
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday"
]


# ============================================================
# DAY ORDER
# ============================================================

DAY_ORDER_SQL = """
CASE r.day
    WHEN 'Sunday' THEN 1
    WHEN 'Monday' THEN 2
    WHEN 'Tuesday' THEN 3
    WHEN 'Wednesday' THEN 4
    WHEN 'Thursday' THEN 5
    WHEN 'Friday' THEN 6
    WHEN 'Saturday' THEN 7
    ELSE 8
END
"""


# ============================================================
# ROUTINE TEMPLATE HELPER
# ============================================================

def render_routine_page(**context):
    possible_templates = [
        "admin/routines.html",
        "admin/routine.html",
        "routine.html"
    ]

    for template_name in possible_templates:
        try:
            current_app.jinja_env.get_template(
                template_name
            )

            return render_template(
                template_name,
                **context
            )

        except TemplateNotFound:
            continue

    raise TemplateNotFound(
        "admin/routines.html"
    )


# ============================================================
# ROUTINE FORM TEMPLATE HELPER
# ============================================================

def render_routine_form(**context):
    possible_templates = [
        "admin/routine_form.html",
        "admin/routines_form.html",
        "admin/routine-form.html"
    ]

    for template_name in possible_templates:
        try:
            current_app.jinja_env.get_template(
                template_name
            )

            return render_template(
                template_name,
                **context
            )

        except TemplateNotFound:
            continue

    raise TemplateNotFound(
        "admin/routine_form.html"
    )


# ============================================================
# MANUAL ROUTINE ID GENERATOR
#
# Database AUTO_INCREMENT is NOT required.
# ============================================================

def get_next_routine_id(cursor):
    cursor.execute(
        """
        SELECT COALESCE(MAX(id), 0)
        FROM routines
        """
    )

    row = cursor.fetchone()

    if not row or row[0] is None:
        return 1

    try:
        current_id = int(row[0])
    except (ValueError, TypeError):
        current_id = 0

    return current_id + 1


# ============================================================
# COMMON FORM DATA
# ============================================================

def get_form_data(cursor):

    cursor.execute(
        """
        SELECT
            s.id,
            s.subject_code,
            s.subject_name,
            s.semester,
            s.department,
            s.teacher_id,
            t.full_name
        FROM subjects s
        LEFT JOIN teachers t
            ON s.teacher_id = t.id
        ORDER BY
            s.semester ASC,
            s.department ASC,
            s.subject_name ASC
        """
    )

    subjects = cursor.fetchall()


    cursor.execute(
        """
        SELECT DISTINCT
            TRIM(department) AS department
        FROM subjects
        WHERE department IS NOT NULL
          AND TRIM(department) <> ''
        ORDER BY
            TRIM(department) ASC
        """
    )

    departments = cursor.fetchall()


    cursor.execute(
        """
        SELECT DISTINCT
            semester
        FROM subjects
        WHERE semester IS NOT NULL
          AND semester BETWEEN 1 AND 8
        ORDER BY
            semester ASC
        """
    )

    semesters = cursor.fetchall()


    return (
        subjects,
        departments,
        semesters
    )


# ============================================================
# GET ROUTINE FORM VALUES
# ============================================================

def get_routine_form_values():

    semester_raw = request.form.get(
        "semester",
        ""
    )

    semester = parse_semester(
        semester_raw
    )


    department = request.form.get(
        "department",
        ""
    ).strip()


    section = request.form.get(
        "section",
        ""
    ).strip()


    day = request.form.get(
        "day",
        ""
    ).strip()


    start_time = request.form.get(
        "start_time",
        ""
    ).strip()


    end_time = request.form.get(
        "end_time",
        ""
    ).strip()


    subject_raw = request.form.get(
        "subject_id",
        ""
    )

    subject_id = parse_positive_int(
        subject_raw,
        "Subject ID"
    )


    room = request.form.get(
        "room",
        ""
    ).strip()


    if not department:
        raise ValueError(
            "Department is required."
        )


    if not day:
        raise ValueError(
            "Day is required."
        )


    if day not in VALID_DAYS:
        raise ValueError(
            f"Invalid day: {day}"
        )


    if not start_time:
        raise ValueError(
            "Start time is required."
        )


    if not end_time:
        raise ValueError(
            "End time is required."
        )


    if start_time >= end_time:
        raise ValueError(
            "End time must be later than start time."
        )


    return {
        "semester": semester,
        "semester_label": semester_label(semester),
        "department": department,
        "section": section,
        "day": day,
        "start_time": start_time,
        "end_time": end_time,
        "subject_id": subject_id,
        "room": room
    }


# ============================================================
# VALIDATE SUBJECT
# ============================================================

def validate_subject(
    cursor,
    subject_id,
    semester,
    department
):

    cursor.execute(
        """
        SELECT
            id,
            semester,
            department,
            teacher_id
        FROM subjects
        WHERE id = %s
        LIMIT 1
        """,
        (subject_id,)
    )

    subject = cursor.fetchone()


    if not subject:
        raise ValueError(
            "Selected subject was not found."
        )


    subject_db_id = parse_positive_int(
        subject[0],
        "Subject ID"
    )


    subject_semester = parse_semester(
        subject[1]
    )


    subject_department = (
        str(subject[2]).strip()
        if subject[2] is not None
        else ""
    )


    teacher_raw = subject[3]


    if teacher_raw is None:
        raise ValueError(
            "The selected subject does not have "
            "a teacher assigned."
        )


    teacher_id = parse_positive_int(
        teacher_raw,
        "Teacher ID"
    )


    if subject_semester != semester:
        raise ValueError(
            "Selected subject does not belong "
            "to the selected semester."
        )


    if subject_department:
        if (
            subject_department.lower()
            != department.lower()
        ):
            raise ValueError(
                "Selected subject does not belong "
                "to the selected department."
            )


    return (
        subject_db_id,
        teacher_id
    )


# ============================================================
# CHECK TEACHER CONFLICT
# ============================================================

def check_teacher_conflict(
    cursor,
    teacher_id,
    day,
    start_time,
    end_time,
    exclude_id=None
):

    query = """
        SELECT id
        FROM routines
        WHERE teacher_id = %s
          AND day = %s
          AND start_time < %s
          AND end_time > %s
    """

    params = [
        teacher_id,
        day,
        end_time,
        start_time
    ]


    if exclude_id is not None:
        query += """
            AND id != %s
        """

        params.append(
            exclude_id
        )


    query += " LIMIT 1"


    cursor.execute(
        query,
        tuple(params)
    )


    if cursor.fetchone():
        raise ValueError(
            "This teacher already has another "
            "class at this time."
        )


# ============================================================
# CHECK ROOM CONFLICT
# ============================================================

def check_room_conflict(
    cursor,
    room,
    day,
    start_time,
    end_time,
    exclude_id=None
):

    if not room:
        return


    query = """
        SELECT id
        FROM routines
        WHERE LOWER(TRIM(room))
              = LOWER(TRIM(%s))
          AND day = %s
          AND start_time < %s
          AND end_time > %s
    """

    params = [
        room,
        day,
        end_time,
        start_time
    ]


    if exclude_id is not None:
        query += """
            AND id != %s
        """

        params.append(
            exclude_id
        )


    query += " LIMIT 1"


    cursor.execute(
        query,
        tuple(params)
    )


    if cursor.fetchone():
        raise ValueError(
            "This room is already occupied "
            "at this time."
        )


# ============================================================
# CHECK CLASS CONFLICT
# ============================================================

def check_class_conflict(
    cursor,
    semester,
    department,
    section,
    day,
    start_time,
    end_time,
    exclude_id=None
):

    query = """
        SELECT id
        FROM routines
        WHERE semester = %s
          AND LOWER(TRIM(department))
              = LOWER(TRIM(%s))
          AND (
                section = %s
                OR (
                    (section IS NULL OR section = '')
                    AND %s = ''
                )
              )
          AND day = %s
          AND start_time < %s
          AND end_time > %s
    """

    params = [
        semester,
        department,
        section,
        section,
        day,
        end_time,
        start_time
    ]


    if exclude_id is not None:
        query += """
            AND id != %s
        """

        params.append(
            exclude_id
        )


    query += " LIMIT 1"


    cursor.execute(
        query,
        tuple(params)
    )


    if cursor.fetchone():
        raise ValueError(
            "This class already has another "
            "routine at this time."
        )


# ============================================================
# ROUTINE LIST
# ============================================================

@routine.route("/")
def index():

    if not admin_required():
        flash(
            "Please login as administrator.",
            "warning"
        )

        return admin_login_redirect()


    mysql = None
    cursor = None


    try:

        mysql = get_mysql()

        cursor = mysql.connection.cursor()


        cursor.execute(
            f"""
            SELECT
                r.id,
                r.semester,
                r.department,
                r.section,
                r.day,
                r.start_time,
                r.end_time,
                r.subject_id,
                s.subject_code,
                s.subject_name,
                r.teacher_id,
                t.full_name,
                r.room
            FROM routines r
            LEFT JOIN subjects s
                ON r.subject_id = s.id
            LEFT JOIN teachers t
                ON r.teacher_id = t.id
            ORDER BY
                r.semester ASC,
                r.department ASC,
                {DAY_ORDER_SQL},
                r.start_time ASC
            """
        )


        routines = cursor.fetchall()


        cursor.execute(
            """
            SELECT DISTINCT
                TRIM(department)
            FROM subjects
            WHERE department IS NOT NULL
              AND TRIM(department) <> ''
            ORDER BY
                TRIM(department)
            """
        )

        departments = cursor.fetchall()


        cursor.execute(
            """
            SELECT DISTINCT
                semester
            FROM subjects
            WHERE semester IS NOT NULL
              AND semester BETWEEN 1 AND 8
            ORDER BY semester ASC
            """
        )

        semesters = cursor.fetchall()


        return render_routine_page(
            routines=routines,
            departments=departments,
            semesters=semesters
        )


    except Exception as e:

        print(
            "ROUTINE LIST ERROR:",
            repr(e)
        )


        flash(
            f"Unable to load routine: {str(e)}",
            "danger"
        )


        return redirect(
            url_for("admin.dashboard")
        )


    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass


# ============================================================
# ADD ROUTINE
# ============================================================

@routine.route(
    "/add",
    methods=["GET", "POST"]
)
def add():

    if not admin_required():

        flash(
            "Please login as administrator.",
            "warning"
        )

        return admin_login_redirect()


    mysql = None
    cursor = None


    try:

        mysql = get_mysql()

        cursor = mysql.connection.cursor()


        # ====================================================
        # POST
        # ====================================================

        if request.method == "POST":

            try:

                data = get_routine_form_values()


                semester = data["semester"]
                department = data["department"]
                section = data["section"]
                day = data["day"]
                start_time = data["start_time"]
                end_time = data["end_time"]
                subject_id = data["subject_id"]
                room = data["room"]


                print(
                    "ADD ROUTINE DATA:",
                    data
                )


                # ------------------------------------------------
                # Validate selected subject
                # ------------------------------------------------

                (
                    subject_db_id,
                    teacher_id
                ) = validate_subject(
                    cursor,
                    subject_id,
                    semester,
                    department
                )


                # ------------------------------------------------
                # Check teacher conflict
                # ------------------------------------------------

                check_teacher_conflict(
                    cursor,
                    teacher_id,
                    day,
                    start_time,
                    end_time
                )


                # ------------------------------------------------
                # Check room conflict
                # ------------------------------------------------

                check_room_conflict(
                    cursor,
                    room,
                    day,
                    start_time,
                    end_time
                )


                # ------------------------------------------------
                # Check class conflict
                # ------------------------------------------------

                check_class_conflict(
                    cursor,
                    semester,
                    department,
                    section,
                    day,
                    start_time,
                    end_time
                )


                # ------------------------------------------------
                # Generate ID manually
                # ------------------------------------------------

                next_id = get_next_routine_id(
                    cursor
                )


                print(
                    "GENERATED ROUTINE ID:",
                    next_id
                )


                # ------------------------------------------------
                # INSERT
                # ------------------------------------------------

                cursor.execute(
                    """
                    INSERT INTO routines
                    (
                        id,
                        semester,
                        department,
                        section,
                        day,
                        start_time,
                        end_time,
                        subject_id,
                        teacher_id,
                        room
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    """,
                    (
                        next_id,
                        semester,
                        department,
                        section or None,
                        day,
                        start_time,
                        end_time,
                        subject_db_id,
                        teacher_id,
                        room or None
                    )
                )


                mysql.connection.commit()


                flash(
                    "Routine added successfully.",
                    "success"
                )


                return redirect(
                    url_for("routine.index")
                )


            except ValueError as e:

                try:
                    mysql.connection.rollback()
                except Exception:
                    pass


                flash(
                    str(e),
                    "danger"
                )


                return redirect(
                    url_for("routine.add")
                )


        # ====================================================
        # GET FORM
        # ====================================================

        (
            subjects,
            departments,
            semesters
        ) = get_form_data(
            cursor
        )


        return render_routine_form(
            form_title="Add Routine",
            form_action=url_for(
                "routine.add"
            ),
            routine_data=None,
            subjects=subjects,
            departments=departments,
            semesters=semesters
        )


    except Exception as e:

        if mysql:

            try:
                mysql.connection.rollback()
            except Exception:
                pass


        print(
            "ADD ROUTINE ERROR:",
            repr(e)
        )


        flash(
            f"Unable to add routine: {str(e)}",
            "danger"
        )


        return redirect(
            url_for("routine.index")
        )


    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass


# ============================================================
# EDIT ROUTINE
# ============================================================

@routine.route(
    "/edit/<int:routine_id>",
    methods=["GET", "POST"]
)
def edit(routine_id):

    if not admin_required():

        flash(
            "Please login as administrator.",
            "warning"
        )

        return admin_login_redirect()


    mysql = None
    cursor = None


    try:

        routine_id = parse_positive_int(
            routine_id,
            "Routine ID"
        )


        mysql = get_mysql()

        cursor = mysql.connection.cursor()


        # ====================================================
        # GET CURRENT ROUTINE
        # ====================================================

        cursor.execute(
            """
            SELECT
                id,
                semester,
                department,
                section,
                day,
                start_time,
                end_time,
                subject_id,
                teacher_id,
                room
            FROM routines
            WHERE id = %s
            LIMIT 1
            """,
            (routine_id,)
        )


        routine_data = cursor.fetchone()


        if not routine_data:

            flash(
                "Routine not found.",
                "danger"
            )

            return redirect(
                url_for("routine.index")
            )


        # ====================================================
        # POST
        # ====================================================

        if request.method == "POST":

            try:

                data = get_routine_form_values()


                semester = data["semester"]
                department = data["department"]
                section = data["section"]
                day = data["day"]
                start_time = data["start_time"]
                end_time = data["end_time"]
                subject_id = data["subject_id"]
                room = data["room"]


                (
                    subject_db_id,
                    teacher_id
                ) = validate_subject(
                    cursor,
                    subject_id,
                    semester,
                    department
                )


                check_teacher_conflict(
                    cursor,
                    teacher_id,
                    day,
                    start_time,
                    end_time,
                    routine_id
                )


                check_room_conflict(
                    cursor,
                    room,
                    day,
                    start_time,
                    end_time,
                    routine_id
                )


                check_class_conflict(
                    cursor,
                    semester,
                    department,
                    section,
                    day,
                    start_time,
                    end_time,
                    routine_id
                )


                cursor.execute(
                    """
                    UPDATE routines
                    SET
                        semester = %s,
                        department = %s,
                        section = %s,
                        day = %s,
                        start_time = %s,
                        end_time = %s,
                        subject_id = %s,
                        teacher_id = %s,
                        room = %s
                    WHERE id = %s
                    """,
                    (
                        semester,
                        department,
                        section or None,
                        day,
                        start_time,
                        end_time,
                        subject_db_id,
                        teacher_id,
                        room or None,
                        routine_id
                    )
                )


                mysql.connection.commit()


                flash(
                    "Routine updated successfully.",
                    "success"
                )


                return redirect(
                    url_for("routine.index")
                )


            except ValueError as e:

                try:
                    mysql.connection.rollback()
                except Exception:
                    pass


                flash(
                    str(e),
                    "danger"
                )


                return redirect(
                    url_for(
                        "routine.edit",
                        routine_id=routine_id
                    )
                )


        # ====================================================
        # FORM DATA
        # ====================================================

        (
            subjects,
            departments,
            semesters
        ) = get_form_data(
            cursor
        )


        return render_routine_form(
            form_title="Edit Routine",
            form_action=url_for(
                "routine.edit",
                routine_id=routine_id
            ),
            routine_data=routine_data,
            subjects=subjects,
            departments=departments,
            semesters=semesters
        )


    except Exception as e:

        if mysql:

            try:
                mysql.connection.rollback()
            except Exception:
                pass


        print(
            "EDIT ROUTINE ERROR:",
            repr(e)
        )


        flash(
            f"Unable to update routine: {str(e)}",
            "danger"
        )


        return redirect(
            url_for("routine.index")
        )


    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass


# ============================================================
# DELETE ROUTINE
# ============================================================

@routine.route(
    "/delete/<int:routine_id>",
    methods=["POST"]
)
def delete(routine_id):

    if not admin_required():

        flash(
            "Please login as administrator.",
            "warning"
        )

        return admin_login_redirect()


    mysql = None
    cursor = None


    try:

        routine_id = parse_positive_int(
            routine_id,
            "Routine ID"
        )


        mysql = get_mysql()

        cursor = mysql.connection.cursor()


        cursor.execute(
            """
            DELETE FROM routines
            WHERE id = %s
            """,
            (routine_id,)
        )


        mysql.connection.commit()


        flash(
            "Routine deleted successfully.",
            "success"
        )


    except Exception as e:

        if mysql:

            try:
                mysql.connection.rollback()
            except Exception:
                pass


        print(
            "DELETE ROUTINE ERROR:",
            repr(e)
        )


        flash(
            f"Unable to delete routine: {str(e)}",
            "danger"
        )


    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass


    return redirect(
        url_for("routine.index")
    )


# ============================================================
# SUBJECTS API
#
# Supports:
#   /admin/routines/subjects?semester=4th
#   /admin/routines/subjects?semester=4
#   /admin/routines/subjects?semester=4th&department=BCA
# ============================================================

@routine.route("/subjects")
def subjects_api():

    if not admin_required():

        return jsonify({
            "success": False,
            "message": "Unauthorized"
        }), 401


    semester_raw = request.args.get(
        "semester",
        ""
    ).strip()


    department = request.args.get(
        "department",
        ""
    ).strip()


    mysql = None
    cursor = None


    try:

        mysql = get_mysql()

        cursor = mysql.connection.cursor()


        query = """
            SELECT
                s.id,
                s.subject_code,
                s.subject_name,
                s.semester,
                s.department,
                s.teacher_id,
                t.full_name
            FROM subjects s
            LEFT JOIN teachers t
                ON s.teacher_id = t.id
            WHERE 1 = 1
        """


        params = []


        if semester_raw:

            semester = parse_semester(
                semester_raw
            )


            query += """
                AND s.semester = %s
            """


            params.append(
                semester
            )


        if department:

            query += """
                AND LOWER(TRIM(s.department))
                    = LOWER(TRIM(%s))
            """


            params.append(
                department
            )


        query += """
            ORDER BY
                s.subject_name ASC
        """


        cursor.execute(
            query,
            tuple(params)
        )


        rows = cursor.fetchall()


        data = []


        for row in rows:

            data.append({
                "id": row[0],
                "subject_code": row[1],
                "subject_name": row[2],
                "semester": row[3],
                "semester_label": semester_label(row[3]),
                "department": row[4],
                "teacher_id": row[5],
                "teacher_name": (
                    row[6]
                    if row[6]
                    else "No teacher assigned"
                )
            })


        return jsonify({
            "success": True,
            "subjects": data
        })


    except Exception as e:

        print(
            "SUBJECT API ERROR:",
            repr(e)
        )


        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass


# ============================================================
# DEPARTMENTS API
#
# Supports:
#   /admin/routines/departments?semester=4th
# ============================================================

@routine.route("/departments")
def departments_api():

    if not admin_required():

        return jsonify({
            "success": False,
            "message": "Unauthorized"
        }), 401


    semester_raw = request.args.get(
        "semester",
        ""
    ).strip()


    mysql = None
    cursor = None


    try:

        mysql = get_mysql()

        cursor = mysql.connection.cursor()


        query = """
            SELECT DISTINCT
                TRIM(department) AS department
            FROM subjects
            WHERE department IS NOT NULL
              AND TRIM(department) <> ''
        """


        params = []


        if semester_raw:

            semester = parse_semester(
                semester_raw
            )


            query += """
                AND semester = %s
            """


            params.append(
                semester
            )


        query += """
            ORDER BY
                TRIM(department) ASC
        """


        cursor.execute(
            query,
            tuple(params)
        )


        rows = cursor.fetchall()


        departments = []


        for row in rows:

            if row[0]:

                departments.append(
                    row[0]
                )


        return jsonify({
            "success": True,
            "departments": departments
        })


    except Exception as e:

        print(
            "DEPARTMENT API ERROR:",
            repr(e)
        )


        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass


# ============================================================
# SEMESTERS API
#
# Useful for HTML/JS dropdowns.
# ============================================================

@routine.route("/semesters")
def semesters_api():

    if not admin_required():

        return jsonify({
            "success": False,
            "message": "Unauthorized"
        }), 401


    mysql = None
    cursor = None


    try:

        mysql = get_mysql()

        cursor = mysql.connection.cursor()


        cursor.execute(
            """
            SELECT DISTINCT
                semester
            FROM subjects
            WHERE semester IS NOT NULL
              AND semester BETWEEN 1 AND 8
            ORDER BY semester ASC
            """
        )


        rows = cursor.fetchall()


        semesters = []


        for row in rows:

            if row[0] is not None:

                semester = parse_semester(
                    row[0]
                )


                semesters.append({
                    "value": semester,
                    "label": semester_label(
                        semester
                    )
                })


        return jsonify({
            "success": True,
            "semesters": semesters
        })


    except Exception as e:

        print(
            "SEMESTER API ERROR:",
            repr(e)
        )


        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass


# ============================================================
# END OF routes/routine.py
# ============================================================
