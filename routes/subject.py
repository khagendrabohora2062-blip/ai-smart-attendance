from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    request,
    flash,
    jsonify
)

from extensions import mysql
import uuid


# ============================================================
# DEBUG - CONFIRM WHICH FILE IS RUNNING
# ============================================================

print("==========================================")
print("SUBJECT ROUTE LOADED FROM:", __file__)
print("==========================================")


# ============================================================
# SUBJECT BLUEPRINT
# ============================================================

subjects = Blueprint(
    "subjects",
    __name__,
    url_prefix="/subjects"
)


# ============================================================
# ADMIN CHECK
# ============================================================

def admin_required():
    return "admin_id" in session


# ============================================================
# SAFE ADMIN REDIRECT
# ============================================================

def admin_login_redirect():
    return redirect(url_for("auth.login"))


# ============================================================
# SELF-GENERATE SUBJECT ID
# ============================================================

def generate_subject_id(cursor):
    """
    Generate a unique positive integer ID.

    Database AUTO_INCREMENT आवश्यक पर्दैन।
    Python ले UUID बाट unique integer ID generate गर्छ।
    """

    while True:
        subject_id = uuid.uuid4().int % 2147483647

        if subject_id <= 0:
            continue

        cursor.execute(
            """
            SELECT id
            FROM subjects
            WHERE id = %s
            LIMIT 1
            """,
            (subject_id,)
        )

        existing_id = cursor.fetchone()

        if not existing_id:
            return subject_id


# ============================================================
# PARSE SEMESTER
# ============================================================

def parse_semester(value):
    """
    Convert semester values such as:
        1
        "1"
        "1st"
        "1st Semester"
        "Semester 1"

    into integer 1-8.
    """

    if value is None:
        raise ValueError("Semester is required.")

    value = str(value).strip().lower()

    if not value:
        raise ValueError("Semester is required.")

    # Direct number
    try:
        number = int(value)

        if 1 <= number <= 8:
            return number

    except (TypeError, ValueError):
        pass

    semester_map = {
        "1st": 1,
        "1st semester": 1,
        "semester 1": 1,

        "2nd": 2,
        "2nd semester": 2,
        "semester 2": 2,

        "3rd": 3,
        "3rd semester": 3,
        "semester 3": 3,

        "4th": 4,
        "4th semester": 4,
        "semester 4": 4,

        "5th": 5,
        "5th semester": 5,
        "semester 5": 5,

        "6th": 6,
        "6th semester": 6,
        "semester 6": 6,

        "7th": 7,
        "7th semester": 7,
        "semester 7": 7,

        "8th": 8,
        "8th semester": 8,
        "semester 8": 8,
    }

    if value in semester_map:
        return semester_map[value]

    raise ValueError("Semester must be between 1 and 8.")


# ============================================================
# SUBJECT LIST
# ============================================================

