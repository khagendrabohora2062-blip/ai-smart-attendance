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
        print(
            "MYSQL IMPORT ERROR:",
            repr(e)
        )

    raise RuntimeError(
        "MySQL connection is not initialized. "
        "Please check MySQL configuration in app.py."
    )


# ============================================================
# ADMIN ACCESS CHECK
# ============================================================

def admin_required():
    return bool(
        session.get("admin_id")
    )


# ============================================================
# LOGIN REDIRECT
# ============================================================

def admin_login_redirect():

    try:
        return redirect(
            url_for("auth.login")
        )

    except Exception:
        return redirect("/login")


# ============================================================
# SAFE INTEGER PARSER
# ============================================================

def parse_positive_int(value, field_name):

    """
    Convert form/API value to a positive integer.

    This prevents values such as:
        '?'
        ''
        'abc'
        'None'

    from reaching MySQL INTEGER columns.
    """

    if value is None:
        raise ValueError(
            f"{field_name} is required."
        )

    value = str(value).strip()

    if not value:
        raise ValueError(
            f"{field_name} is required."
        )

    if value in ("?", "None", "null", "NULL"):
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
# ROUTINE TEMPLATE HELPER
# ============================================================

def render_routine_page(**context):

    possible_templates = [
        "admin/routines.html",
        "admin/routine.html",
        "routine.html",
    ]

    for template_name in possible_templates:

        try:
            current_app.jinja_env.get_template(
                template_name
            )

            print(
                "ROUTINE TEMPLATE FOUND:",
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
        "admin/routine-form.html",
    ]

    for template_name in possible_templates:

        try:
            current_app.jinja_env.get_template(
                template_name
            )

            print(
                "ROUTINE FORM TEMPLATE FOUND:",
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
# COMMON FORM DATA
# ============================================================

def get_form_data(cursor):

    # --------------------------------------------------------
    # SUBJECTS
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # DEPARTMENTS
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # SEMESTERS
    # --------------------------------------------------------

    cursor.execute(
        """
        SELECT DISTINCT
            semester
        FROM subjects
        WHERE semester IS NOT NULL
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
            """
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

                CASE r.day
                    WHEN 'Sunday' THEN 1
                    WHEN 'Monday' THEN 2
                    WHEN 'Tuesday' THEN 3
                    WHEN 'Wednesday' THEN 4
                    WHEN 'Thursday' THEN 5
                    WHEN 'Friday' THEN 6
                    WHEN 'Saturday' THEN 7
                    ELSE 8
                END ASC,

                r.start_time ASC
            """
        )

        routines = cursor.fetchall()

        print(
            "ROUTINES LOADED:",
            len(routines)
        )

        # ----------------------------------------------------
        # DEPARTMENTS
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # SEMESTERS
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT DISTINCT
                semester
            FROM subjects
            WHERE semester IS NOT NULL
            ORDER BY
                semester ASC
            """
        )

        semesters = cursor.fetchall()

        return render_routine_page(
            routines=routines,
            departments=departments,
            semesters=semesters
        )

    except TemplateNotFound:

        flash(
            "Routine page template not found.",
            "danger"
        )

        try:
            return redirect(
                url_for("admin.dashboard")
            )

        except Exception:
            return redirect(
                "/admin/dashboard"
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

        try:
            return redirect(
                url_for("admin.dashboard")
            )

        except Exception:
            return redirect(
                "/admin/dashboard"
            )

    finally:

        if cursor is not None:

            try:
                cursor.close()

            except Exception:
                pass


# ============================================================
# ADD ROUTINE
# ============================================================

@routine.route(
    "/add",
    methods=["GET", "POST"],
    endpoint="add"
)
@routine.route(
    "/add",
    methods=["GET", "POST"],
    endpoint="add_routine"
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

            semester = request.form.get(
                "semester",
                ""
            ).strip()

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

            room = request.form.get(
                "room",
                ""
            ).strip()

            print(
                "ADD ROUTINE FORM:",
                {
                    "semester": semester,
                    "department": department,
                    "section": section,
                    "day": day,
                    "start_time": start_time,
                    "end_time": end_time,
                    "subject_id": subject_raw,
                    "room": room
                }
            )

            # ------------------------------------------------
            # REQUIRED
            # ------------------------------------------------

            if not all([
                semester,
                department,
                day,
                start_time,
                end_time
            ]):

                flash(
                    "Please fill all required fields.",
                    "danger"
                )

                return redirect(
                    url_for("routine.add")
                )

            # ------------------------------------------------
            # SUBJECT ID INTEGER VALIDATION
            # ------------------------------------------------

            try:

                subject_id = parse_positive_int(
                    subject_raw,
                    "Subject ID"
                )

            except ValueError as e:

                flash(
                    str(e),
                    "danger"
                )

                return redirect(
                    url_for("routine.add")
                )

            # ------------------------------------------------
            # TIME
            # ------------------------------------------------

            if start_time >= end_time:

                flash(
                    "End time must be later than start time.",
                    "danger"
                )

                return redirect(
                    url_for("routine.add")
                )

            # =================================================
            # GET SUBJECT
            # =================================================

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

                flash(
                    "Selected subject was not found.",
                    "danger"
                )

                return redirect(
                    url_for("routine.add")
                )

            # ------------------------------------------------
            # SUBJECT ID FROM DB
            # ------------------------------------------------

            subject_db_id = parse_positive_int(
                subject[0],
                "Subject ID"
            )

            subject_semester = subject[1]
            subject_department = subject[2]
            teacher_raw = subject[3]

            # ------------------------------------------------
            # TEACHER ID
            # ------------------------------------------------

            if teacher_raw is None:

                flash(
                    "The selected subject does not have "
                    "a teacher assigned.",
                    "danger"
                )

                return redirect(
                    url_for("routine.add")
                )

            try:

                teacher_id = parse_positive_int(
                    teacher_raw,
                    "Teacher ID"
                )

            except ValueError as e:

                flash(
                    str(e),
                    "danger"
                )

                return redirect(
                    url_for("routine.add")
                )

            # ------------------------------------------------
            # SEMESTER
            # ------------------------------------------------

            if str(subject_semester).strip() != str(
                semester
            ).strip():

                flash(
                    "Selected subject does not belong "
                    "to the selected semester.",
                    "danger"
                )

                return redirect(
                    url_for("routine.add")
                )

            # ------------------------------------------------
            # DEPARTMENT
            # ------------------------------------------------

            if subject_department:

                if (
                    str(subject_department).strip().lower()
                    !=
                    str(department).strip().lower()
                ):

                    flash(
                        "Selected subject does not belong "
                        "to the selected department.",
                        "danger"
                    )

                    return redirect(
                        url_for("routine.add")
                    )

            # =================================================
            # TEACHER CONFLICT
            # =================================================

            cursor.execute(
                """
                SELECT id
                FROM routines
                WHERE teacher_id = %s
                  AND day = %s
                  AND start_time < %s
                  AND end_time > %s
                LIMIT 1
                """,
                (
                    teacher_id,
                    day,
                    end_time,
                    start_time
                )
            )

            if cursor.fetchone():

                flash(
                    "This teacher already has another "
                    "class at this time.",
                    "danger"
                )

                return redirect(
                    url_for("routine.add")
                )

            # =================================================
            # ROOM CONFLICT
            # =================================================

            if room:

                cursor.execute(
                    """
                    SELECT id
                    FROM routines
                    WHERE room = %s
                      AND day = %s
                      AND start_time < %s
                      AND end_time > %s
                    LIMIT 1
                    """,
                    (
                        room,
                        day,
                        end_time,
                        start_time
                    )
                )

                if cursor.fetchone():

                    flash(
                        "This room is already occupied "
                        "at this time.",
                        "danger"
                    )

                    return redirect(
                        url_for("routine.add")
                    )

            # =================================================
            # CLASS CONFLICT
            # =================================================

            cursor.execute(
                """
                SELECT id
                FROM routines
                WHERE semester = %s
                  AND department = %s
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
                LIMIT 1
                """,
                (
                    semester,
                    department,
                    section,
                    section,
                    day,
                    end_time,
                    start_time
                )
            )

            if cursor.fetchone():

                flash(
                    "This class already has another "
                    "routine at this time.",
                    "danger"
                )

                return redirect(
                    url_for("routine.add")
                )

            # =================================================
            # INSERT
            # =================================================

            cursor.execute(
                """
                INSERT INTO routines
                (
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
                    %s
                )
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

        # ====================================================
        # GET FORM
        # ====================================================

        (
            subjects,
            departments,
            semesters
        ) = get_form_data(cursor)

        return render_routine_form(
            form_title="Add Routine",
            form_action=url_for(
                "routine.add_routine"
            ),
            routine_data=None,
            subjects=subjects,
            departments=departments,
            semesters=semesters
        )

    except Exception as e:

        if mysql is not None:

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

        if cursor is not None:

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

        mysql = get_mysql()
        cursor = mysql.connection.cursor()

        # ====================================================
        # ROUTINE ID VALIDATION
        # ====================================================

        try:

            routine_id = parse_positive_int(
                routine_id,
                "Routine ID"
            )

        except ValueError as e:

            flash(
                str(e),
                "danger"
            )

            return redirect(
                url_for("routine.index")
            )

        # ====================================================
        # CURRENT ROUTINE
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

            semester = request.form.get(
                "semester",
                ""
            ).strip()

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

            room = request.form.get(
                "room",
                ""
            ).strip()

            print(
                "EDIT ROUTINE FORM:",
                {
                    "routine_id": routine_id,
                    "semester": semester,
                    "department": department,
                    "section": section,
                    "day": day,
                    "start_time": start_time,
                    "end_time": end_time,
                    "subject_id": subject_raw,
                    "room": room
                }
            )

            # ------------------------------------------------
            # REQUIRED
            # ------------------------------------------------

            if not all([
                semester,
                department,
                day,
                start_time,
                end_time
            ]):

                flash(
                    "Please fill all required fields.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "routine.edit",
                        routine_id=routine_id
                    )
                )

            # ------------------------------------------------
            # SUBJECT ID
            # ------------------------------------------------

            try:

                subject_id = parse_positive_int(
                    subject_raw,
                    "Subject ID"
                )

            except ValueError as e:

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

            # ------------------------------------------------
            # TIME
            # ------------------------------------------------

            if start_time >= end_time:

                flash(
                    "End time must be later than start time.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "routine.edit",
                        routine_id=routine_id
                    )
                )

            # =================================================
            # GET SUBJECT
            # =================================================

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

                flash(
                    "Selected subject was not found.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "routine.edit",
                        routine_id=routine_id
                    )
                )

            # ------------------------------------------------
            # SAFE SUBJECT ID
            # ------------------------------------------------

            subject_db_id = parse_positive_int(
                subject[0],
                "Subject ID"
            )

            # ------------------------------------------------
            # TEACHER ID
            # ------------------------------------------------

            if subject[3] is None:

                flash(
                    "The selected subject does not have "
                    "a teacher assigned.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "routine.edit",
                        routine_id=routine_id
                    )
                )

            try:

                teacher_id = parse_positive_int(
                    subject[3],
                    "Teacher ID"
                )

            except ValueError as e:

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

            # ------------------------------------------------
            # SEMESTER
            # ------------------------------------------------

            if str(subject[1]).strip() != str(
                semester
            ).strip():

                flash(
                    "Selected subject does not belong "
                    "to the selected semester.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "routine.edit",
                        routine_id=routine_id
                    )
                )

            # ------------------------------------------------
            # DEPARTMENT
            # ------------------------------------------------

            if subject[2]:

                if (
                    str(subject[2]).strip().lower()
                    !=
                    str(department).strip().lower()
                ):

                    flash(
                        "Selected subject does not belong "
                        "to the selected department.",
                        "danger"
                    )

                    return redirect(
                        url_for(
                            "routine.edit",
                            routine_id=routine_id
                        )
                    )

            # =================================================
            # TEACHER CONFLICT
            # =================================================

            cursor.execute(
                """
                SELECT id
                FROM routines
                WHERE teacher_id = %s
                  AND day = %s
                  AND start_time < %s
                  AND end_time > %s
                  AND id != %s
                LIMIT 1
                """,
                (
                    teacher_id,
                    day,
                    end_time,
                    start_time,
                    routine_id
                )
            )

            if cursor.fetchone():

                flash(
                    "This teacher already has another "
                    "class at this time.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "routine.edit",
                        routine_id=routine_id
                    )
                )

            # =================================================
            # ROOM CONFLICT
            # =================================================

            if room:

                cursor.execute(
                    """
                    SELECT id
                    FROM routines
                    WHERE room = %s
                      AND day = %s
                      AND start_time < %s
                      AND end_time > %s
                      AND id != %s
                    LIMIT 1
                    """,
                    (
                        room,
                        day,
                        end_time,
                        start_time,
                        routine_id
                    )
                )

                if cursor.fetchone():

                    flash(
                        "This room is already occupied "
                        "at this time.",
                        "danger"
                    )

                    return redirect(
                        url_for(
                            "routine.edit",
                            routine_id=routine_id
                        )
                    )

            # =================================================
            # CLASS CONFLICT
            # =================================================

            cursor.execute(
                """
                SELECT id
                FROM routines
                WHERE semester = %s
                  AND department = %s
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
                  AND id != %s
                LIMIT 1
                """,
                (
                    semester,
                    department,
                    section,
                    section,
                    day,
                    end_time,
                    start_time,
                    routine_id
                )
            )

            if cursor.fetchone():

                flash(
                    "This class already has another "
                    "routine at this time.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "routine.edit",
                        routine_id=routine_id
                    )
                )

            # =================================================
            # UPDATE
            # =================================================

            print(
                "UPDATING ROUTINE:",
                {
                    "routine_id": routine_id,
                    "subject_id": subject_db_id,
                    "teacher_id": teacher_id
                }
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

            print(
                "ROUTINE UPDATE SUCCESS:",
                routine_id
            )

            flash(
                "Routine updated successfully.",
                "success"
            )

            return redirect(
                url_for("routine.index")
            )

        # ====================================================
        # FORM DATA
        # ====================================================

        (
            subjects,
            departments,
            semesters
        ) = get_form_data(cursor)

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

        if mysql is not None:

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

        if cursor is not None:

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

        mysql = get_mysql()
        cursor = mysql.connection.cursor()

        routine_id = parse_positive_int(
            routine_id,
            "Routine ID"
        )

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

        if mysql is not None:

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

        if cursor is not None:

            try:
                cursor.close()

            except Exception:
                pass

    return redirect(
        url_for("routine.index")
    )


# ============================================================
# SUBJECTS API
# ============================================================

@routine.route("/subjects")
def subjects_api():

    if not admin_required():

        return jsonify({
            "success": False,
            "message": "Unauthorized"
        }), 401

    semester = request.args.get(
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

        # ----------------------------------------------------
        # SEMESTER
        # ----------------------------------------------------

        if semester:

            query += """
                AND CAST(s.semester AS CHAR) = %s
            """

            params.append(
                semester
            )

        # ----------------------------------------------------
        # DEPARTMENT
        # ----------------------------------------------------

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
                "department": row[4],
                "teacher_id": row[5],
                "teacher_name":
                    row[6]
                    if row[6]
                    else "No teacher assigned"
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

        if cursor is not None:

            try:
                cursor.close()

            except Exception:
                pass


# ============================================================
# DEPARTMENTS API
# ============================================================

@routine.route("/departments")
def departments_api():

    if not admin_required():

        return jsonify({
            "success": False,
            "message": "Unauthorized"
        }), 401

    semester = request.args.get(
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

        if semester:

            query += """
                AND CAST(semester AS CHAR) = %s
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

        if cursor is not None:

            try:
                cursor.close()

            except Exception:
                pass


# ============================================================
# END OF routes/routine.py
# ============================================================