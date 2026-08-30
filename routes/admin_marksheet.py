
from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    session,
    current_app,
    request
)

admin_marksheet = Blueprint(
    "admin_marksheet",
    __name__,
    url_prefix="/admin/marksheets"
)


# ============================================================
# MYSQL CONNECTION
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
        print("ADMIN MARKSHEET MYSQL ERROR:", repr(e))

    raise RuntimeError(
        "MySQL connection is not initialized."
    )


# ============================================================
# ADMIN LOGIN CHECK
# ============================================================

def admin_required():
    return bool(
        session.get("admin_id")
        or session.get("admin_logged_in")
        or session.get("admin")
    )


# ============================================================
# GRADE CALCULATION
# ============================================================

def calculate_grade(total_marks, full_marks):

    if full_marks <= 0:
        return "F", 0.00

    percentage = (
        float(total_marks) / float(full_marks)
    ) * 100

    if percentage >= 90:
        return "A+", 4.00

    elif percentage >= 80:
        return "A", 3.60

    elif percentage >= 70:
        return "B+", 3.20

    elif percentage >= 60:
        return "B", 2.80

    elif percentage >= 50:
        return "C+", 2.40

    elif percentage >= 40:
        return "C", 2.00

    else:
        return "F", 0.00


# ============================================================
# MARKSHEET LIST
# ============================================================

@admin_marksheet.route("/")
def index():

    if not admin_required():
        flash(
            "Please login as administrator.",
            "warning"
        )

        return redirect(
            url_for("admin_auth.login")
        )

    mysql = get_mysql()
    cursor = mysql.connection.cursor()

    try:

        cursor.execute("""
            SELECT
                m.id,
                s.student_id,
                s.full_name,
                s.department,
                s.semester,

                sub.subject_code,
                sub.subject_name,
                sub.theory_full_marks,
                sub.practical_full_marks,
                sub.full_marks,
                sub.pass_marks,

                m.theory_marks,
                m.practical_marks,
                m.total_marks,
                m.grade,
                m.grade_point,
                m.remarks,
                m.created_at,
                m.updated_at

            FROM marksheets m

            INNER JOIN students s
                ON s.id = m.student_id

            INNER JOIN subjects sub
                ON sub.id = m.subject_id

            ORDER BY
                s.full_name ASC,
                sub.subject_name ASC
        """)

        raw_marksheets = cursor.fetchall()

        marksheets = []

        for mark in raw_marksheets:

            mark = list(mark)

            # SUBJECT FULL MARKS
            mark[7] = float(mark[7] or 0)
            mark[8] = float(mark[8] or 0)
            mark[9] = float(mark[9] or 0)
            mark[10] = float(mark[10] or 0)

            # STUDENT MARKS
            mark[11] = float(mark[11] or 0)
            mark[12] = float(mark[12] or 0)
            mark[13] = float(mark[13] or 0)

            # GRADE POINT
            if mark[15] is not None:
                mark[15] = float(mark[15])

            marksheets.append(tuple(mark))

        return render_template(
            "admin/marksheets/index.html",
            marksheets=marksheets
        )

    except Exception as e:

        print(
            "ADMIN MARKSHEET INDEX ERROR:",
            repr(e)
        )

        flash(
            f"Unable to load marksheets: {str(e)}",
            "danger"
        )

        return redirect(
            url_for("admin.dashboard")
        )

    finally:
        cursor.close()


# ============================================================
# ADD MARKS
# ============================================================