@subjects.route("/")
def index():

    if not admin_required():
        flash(
            "Please login as administrator.",
            "warning"
        )
        return admin_login_redirect()

    cursor = mysql.connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                s.id,
                s.subject_code,
                s.subject_name,
                s.semester,
                s.department,
                s.teacher_id,
                COALESCE(
                    t.full_name,
                    'Not Assigned'
                ) AS teacher_name
            FROM subjects s
            LEFT JOIN teachers t
                ON s.teacher_id = t.id
            ORDER BY
                s.semester ASC,
                s.department ASC,
                s.subject_code ASC
            """
        )

        subject_data = cursor.fetchall()

        return render_template(
            "admin/subjects.html",
            subjects=subject_data
        )

    except Exception as e:

        try:
            mysql.connection.rollback()
        except Exception:
            pass

        print(
            "SUBJECT LIST ERROR:",
            repr(e)
        )

        flash(
            f"Unable to load subjects: {str(e)}",
            "danger"
        )

        return redirect(
            url_for("admin.dashboard")
        )

    finally:

        try:
            cursor.close()
        except Exception:
            pass


# ============================================================
# ADD SUBJECT
# ============================================================

@subjects.route(
    "/add",
    methods=["GET", "POST"]
)
def add_subject():

    if not admin_required():
        flash(
            "Please login as administrator.",
            "warning"
        )
        return admin_login_redirect()

    cursor = mysql.connection.cursor()

    try:

        # ----------------------------------------------------
        # GET TEACHERS
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                full_name
            FROM teachers
            ORDER BY
                full_name ASC
            """
        )

        teachers = cursor.fetchall()

        # ----------------------------------------------------
        # POST
        # ----------------------------------------------------

        if request.method == "POST":

            print("==========================================")
            print("### NEW ADD SUBJECT POST ROUTE EXECUTED ###")
            print("FORM DATA:", request.form.to_dict())
            print("==========================================")

            subject_code = request.form.get(
                "subject_code",
                ""
            ).strip()

            subject_name = request.form.get(
                "subject_name",
                ""
            ).strip()

            semester_raw = request.form.get(
                "semester",
                ""
            ).strip()

            department = request.form.get(
                "department",
                ""
            ).strip()

            teacher_id_raw = request.form.get(
                "teacher_id",
                ""
            ).strip()

            # ------------------------------------------------
            # SUBJECT CODE
            # ------------------------------------------------

            if not subject_code:

                flash(
                    "Subject Code is required.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "subjects.add_subject"
                    )
                )

            # ------------------------------------------------
            # SUBJECT NAME
            # ------------------------------------------------

            if not subject_name:

                flash(
                    "Subject Name is required.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "subjects.add_subject"
                    )
                )

            # ------------------------------------------------
            # SEMESTER
            # ------------------------------------------------

            try:

                semester = parse_semester(
                    semester_raw
                )

            except ValueError as e:

                flash(
                    str(e),
                    "danger"
                )

                return redirect(
                    url_for(
                        "subjects.add_subject"
                    )
                )

            # ------------------------------------------------
            # DEPARTMENT
            # ------------------------------------------------

            if not department:

                flash(
                    "Department is required.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "subjects.add_subject"
                    )
                )

            # ------------------------------------------------
            # TEACHER
            # ------------------------------------------------

            if not teacher_id_raw:

                flash(
                    "Please select a teacher.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "subjects.add_subject"
                    )
                )

            try:

                teacher_id = int(
                    teacher_id_raw
                )

            except (TypeError, ValueError):

                flash(
                    "Invalid teacher selected.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "subjects.add_subject"
                    )
                )

            # ------------------------------------------------
            # CHECK TEACHER
            # ------------------------------------------------

            cursor.execute(
                """
                SELECT
                    id
                FROM teachers
                WHERE id = %s
                LIMIT 1
                """,
                (teacher_id,)
            )

            teacher = cursor.fetchone()

            if not teacher:

                flash(
                    "Selected teacher was not found.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "subjects.add_subject"
                    )
                )

            # ------------------------------------------------
            # CHECK DUPLICATE SUBJECT CODE
            # ------------------------------------------------

            cursor.execute(
                """
                SELECT
                    id
                FROM subjects
                WHERE LOWER(
                    TRIM(subject_code)
                ) = LOWER(
                    TRIM(%s)
                )
                LIMIT 1
                """,
                (subject_code,)
            )

            existing_subject = cursor.fetchone()

            if existing_subject:

                flash(
                    "Subject Code already exists!",
                    "danger"
                )

                return redirect(
                    url_for(
                        "subjects.add_subject"
                    )
                )

            # ------------------------------------------------
            # GENERATE SUBJECT ID
            # ------------------------------------------------

            subject_id = generate_subject_id(
                cursor
            )

            print("==========================================")
            print("### GENERATED SUBJECT ID ###")
            print("SUBJECT ID:", subject_id)
            print("==========================================")

            # ------------------------------------------------
            # INSERT SUBJECT
            # ------------------------------------------------

            cursor.execute(
                """
                INSERT INTO subjects
                (
                    id,
                    subject_code,
                    subject_name,
                    semester,
                    department,
                    teacher_id
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    subject_id,
                    subject_code,
                    subject_name,
                    semester,
                    department,
                    teacher_id
                )
            )

            mysql.connection.commit()

            print(
                "SUBJECT INSERT SUCCESS:",
                subject_id
            )

            flash(
                "Subject added successfully!",
                "success"
            )

            return redirect(
                url_for(
                    "subjects.index"
                )
            )

        # ----------------------------------------------------
        # GET PAGE
        # ----------------------------------------------------

        return render_template(
            "admin/add_subject.html",
            teachers=teachers
        )

    except Exception as e:

        try:
            mysql.connection.rollback()
        except Exception:
            pass

        print(
            "ADD SUBJECT ERROR:",
            repr(e)
        )

        flash(
            f"Unable to add subject: {str(e)}",
            "danger"
        )

        return redirect(
            url_for(
                "subjects.index"
            )
        )

    finally:

        try:
            cursor.close()
        except Exception:
            pass


# ============================================================
# EDIT SUBJECT
# ============================================================

@subjects.route(
    "/edit/<int:id>",
    methods=["GET", "POST"]
)
def edit_subject(id):

    if not admin_required():
        flash(
            "Please login as administrator.",
            "warning"
        )
        return admin_login_redirect()

    cursor = mysql.connection.cursor()

    try:

        # ----------------------------------------------------
        # GET TEACHERS
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                full_name
            FROM teachers
            ORDER BY
                full_name ASC
            """
        )

        teachers = cursor.fetchall()

        # ----------------------------------------------------
        # GET SUBJECT
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                subject_code,
                subject_name,
                semester,
                department,
                teacher_id
            FROM subjects
            WHERE id = %s
            LIMIT 1
            """,
            (id,)
        )

        subject = cursor.fetchone()

        if not subject:

            flash(
                "Subject not found.",
                "warning"
            )

            return redirect(
                url_for(
                    "subjects.index"
                )
            )

        # ----------------------------------------------------
        # POST
        # ----------------------------------------------------

        if request.method == "POST":

            subject_code = request.form.get(
                "subject_code",
                ""
            ).strip()

            subject_name = request.form.get(
                "subject_name",
                ""
            ).strip()

            semester_raw = request.form.get(
                "semester",
                ""
            ).strip()

            department = request.form.get(
                "department",
                ""
            ).strip()

            teacher_id_raw = request.form.get(
                "teacher_id",
                ""
            ).strip()

            # ------------------------------------------------
            # VALIDATION
            # ------------------------------------------------

            if not subject_code:

                flash(
                    "Subject Code is required.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "subjects.edit_subject",
                        id=id
                    )
                )

            if not subject_name:

                flash(
                    "Subject Name is required.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "subjects.edit_subject",
                        id=id
                    )
                )

            try:

                semester = parse_semester(
                    semester_raw
                )

            except ValueError as e:

                flash(
                    str(e),
                    "danger"
                )

                return redirect(
                    url_for(
                        "subjects.edit_subject",
                        id=id
                    )
                )

            if not department:

                flash(
                    "Department is required.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "subjects.edit_subject",
                        id=id
                    )
                )

            if not teacher_id_raw:

                flash(
                    "Please select a teacher.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "subjects.edit_subject",
                        id=id
                    )
                )

            try:

                teacher_id = int(
                    teacher_id_raw
                )

            except (TypeError, ValueError):

                flash(
                    "Invalid teacher selected.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "subjects.edit_subject",
                        id=id
                    )
                )

            # ------------------------------------------------
            # CHECK TEACHER
            # ------------------------------------------------

            cursor.execute(
                """
                SELECT
                    id
                FROM teachers
                WHERE id = %s
                LIMIT 1
                """,
                (teacher_id,)
            )

            teacher = cursor.fetchone()

            if not teacher:

                flash(
                    "Selected teacher was not found.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "subjects.edit_subject",
                        id=id
                    )
                )

            # ------------------------------------------------
            # CHECK DUPLICATE CODE
            # ------------------------------------------------

            cursor.execute(
                """
                SELECT
                    id
                FROM subjects
                WHERE LOWER(
                    TRIM(subject_code)
                ) = LOWER(
                    TRIM(%s)
                )
                AND id != %s
                LIMIT 1
                """,
                (
                    subject_code,
                    id
                )
            )

            duplicate_subject = cursor.fetchone()

            if duplicate_subject:

                flash(
                    "Subject Code already exists!",
                    "danger"
                )

                return redirect(
                    url_for(
                        "subjects.edit_subject",
                        id=id
                    )
                )

            # ------------------------------------------------
            # UPDATE
            # ------------------------------------------------

            cursor.execute(
                """
                UPDATE subjects
                SET
                    subject_code = %s,
                    subject_name = %s,
                    semester = %s,
                    department = %s,
                    teacher_id = %s
                WHERE id = %s
                """,
                (
                    subject_code,
                    subject_name,
                    semester,
                    department,
                    teacher_id,
                    id
                )
            )

            mysql.connection.commit()

            flash(
                "Subject updated successfully!",
                "success"
            )

            return redirect(
                url_for(
                    "subjects.index"
                )
            )

        # ----------------------------------------------------
        # GET PAGE
        # ----------------------------------------------------

        return render_template(
            "admin/edit_subject.html",
            subject=subject,
            teachers=teachers
        )

    except Exception as e:

        try:
            mysql.connection.rollback()
        except Exception:
            pass

        print(
            "EDIT SUBJECT ERROR:",
            repr(e)
        )

        flash(
            f"Unable to update subject: {str(e)}",
            "danger"
        )

        return redirect(
            url_for(
                "subjects.index"
            )
        )

    finally:

        try:
            cursor.close()
        except Exception:
            pass


# ============================================================
# DELETE SUBJECT
# ============================================================

@subjects.route(
    "/delete/<int:id>",
    methods=["POST", "GET"]
)
def delete_subject(id):

    if not admin_required():
        flash(
            "Please login as administrator.",
            "warning"
        )
        return admin_login_redirect()

    cursor = mysql.connection.cursor()

    try:

        # ----------------------------------------------------
        # CHECK SUBJECT
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                id
            FROM subjects
            WHERE id = %s
            LIMIT 1
            """,
            (id,)
        )

        subject = cursor.fetchone()

        if not subject:

            flash(
                "Subject not found.",
                "warning"
            )

            return redirect(
                url_for(
                    "subjects.index"
                )
            )

        # ----------------------------------------------------
        # CHECK ATTENDANCE SESSIONS
        # ----------------------------------------------------

        try:

            cursor.execute(
                """
                SELECT
                    id
                FROM attendance_sessions
                WHERE subject_id = %s
                LIMIT 1
                """,
                (id,)
            )

            attendance_session = cursor.fetchone()

        except Exception:

            attendance_session = None

            try:
                mysql.connection.rollback()
            except Exception:
                pass

        if attendance_session:

            flash(
                "This subject cannot be deleted because attendance sessions already exist for it.",
                "warning"
            )

            return redirect(
                url_for(
                    "subjects.index"
                )
            )

        # ----------------------------------------------------
        # DELETE
        # ----------------------------------------------------

        cursor.execute(
            """
            DELETE FROM subjects
            WHERE id = %s
            """,
            (id,)
        )

        mysql.connection.commit()

        if cursor.rowcount > 0:

            flash(
                "Subject deleted successfully!",
                "success"
            )

        else:

            flash(
                "Subject not found.",
                "warning"
            )

        return redirect(
            url_for(
                "subjects.index"
            )
        )

    except Exception as e:

        try:
            mysql.connection.rollback()
        except Exception:
            pass

        print(
            "DELETE SUBJECT ERROR:",
            repr(e)
        )

        flash(
            f"Unable to delete subject: {str(e)}",
            "danger"
        )

        return redirect(
            url_for(
                "subjects.index"
            )
        )

    finally:

        try:
            cursor.close()
        except Exception:
            pass


# ============================================================
# SUBJECTS API
# ============================================================

@subjects.route("/api")
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

    cursor = mysql.connection.cursor()

    try:

        query = """
            SELECT
                s.id,
                s.subject_code,
                s.subject_name,
                s.semester,
                s.department,
                s.teacher_id,
                COALESCE(
                    t.full_name,
                    'Not Assigned'
                ) AS teacher_name
            FROM subjects s
            LEFT JOIN teachers t
                ON s.teacher_id = t.id
            WHERE 1 = 1
        """

        params = []

        # ----------------------------------------------------
        # SEMESTER FILTER
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # DEPARTMENT FILTER
        # ----------------------------------------------------

        if department:

            query += """
                AND LOWER(
                    TRIM(s.department)
                ) = LOWER(
                    TRIM(%s)
                )
            """

            params.append(
                department
            )

        # ----------------------------------------------------
        # ORDER
        # ----------------------------------------------------

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
                "teacher_name": (
                    row[6]
                    if row[6]
                    else "Not Assigned"
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

        try:
            cursor.close()
        except Exception:
            pass