from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    request,
    flash
)

from extensions import mysql
import uuid


# ============================================================
# BLUEPRINT
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
# GENERATE UNIQUE SUBJECT ID
# ============================================================

def generate_subject_id(cursor):
    """
    Generates a unique positive integer ID.

    Current database:
        subjects.id INT NOT NULL PRIMARY KEY

    AUTO_INCREMENT is not available, so ID is generated manually.
    """

    while True:

        new_id = uuid.uuid4().int % 2147483647

        if new_id <= 0:
            continue

        cursor.execute(
            """
            SELECT id
            FROM subjects
            WHERE id = %s
            LIMIT 1
            """,
            (new_id,)
        )

        if not cursor.fetchone():
            return new_id


# ============================================================
# SUBJECT LIST
# ============================================================

@subjects.route("/")
def index():

    if not admin_required():
        return redirect(url_for("auth.login"))

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
                t.full_name,
                s.theory_full_marks,
                s.practical_full_marks,
                s.full_marks,
                s.pass_marks
            FROM subjects s

            LEFT JOIN teachers t
                ON s.teacher_id = t.id

            ORDER BY s.id DESC
            """
        )

        subject_data = cursor.fetchall()

        return render_template(
            "admin/subjects.html",
            subjects=subject_data
        )

    except Exception as e:

        mysql.connection.rollback()

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

        cursor.close()


# ============================================================
# ADD SUBJECT
# ============================================================

@subjects.route(
    "/add",
    methods=["GET", "POST"]
)
def add_subject():

    if not admin_required():
        return redirect(url_for("auth.login"))

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
            ORDER BY full_name
            """
        )

        teachers = cursor.fetchall()

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

            semester = request.form.get(
                "semester",
                ""
            ).strip()

            department = request.form.get(
                "department",
                ""
            ).strip()

            teacher_id = request.form.get(
                "teacher_id",
                ""
            ).strip()

            theory_full_marks = request.form.get(
                "theory_full_marks",
                ""
            ).strip()

            practical_full_marks = request.form.get(
                "practical_full_marks",
                ""
            ).strip()

            pass_marks = request.form.get(
                "pass_marks",
                ""
            ).strip()

            # ------------------------------------------------
            # REQUIRED VALIDATION
            # ------------------------------------------------

            if not subject_code:

                flash(
                    "Subject Code is required.",
                    "danger"
                )

                return redirect(
                    url_for("subjects.add_subject")
                )

            if not subject_name:

                flash(
                    "Subject Name is required.",
                    "danger"
                )

                return redirect(
                    url_for("subjects.add_subject")
                )

            if not theory_full_marks:

                flash(
                    "Theory Full Marks is required.",
                    "danger"
                )

                return redirect(
                    url_for("subjects.add_subject")
                )

            if not practical_full_marks:

                flash(
                    "Practical Full Marks is required.",
                    "danger"
                )

                return redirect(
                    url_for("subjects.add_subject")
                )

            if not pass_marks:

                flash(
                    "Pass Marks is required.",
                    "danger"
                )

                return redirect(
                    url_for("subjects.add_subject")
                )

            # ------------------------------------------------
            # NUMBER VALIDATION
            # ------------------------------------------------

            try:

                theory = float(
                    theory_full_marks
                )

                practical = float(
                    practical_full_marks
                )

                pass_mark = float(
                    pass_marks
                )

            except (ValueError, TypeError):

                flash(
                    "Full marks and pass marks must be valid numbers.",
                    "danger"
                )

                return redirect(
                    url_for("subjects.add_subject")
                )

            # ------------------------------------------------
            # MARK VALIDATION
            # ------------------------------------------------

            if theory <= 0:

                flash(
                    "Theory Full Marks must be greater than 0.",
                    "danger"
                )

                return redirect(
                    url_for("subjects.add_subject")
                )

            if practical < 0:

                flash(
                    "Practical Full Marks cannot be negative.",
                    "danger"
                )

                return redirect(
                    url_for("subjects.add_subject")
                )

            full_marks = theory + practical

            if full_marks <= 0:

                flash(
                    "Total Full Marks must be greater than 0.",
                    "danger"
                )

                return redirect(
                    url_for("subjects.add_subject")
                )

            if pass_mark < 0 or pass_mark > full_marks:

                flash(
                    "Pass Marks must be between 0 and Total Full Marks.",
                    "danger"
                )

                return redirect(
                    url_for("subjects.add_subject")
                )

            # ------------------------------------------------
            # CHECK DUPLICATE SUBJECT CODE
            # ------------------------------------------------

            cursor.execute(
                """
                SELECT id
                FROM subjects
                WHERE subject_code = %s
                LIMIT 1
                """,
                (subject_code,)
            )

            if cursor.fetchone():

                flash(
                    "Subject Code already exists!",
                    "danger"
                )

                return redirect(
                    url_for("subjects.add_subject")
                )

            # ------------------------------------------------
            # VALIDATE TEACHER
            # ------------------------------------------------

            teacher_value = None

            if teacher_id:

                try:

                    teacher_value = int(
                        teacher_id
                    )

                except (ValueError, TypeError):

                    flash(
                        "Invalid teacher selected.",
                        "danger"
                    )

                    return redirect(
                        url_for("subjects.add_subject")
                    )

                cursor.execute(
                    """
                    SELECT id
                    FROM teachers
                    WHERE id = %s
                    LIMIT 1
                    """,
                    (teacher_value,)
                )

                if not cursor.fetchone():

                    flash(
                        "Selected teacher does not exist.",
                        "danger"
                    )

                    return redirect(
                        url_for("subjects.add_subject")
                    )

            # ------------------------------------------------
            # GENERATE MANUAL ID
            # ------------------------------------------------

            subject_id = generate_subject_id(
                cursor
            )

            # ------------------------------------------------
            # INSERT SUBJECT
            #
            # IMPORTANT:
            # Each database column appears ONLY ONCE.
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
                    teacher_id,

                    theory_internal_full_marks,
                    theory_external_full_marks,

                    practical_internal_full_marks,
                    practical_external_full_marks,

                    theory_full_marks,
                    practical_full_marks,

                    full_marks,
                    pass_marks,

                    internal_theory_full_marks,
                    internal_practical_full_marks,

                    external_theory_full_marks,
                    external_practical_full_marks
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
                    subject_id,
                    subject_code,
                    subject_name,
                    semester,
                    department,
                    teacher_value,

                    # Theory internal/external
                    theory,
                    theory,

                    # Practical internal/external
                    practical,
                    practical,

                    # Main full marks
                    theory,
                    practical,

                    # Total/pass
                    full_marks,
                    pass_mark,

                    # Internal marks
                    theory,
                    practical,

                    # External marks
                    theory,
                    practical
                )
            )

            mysql.connection.commit()

            flash(
                "Subject added successfully!",
                "success"
            )

            return redirect(
                url_for("subjects.index")
            )

        # ----------------------------------------------------
        # GET
        # ----------------------------------------------------

        return render_template(
            "admin/add_subject.html",
            teachers=teachers
        )

    except Exception as e:

        mysql.connection.rollback()

        print(
            "ADD SUBJECT ERROR:",
            repr(e)
        )

        flash(
            f"Unable to add subject: {str(e)}",
            "danger"
        )

        return redirect(
            url_for("subjects.index")
        )

    finally:

        cursor.close()


