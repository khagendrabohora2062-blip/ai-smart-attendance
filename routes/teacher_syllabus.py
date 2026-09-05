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
# TEACHER SYLLABUS BLUEPRINT
# ============================================================

teacher_syllabus = Blueprint(
    "teacher_syllabus",
    __name__,
    url_prefix="/teacher/syllabus"
)


# ============================================================
# HELPER: GET SYLLABUS FILE DATA
# ============================================================

def _get_syllabus_file_data(filename):
    """
    Get syllabus PDF from database using filename.
    Returns:
        file_data, file_path
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
# TEACHER SYLLABUS INDEX
# ============================================================

@teacher_syllabus.route("/")
def index():

    # --------------------------------------------------------
    # CHECK TEACHER LOGIN
    # --------------------------------------------------------

    if "teacher_id" not in session:
        flash("Please login as teacher to access syllabus.", "warning")
        return redirect(url_for("teacher_auth.login"))

    teacher_id = session.get("teacher_id")

    cur = mysql.connection.cursor()

    # --------------------------------------------------------
    # GET CURRENT TEACHER
    # --------------------------------------------------------

    cur.execute(
        """
        SELECT
            id,
            teacher_id,
            full_name,
            email,
            department
        FROM teachers
        WHERE teacher_id = %s
        LIMIT 1
        """,
        (teacher_id,)
    )

    teacher = cur.fetchone()

    if not teacher:
        cur.close()
        flash("Teacher record not found.", "danger")
        return redirect(url_for("teacher_auth.login"))

    department = teacher[4]

    # --------------------------------------------------------
    # GET SYLLABUS
    #
    # Teacher can view syllabus belonging to:
    # - Same department
    # - Subjects assigned to the teacher
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
          AND (
                sub.teacher_id = %s
                OR sub.teacher_id IS NULL
              )
        ORDER BY s.created_at DESC
        """,
        (department, teacher[0])
    )

    syllabi = cur.fetchall()

    cur.close()

    return render_template(
        "teacher/syllabus/index.html",
        teacher=teacher,
        syllabi=syllabi,
        department=department
    )


# ============================================================
# VIEW SYLLABUS PDF
# ============================================================

@teacher_syllabus.route("/view/<path:filename>")
def view(filename):

    # --------------------------------------------------------
    # CHECK TEACHER LOGIN
    # --------------------------------------------------------

    if "teacher_id" not in session:
        flash("Please login as teacher first.", "warning")
        return redirect(url_for("teacher_auth.login"))

    # --------------------------------------------------------
    # GET FILE
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

    return redirect(url_for("teacher_syllabus.index"))


# ============================================================
# DOWNLOAD SYLLABUS PDF
# ============================================================

@teacher_syllabus.route("/download/<path:filename>")
def download(filename):

    # --------------------------------------------------------
    # CHECK TEACHER LOGIN
    # --------------------------------------------------------

    if "teacher_id" not in session:
        flash("Please login as teacher first.", "warning")
        return redirect(url_for("teacher_auth.login"))

    # --------------------------------------------------------
    # GET FILE
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

    return redirect(url_for("teacher_syllabus.index"))