@admin_marksheet.route(
    "/add",
    methods=["GET", "POST"]
)
def add():

    if not admin_required():

        flash(
            "Please login as administrator.",
            "warning"
        )

        return redirect(
            url_for("admin_auth.login")
        )

    mysql = get_mysql()
    cursor = mysql.connection.cursor()

    try:

        # ====================================================
        # POST
        # ====================================================

        if request.method == "POST":

            student_id = request.form.get(
                "student_id",
                ""
            ).strip()

            subject_id = request.form.get(
                "subject_id",
                ""
            ).strip()

            theory_marks = request.form.get(
                "theory_marks",
                "0"
            ).strip()

            practical_marks = request.form.get(
                "practical_marks",
                "0"
            ).strip()

            remarks = request.form.get(
                "remarks",
                ""
            ).strip()

            # ------------------------------------------------
            # REQUIRED
            # ------------------------------------------------

            if not student_id or not subject_id:

                flash(
                    "Student and subject are required.",
                    "danger"
                )

                return redirect(
                    url_for("admin_marksheet.add")
                )

            # ------------------------------------------------
            # CHECK STUDENT
            # ------------------------------------------------

            cursor.execute("""
                SELECT
                    id,
                    student_id,
                    full_name,
                    department,
                    semester
                FROM students
                WHERE id = %s
                LIMIT 1
            """, (student_id,))

            student = cursor.fetchone()

            if not student:

                flash(
                    "Selected student was not found.",
                    "danger"
                )

                return redirect(
                    url_for("admin_marksheet.add")
                )

            # ------------------------------------------------
            # GET SUBJECT CONFIGURATION
            # ------------------------------------------------

            cursor.execute("""
                SELECT
                    id,
                    subject_code,
                    subject_name,
                    theory_full_marks,
                    practical_full_marks,
                    full_marks,
                    pass_marks
                FROM subjects
                WHERE id = %s
                LIMIT 1
            """, (subject_id,))

            subject = cursor.fetchone()

            if not subject:

                flash(
                    "Selected subject was not found.",
                    "danger"
                )

                return redirect(
                    url_for("admin_marksheet.add")
                )

            # ------------------------------------------------
            # SUBJECT CONFIG
            # ------------------------------------------------

            theory_full = float(
                subject[3] or 0
            )

            practical_full = float(
                subject[4] or 0
            )

            total_full = (
                theory_full +
                practical_full
            )

            pass_mark = float(
                subject[6] or 0
            )

            # ------------------------------------------------
            # VALIDATE CONFIGURATION
            # ------------------------------------------------

            if theory_full < 0:

                flash(
                    "Theory full marks cannot be negative.",
                    "danger"
                )

                return redirect(
                    url_for("admin_marksheet.add")
                )

            if practical_full < 0:

                flash(
                    "Practical full marks cannot be negative.",
                    "danger"
                )

                return redirect(
                    url_for("admin_marksheet.add")
                )

            if total_full <= 0:

                flash(
                    "Subject total full marks must be greater than 0.",
                    "danger"
                )

                return redirect(
                    url_for("admin_marksheet.add")
                )

            if pass_mark < 0 or pass_mark > total_full:

                flash(
                    f"Pass marks must be between 0 and {total_full:g}.",
                    "danger"
                )

                return redirect(
                    url_for("admin_marksheet.add")
                )

            # ------------------------------------------------
            # MARK CONVERSION
            # ------------------------------------------------

            try:

                theory = float(
                    theory_marks or 0
                )

                practical = float(
                    practical_marks or 0
                )

            except ValueError:

                flash(
                    "Student marks must be valid numbers.",
                    "danger"
                )

                return redirect(
                    url_for("admin_marksheet.add")
                )

            # ------------------------------------------------
            # THEORY VALIDATION
            # ------------------------------------------------

            if theory < 0:

                flash(
                    "Theory marks cannot be negative.",
                    "danger"
                )

                return redirect(
                    url_for("admin_marksheet.add")
                )

            if theory > theory_full:

                flash(
                    f"Theory marks cannot exceed {theory_full:g}.",
                    "danger"
                )

                return redirect(
                    url_for("admin_marksheet.add")
                )

            # ------------------------------------------------
            # PRACTICAL VALIDATION
            # ------------------------------------------------

            if practical < 0:

                flash(
                    "Practical marks cannot be negative.",
                    "danger"
                )

                return redirect(
                    url_for("admin_marksheet.add")
                )

            if practical > practical_full:

                flash(
                    f"Practical marks cannot exceed {practical_full:g}.",
                    "danger"
                )

                return redirect(
                    url_for("admin_marksheet.add")
                )

            # ------------------------------------------------
            # TOTAL
            # ------------------------------------------------

            total = theory + practical

            if total > total_full:

                flash(
                    f"Total marks cannot exceed {total_full:g}.",
                    "danger"
                )

                return redirect(
                    url_for("admin_marksheet.add")
                )

            # ------------------------------------------------
            # GRADE
            # ------------------------------------------------

            grade, grade_point = calculate_grade(
                total,
                total_full
            )

            # ------------------------------------------------
            # PASS / FAIL
            # ------------------------------------------------

            if total >= pass_mark:
                result_status = "Pass"
            else:
                result_status = "Fail"

            # ------------------------------------------------
            # DUPLICATE CHECK
            # ------------------------------------------------

            cursor.execute("""
                SELECT id
                FROM marksheets
                WHERE student_id = %s
                  AND subject_id = %s
                LIMIT 1
            """, (
                student_id,
                subject_id
            ))

            existing = cursor.fetchone()

            if existing:

                flash(
                    "Marks for this student and subject already exist.",
                    "warning"
                )

                return redirect(
                    url_for("admin_marksheet.add")
                )

            # =================================================
            # IMPORTANT:
            # marksheets.id HAS NO AUTO_INCREMENT
            #
            # So manually generate next ID.
            # =================================================

            cursor.execute("""
                SELECT COALESCE(MAX(id), 0) + 1
                FROM marksheets
            """)

            next_id_result = cursor.fetchone()

            next_id = int(
                next_id_result[0]
            )

            # ------------------------------------------------
            # INSERT
            # ------------------------------------------------

            cursor.execute("""
                INSERT INTO marksheets
                (
                    id,
                    student_id,
                    subject_id,

                    internal_theory_marks,
                    internal_practical_marks,
                    external_theory_marks,
                    external_practical_marks,

                    theory_marks,
                    practical_marks,
                    total_marks,
                    grade,
                    grade_point,
                    remarks
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
                    %s
                )
            """, (

                next_id,

                student_id,
                subject_id,

                # Existing internal/external columns
                # are kept at 0 because this form uses
                # combined theory/practical marks.

                0,
                0,
                0,
                0,

                theory,
                practical,
                total,
                grade,
                grade_point,

                remarks if remarks else result_status
            ))

            mysql.connection.commit()

            flash(
                "Student marks added successfully.",
                "success"
            )

            return redirect(
                url_for("admin_marksheet.index")
            )

        # ====================================================
        # GET - STUDENTS
        # ====================================================

        cursor.execute("""
            SELECT
                id,
                student_id,
                full_name,
                department,
                semester
            FROM students
            ORDER BY
                semester ASC,
                department ASC,
                full_name ASC
        """)

        students = cursor.fetchall()

        # ====================================================
        # GET - SUBJECTS
        # ====================================================

        cursor.execute("""
            SELECT
                id,
                subject_code,
                subject_name,
                semester,
                department,
                theory_full_marks,
                practical_full_marks,
                full_marks,
                pass_marks
            FROM subjects
            ORDER BY
                semester ASC,
                department ASC,
                subject_name ASC
        """)

        subjects = cursor.fetchall()

        return render_template(
            "admin/marksheets/add.html",
            students=students,
            subjects=subjects
        )

    except Exception as e:

        mysql.connection.rollback()

        print(
            "ADMIN MARKSHEET ADD ERROR:",
            repr(e)
        )

        flash(
            f"Unable to add marks: {str(e)}",
            "danger"
        )

        return redirect(
            url_for("admin_marksheet.index")
        )

    finally:
        cursor.close()