# ============================================================
# EDIT SUBJECT
# ============================================================

@subjects.route(
    "/edit/<int:id>",
    methods=["GET", "POST"]
)
def edit_subject(id):

    if not admin_required():
        return redirect(url_for("auth.login"))

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
            ORDER BY full_name
            """
        )

        teachers = cursor.fetchall()

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

            semester = request.form.get(
                "semester",
                ""
            ).strip()

            department = request.form.get(
                "department",
                ""
            ).strip()

            teacher_id = request.form.get(
                "teacher_id",
                ""
            ).strip()

            theory_full_marks = request.form.get(
                "theory_full_marks",
                ""
            ).strip()

            practical_full_marks = request.form.get(
                "practical_full_marks",
                ""
            ).strip()

            pass_marks = request.form.get(
                "pass_marks",
                ""
            ).strip()

            # ------------------------------------------------
            # REQUIRED VALIDATION
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

            if not theory_full_marks:

                flash(
                    "Theory Full Marks is required.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "subjects.edit_subject",
                        id=id
                    )
                )

            if not practical_full_marks:

                flash(
                    "Practical Full Marks is required.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "subjects.edit_subject",
                        id=id
                    )
                )

            if not pass_marks:

                flash(
                    "Pass Marks is required.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "subjects.edit_subject",
                        id=id
                    )
                )

            # ------------------------------------------------
            # NUMBER VALIDATION
            # ------------------------------------------------

            try:

                theory = float(
                    theory_full_marks
                )

                practical = float(
                    practical_full_marks
                )

                pass_mark = float(
                    pass_marks
                )

            except (ValueError, TypeError):

                flash(
                    "Full marks and pass marks must be valid numbers.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "subjects.edit_subject",
                        id=id
                    )
                )

            # ------------------------------------------------
            # MARK VALIDATION
            # ------------------------------------------------

            if theory <= 0:

                flash(
                    "Theory Full Marks must be greater than 0.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "subjects.edit_subject",
                        id=id
                    )
                )

            if practical < 0:

                flash(
                    "Practical Full Marks cannot be negative.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "subjects.edit_subject",
                        id=id
                    )
                )

            full_marks = theory + practical

            if full_marks <= 0:

                flash(
                    "Total Full Marks must be greater than 0.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "subjects.edit_subject",
                        id=id
                    )
                )

            if pass_mark < 0 or pass_mark > full_marks:

                flash(
                    "Pass Marks must be between 0 and Total Full Marks.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "subjects.edit_subject",
                        id=id
                    )
                )

            # ------------------------------------------------
            # CHECK DUPLICATE SUBJECT CODE
            # ------------------------------------------------

            cursor.execute(
                """
                SELECT id
                FROM subjects
                WHERE subject_code = %s
                  AND id != %s
                LIMIT 1
                """,
                (
                    subject_code,
                    id
                )
            )

            if cursor.fetchone():

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
            # VALIDATE TEACHER
            # ------------------------------------------------

            teacher_value = None

            if teacher_id:

                try:

                    teacher_value = int(
                        teacher_id
                    )

                except (ValueError, TypeError):

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

                cursor.execute(
                    """
                    SELECT id
                    FROM teachers
                    WHERE id = %s
                    LIMIT 1
                    """,
                    (teacher_value,)
                )

                if not cursor.fetchone():

                    flash(
                        "Selected teacher does not exist.",
                        "danger"
                    )

                    return redirect(
                        url_for(
                            "subjects.edit_subject",
                            id=id
                        )
                    )

            # ------------------------------------------------
            # CHECK SUBJECT EXISTS
            # ------------------------------------------------

            cursor.execute(
                """
                SELECT id
                FROM subjects
                WHERE id = %s
                LIMIT 1
                """,
                (id,)
            )

            if not cursor.fetchone():

                flash(
                    "Subject not found.",
                    "warning"
                )

                return redirect(
                    url_for("subjects.index")
                )

            # ------------------------------------------------
            # UPDATE SUBJECT
            # ------------------------------------------------

            cursor.execute(
                """
                UPDATE subjects

                SET
                    subject_code = %s,
                    subject_name = %s,
                    semester = %s,
                    department = %s,
                    teacher_id = %s,

                    theory_internal_full_marks = %s,
                    theory_external_full_marks = %s,

                    practical_internal_full_marks = %s,
                    practical_external_full_marks = %s,

                    theory_full_marks = %s,
                    practical_full_marks = %s,

                    full_marks = %s,
                    pass_marks = %s,

                    internal_theory_full_marks = %s,
                    internal_practical_full_marks = %s,

                    external_theory_full_marks = %s,
                    external_practical_full_marks = %s

                WHERE id = %s
                """,
                (
                    subject_code,
                    subject_name,
                    semester,
                    department,
                    teacher_value,

                    # Theory internal/external
                    theory,
                    theory,

                    # Practical internal/external
                    practical,
                    practical,

                    # Main full marks
                    theory,
                    practical,

                    # Total/pass
                    full_marks,
                    pass_mark,

                    # Internal
                    theory,
                    practical,

                    # External
                    theory,
                    practical,

                    # Subject ID
                    id
                )
            )

            mysql.connection.commit()

            flash(
                "Subject updated successfully!",
                "success"
            )

            return redirect(
                url_for("subjects.index")
            )

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
                teacher_id,

                theory_internal_full_marks,
                theory_external_full_marks,

                practical_internal_full_marks,
                practical_external_full_marks,

                theory_full_marks,
                practical_full_marks,

                full_marks,
                pass_marks,

                internal_theory_full_marks,
                internal_practical_full_marks,

                external_theory_full_marks,
                external_practical_full_marks

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
                url_for("subjects.index")
            )

        return render_template(
            "admin/edit_subject.html",
            subject=subject,
            teachers=teachers
        )

    except Exception as e:

        mysql.connection.rollback()

        print(
            "EDIT SUBJECT ERROR:",
            repr(e)
        )

        flash(
            f"Unable to update subject: {str(e)}",
            "danger"
        )

        return redirect(
            url_for("subjects.index")
        )

    finally:

        cursor.close()


# ============================================================
# DELETE SUBJECT
# ============================================================

@subjects.route(
    "/delete/<int:id>",
    methods=["POST", "GET"]
)
def delete_subject(id):

    if not admin_required():
        return redirect(url_for("auth.login"))

    cursor = mysql.connection.cursor()

    try:

        # ----------------------------------------------------
        # CHECK SUBJECT
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT id
            FROM subjects
            WHERE id = %s
            LIMIT 1
            """,
            (id,)
        )

        if not cursor.fetchone():

            flash(
                "Subject not found.",
                "warning"
            )

            return redirect(
                url_for("subjects.index")
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

        flash(
            "Subject deleted successfully!",
            "success"
        )

        return redirect(
            url_for("subjects.index")
        )

    except Exception as e:

        mysql.connection.rollback()

        print(
            "DELETE SUBJECT ERROR:",
            repr(e)
        )

        flash(
            f"Unable to delete subject: {str(e)}",
            "danger"
        )

        return redirect(
            url_for("subjects.index")
        )

    finally:

        cursor.close()