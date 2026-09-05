from flask import (
    Blueprint,
    session,
    redirect,
    url_for,
    flash,
    render_template,
    send_file
)

from io import BytesIO
import os

from extensions import mysql


# ============================================================
# STUDENT SYLLABUS BLUEPRINT
# ============================================================

student_syllabus = Blueprint(
    "student_syllabus",
    __name__,
    url_prefix="/student/syllabus"
)


# ============================================================
# HELPER: GET SYLLABUS FILE FROM DATABASE
# ============================================================

def _get_syllabus_file_data(filename):
    """
    Get syllabus PDF from database using stored filename.
    Returns file_data, file_path or (None, None).
    """

    cur = mysql.connection.cursor()

    cur.execute(
        """
        SELECT file_data, file_path
        FROM syllabus
        WHERE file_name = %s
        LIMIT 1
        """,
        (filename,)
    )

    result = cur.fetchone()
    cur.close()

    if not result:
        return None, None

    return result[0], result[1]


# ============================================================
# STUDENT SYLLABUS INDEX
# ============================================================

@student_syllabus.route("/")
def index():

    # --------------------------------------------------------
    # CHECK STUDENT LOGIN
    # --------------------------------------------------------

    if "student_id" not in session:
        flash("Please login as student to access syllabus.", "warning")
        return redirect(url_for("student_auth.login"))

    student_id = session.get("student_id")

    cur = mysql.connection.cursor()

    # --------------------------------------------------------
    # GET CURRENT STUDENT
    # --------------------------------------------------------

    cur.execute(
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
        WHERE student_id = %s
        LIMIT 1
        """,
        (student_id,)
    )

    student = cur.fetchone()

    if not student:
        cur.close()
        flash("Student record not found.", "danger")
        return redirect(url_for("student_auth.login"))

    department = student[4]
    semester = student[5]

    # --------------------------------------------------------
    # GET SYLLABUS FOR STUDENT
    # --------------------------------------------------------

    cur.execute(
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
            s.updated_at
        FROM syllabus s
        LEFT JOIN subjects sub
            ON s.subject_id = sub.id
        WHERE s.department = %s
          AND s.semester = %s
        ORDER BY s.created_at DESC
        """,
        (department, semester)
    )

    syllabi = cur.fetchall()

    cur.close()

    return render_template(
        "student/syllabus/index.html",
        student=student,
        syllabi=syllabi,
        department=department,
        semester=semester
    )


# ============================================================
# VIEW SYLLABUS PDF
# ============================================================

@student_syllabus.route("/view/<path:filename>")
def view(filename):

    # --------------------------------------------------------
    # CHECK STUDENT LOGIN
    # --------------------------------------------------------

    if "student_id" not in session:
        flash("Please login as student first.", "warning")
        return redirect(url_for("student_auth.login"))

    # --------------------------------------------------------
    # GET FILE FROM DATABASE
    # --------------------------------------------------------

    file_data, file_path = _get_syllabus_file_data(filename)

    # --------------------------------------------------------
    # DATABASE FILE AVAILABLE
    # --------------------------------------------------------

    if file_data:
        return send_file(
            BytesIO(bytes(file_data)),
            mimetype="application/pdf",
            as_attachment=False,
            download_name=filename
        )

    # --------------------------------------------------------
    # FALLBACK TO PHYSICAL FILE
    # --------------------------------------------------------

    if file_path:
        physical_path = file_path

        if not os.path.isabs(physical_path):
            physical_path = os.path.join(
                os.getcwd(),
                physical_path
            )

        if os.path.exists(physical_path):
            return send_file(
                physical_path,
                mimetype="application/pdf",
                as_attachment=False,
                download_name=filename
            )

    # --------------------------------------------------------
    # FILE NOT FOUND
    # --------------------------------------------------------

    flash(
        "Syllabus file not found. Please contact administrator.",
        "danger"
    )

    return redirect(url_for("student_syllabus.index"))


# ============================================================
# DOWNLOAD SYLLABUS PDF
# ============================================================

@student_syllabus.route("/download/<path:filename>")
def download(filename):

    # --------------------------------------------------------
    # CHECK STUDENT LOGIN
    # --------------------------------------------------------

    if "student_id" not in session:
        flash("Please login as student first.", "warning")
        return redirect(url_for("student_auth.login"))

    # --------------------------------------------------------
    # GET FILE FROM DATABASE
    # --------------------------------------------------------

    file_data, file_path = _get_syllabus_file_data(filename)

    # --------------------------------------------------------
    # DATABASE FILE AVAILABLE
    # --------------------------------------------------------

    if file_data:
        return send_file(
            BytesIO(bytes(file_data)),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename
        )

    # --------------------------------------------------------
    # FALLBACK TO PHYSICAL FILE
    # --------------------------------------------------------

    if file_path:
        physical_path = file_path

        if not os.path.isabs(physical_path):
            physical_path = os.path.join(
                os.getcwd(),
                physical_path
            )

        if os.path.exists(physical_path):
            return send_file(
                physical_path,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=filename
            )

    # --------------------------------------------------------
    # FILE NOT FOUND
    # --------------------------------------------------------

    flash(
        "Syllabus file not found. Please contact administrator.",
        "danger"
    )

    return redirect(url_for("student_syllabus.index"))