# ============================================================
# EDIT MARKS
# ============================================================

@admin_marksheet.route(
    "/edit/<int:marksheet_id>",
    methods=["GET", "POST"]
)
def edit(marksheet_id):

    if not admin_required():

        flash(
            "Please login as administrator.",
            "warning"
        )

        return redirect(
            url_for("admin_auth.login")
        )

    mysql = get_mysql()
    cursor = mysql.connection.cursor()

    try:

        # ====================================================
        # GET CURRENT MARKSHEET
        # ====================================================

        cursor.execute("""
            SELECT

                m.id,
                m.student_id,
                m.subject_id,

                s.student_id,
                s.full_name,
                s.department,
                s.semester,

                sub.subject_code,
                sub.subject_name,
                sub.theory_full_marks,
                sub.practical_full_marks,
                sub.full_marks,
                sub.pass_marks,

                m.theory_marks,
                m.practical_marks,
                m.total_marks,
                m.grade,
                m.grade_point,
                m.remarks

            FROM marksheets m

            INNER JOIN students s
                ON s.id = m.student_id

            INNER JOIN subjects sub
                ON sub.id = m.subject_id

            WHERE m.id = %s

            LIMIT 1
        """, (marksheet_id,))

        marksheet = cursor.fetchone()

        if not marksheet:

            flash(
                "Marksheet record not found.",
                "warning"
            )

            return redirect(
                url_for("admin_marksheet.index")
            )

        # ====================================================
        # POST
        # ====================================================

        if request.method == "POST":

            theory_marks = request.form.get(
                "theory_marks",
                "0"
            ).strip()

            practical_marks = request.form.get(
                "practical_marks",
                "0"
            ).strip()

            remarks = request.form.get(
                "remarks",
                ""
            ).strip()

            # ------------------------------------------------
            # SUBJECT CONFIG
            # ------------------------------------------------

            theory_full = float(
                marksheet[9] or 0
            )

            practical_full = float(
                marksheet[10] or 0
            )

            total_full = (
                theory_full +
                practical_full
            )

            pass_mark = float(
                marksheet[12] or 0
            )

            # ------------------------------------------------
            # CONVERT
            # ------------------------------------------------

            try:

                theory = float(
                    theory_marks or 0
                )

                practical = float(
                    practical_marks or 0
                )

            except ValueError:

                flash(
                    "Marks must be valid numbers.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "admin_marksheet.edit",
                        marksheet_id=marksheet_id
                    )
                )

            # ------------------------------------------------
            # THEORY
            # ------------------------------------------------

            if theory < 0 or theory > theory_full:

                flash(
                    f"Theory marks must be between 0 and {theory_full:g}.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "admin_marksheet.edit",
                        marksheet_id=marksheet_id
                    )
                )

            # ------------------------------------------------
            # PRACTICAL
            # ------------------------------------------------

            if practical < 0 or practical > practical_full:

                flash(
                    f"Practical marks must be between 0 and {practical_full:g}.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "admin_marksheet.edit",
                        marksheet_id=marksheet_id
                    )
                )

            # ------------------------------------------------
            # TOTAL
            # ------------------------------------------------

            total = theory + practical

            if total > total_full:

                flash(
                    f"Total marks cannot exceed {total_full:g}.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "admin_marksheet.edit",
                        marksheet_id=marksheet_id
                    )
                )

            # ------------------------------------------------
            # GRADE
            # ------------------------------------------------

            grade, grade_point = calculate_grade(
                total,
                total_full
            )

            # ------------------------------------------------
            # PASS / FAIL
            # ------------------------------------------------

            if total >= pass_mark:
                result_status = "Pass"
            else:
                result_status = "Fail"

            # ------------------------------------------------
            # UPDATE
            # ------------------------------------------------

            cursor.execute("""
                UPDATE marksheets

                SET
                    theory_marks = %s,
                    practical_marks = %s,
                    total_marks = %s,
                    grade = %s,
                    grade_point = %s,
                    remarks = %s

                WHERE id = %s
            """, (

                theory,
                practical,
                total,
                grade,
                grade_point,

                remarks if remarks else result_status,

                marksheet_id
            ))

            mysql.connection.commit()

            flash(
                "Student marks updated successfully.",
                "success"
            )

            return redirect(
                url_for("admin_marksheet.index")
            )

        # ====================================================
        # GET PAGE
        # ====================================================

        return render_template(
            "admin/marksheets/edit.html",
            marksheet=marksheet
        )

    except Exception as e:

        mysql.connection.rollback()

        print(
            "ADMIN MARKSHEET EDIT ERROR:",
            repr(e)
        )

        flash(
            f"Unable to edit marks: {str(e)}",
            "danger"
        )

        return redirect(
            url_for("admin_marksheet.index")
        )

    finally:
        cursor.close()


# ============================================================
# DELETE MARKS
# ============================================================

@admin_marksheet.route(
    "/delete/<int:marksheet_id>",
    methods=["POST"]
)
def delete(marksheet_id):

    if not admin_required():

        flash(
            "Please login as administrator.",
            "warning"
        )

        return redirect(
            url_for("admin_auth.login")
        )

    mysql = get_mysql()
    cursor = mysql.connection.cursor()

    try:

        cursor.execute("""
            DELETE FROM marksheets
            WHERE id = %s
        """, (marksheet_id,))

        mysql.connection.commit()

        if cursor.rowcount > 0:

            flash(
                "Marks deleted successfully.",
                "success"
            )

        else:

            flash(
                "Marksheet record was not found.",
                "warning"
            )

        return redirect(
            url_for("admin_marksheet.index")
        )

    except Exception as e:

        mysql.connection.rollback()

        print(
            "ADMIN MARKSHEET DELETE ERROR:",
            repr(e)
        )

        flash(
            f"Unable to delete marks: {str(e)}",
            "danger"
        )

        return redirect(
            url_for("admin_marksheet.index")
        )

    finally:
        cursor.close()

