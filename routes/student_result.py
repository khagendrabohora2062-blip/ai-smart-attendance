from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    session,
    flash
)

from extensions import mysql


# ============================================================
# STUDENT RESULT BLUEPRINT
# ============================================================

student_result = Blueprint(
    "student_result",
    __name__,
    url_prefix="/student/results"
)


# ============================================================
# LOGIN CHECK
# ============================================================

def student_logged_in():
    return "student_db_id" in session


# ============================================================
# STUDENT RESULT
# ============================================================

@student_result.route("/")
def index():

    # --------------------------------------------------------
    # LOGIN CHECK
    # --------------------------------------------------------

    if not student_logged_in():
        return redirect(
            url_for("student_auth.login")
        )

    cursor = mysql.connection.cursor()

    student = None
    results = []

    try:

        # ====================================================
        # GET LOGGED-IN STUDENT
        # ====================================================

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
                session["student_db_id"],
            )
        )

        student = cursor.fetchone()

        if not student:

            session.clear()

            flash(
                "Student account not found.",
                "danger"
            )

            return redirect(
                url_for("student_auth.login")
            )


        # ====================================================
        # GET ONLY LOGGED-IN STUDENT'S RESULTS
        # ====================================================

        cursor.execute(
            """
            SELECT

                m.id,

                sub.subject_code,
                sub.subject_name,
                sub.semester,

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

            INNER JOIN subjects sub
                ON sub.id = m.subject_id

            WHERE m.student_id = %s

            ORDER BY
                sub.semester ASC,
                sub.subject_name ASC
            """,
            (
                session["student_db_id"],
            )
        )

        results = cursor.fetchall()


        # ====================================================
        # SUMMARY
        # ====================================================

        total_subjects = len(results)

        passed_subjects = 0
        failed_subjects = 0

        total_obtained = 0
        total_full = 0

        for result in results:

            total = float(
                result[10] or 0
            )

            full = float(
                result[6] or 0
            )

            pass_marks = float(
                result[7] or 0
            )

            total_obtained += total
            total_full += full

            if total >= pass_marks:
                passed_subjects += 1
            else:
                failed_subjects += 1


        # ====================================================
        # OVERALL PERCENTAGE
        # ====================================================

        percentage = 0

        if total_full > 0:

            percentage = round(
                (
                    total_obtained /
                    total_full
                ) * 100,
                2
            )


        return render_template(
            "student/results.html",

            student=student,
            results=results,

            total_subjects=total_subjects,
            passed_subjects=passed_subjects,
            failed_subjects=failed_subjects,

            total_obtained=total_obtained,
            total_full=total_full,

            percentage=percentage
        )


    except Exception as e:

        mysql.connection.rollback()

        print(
            "STUDENT RESULT ERROR:",
            repr(e)
        )

        flash(
            f"Unable to load results: {str(e)}",
            "danger"
        )

        return redirect(
            url_for(
                "student_auth.dashboard"
            )
        )

    finally:

        cursor.close()