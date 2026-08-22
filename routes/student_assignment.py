from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    current_app,
    send_from_directory
)

from extensions import mysql
from werkzeug.utils import secure_filename

import os
import uuid


# ============================================================
# BLUEPRINT
# ============================================================

student_assignment = Blueprint(
    "student_assignment",
    __name__,
    url_prefix="/student/assignments"
)


# ============================================================
# ALLOWED FILE TYPES
# ============================================================

ASSIGNMENT_ALLOWED_EXTENSIONS = {
    "pdf",
    "doc",
    "docx",
    "txt",
    "jpg",
    "jpeg",
    "png",
    "webp"
}

SUBMISSION_ALLOWED_EXTENSIONS = {
    "pdf",
    "doc",
    "docx",
    "txt",
    "jpg",
    "jpeg",
    "png",
    "webp",
    "zip"
}


# ============================================================
# LOGIN CHECK
# ============================================================

def student_logged_in():
    return "student_db_id" in session


# ============================================================
# FILE VALIDATION
# ============================================================

def allowed_assignment_file(filename):

    return (
        filename
        and "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ASSIGNMENT_ALLOWED_EXTENSIONS
    )


def allowed_submission_file(filename):

    return (
        filename
        and "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in SUBMISSION_ALLOWED_EXTENSIONS
    )


# ============================================================
# ASSIGNMENT UPLOAD FOLDER
# ============================================================

def assignment_upload_folder():

    folder = os.path.join(
        current_app.root_path,
        "static",
        "uploads",
        "assignments"
    )

    os.makedirs(
        folder,
        exist_ok=True
    )

    return folder


# ============================================================
# SUBMISSION UPLOAD FOLDER
# ============================================================

def submission_upload_folder():

    folder = os.path.join(
        current_app.root_path,
        "static",
        "uploads",
        "assignment_submissions"
    )

    os.makedirs(
        folder,
        exist_ok=True
    )

    return folder


# ============================================================
# GET LOGGED-IN STUDENT
# ============================================================

def get_student(cursor):

    student_db_id = session.get(
        "student_db_id"
    )

    cursor.execute(
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
        WHERE id = %s
        LIMIT 1
        """,
        (
            student_db_id,
        )
    )

    return cursor.fetchone()


# ============================================================
# ASSIGNMENT LIST
# ============================================================

@student_assignment.route("/")
def index():

    if not student_logged_in():

        return redirect(
            url_for("student_auth.login")
        )

    cursor = mysql.connection.cursor()

    assignments = []
    student = None

    try:

        # ----------------------------------------------------
        # STUDENT
        # ----------------------------------------------------

        student = get_student(cursor)

        if not student:

            session.clear()

            flash(
                "Student account not found.",
                "danger"
            )

            return redirect(
                url_for("student_auth.login")
            )

        student_id = student[0]
        student_department = student[4]
        student_semester = student[5]

        # ----------------------------------------------------
        # ASSIGNMENTS
        # ----------------------------------------------------
        # IMPORTANT:
        # Use a.attachment
        # NOT a.file_name
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                a.id,
                a.title,
                a.description,
                a.total_marks,
                a.due_date,
                a.due_time,
                a.attachment,
                a.status,
                a.created_at,

                s.id AS subject_id,
                s.subject_code,
                s.subject_name,
                s.semester,

                t.full_name AS teacher_name

            FROM assignments a

            INNER JOIN subjects s
                ON a.subject_id = s.id

            LEFT JOIN teachers t
                ON a.teacher_id = t.id

            WHERE
                a.status = 'ACTIVE'

                AND s.semester = %s

                AND LOWER(TRIM(s.department))
                    = LOWER(TRIM(%s))

            ORDER BY
                a.due_date ASC,
                a.due_time ASC,
                a.created_at DESC
            """,
            (
                student_semester,
                student_department
            )
        )

        assignment_rows = cursor.fetchall()

        # ----------------------------------------------------
        # SUBMISSION INFORMATION
        # ----------------------------------------------------

        for assignment in assignment_rows:

            assignment_id = assignment[0]

            cursor.execute(
                """
                SELECT
                    id,
                    answer,
                    attachment,
                    submitted_at,
                    marks,
                    feedback,
                    status

                FROM assignment_submissions

                WHERE
                    assignment_id = %s
                    AND student_id = %s

                LIMIT 1
                """,
                (
                    assignment_id,
                    student_id
                )
            )

            submission = cursor.fetchone()

            assignments.append({

                "id": assignment[0],

                "title": assignment[1],

                "description": assignment[2],

                "total_marks": assignment[3],

                "due_date": assignment[4],

                "due_time": assignment[5],

                "attachment": assignment[6],

                "status": assignment[7],

                "created_at": assignment[8],

                "subject_id": assignment[9],

                "subject_code": assignment[10],

                "subject_name": assignment[11],

                "semester": assignment[12],

                "teacher_name": (
                    assignment[13]
                    if assignment[13]
                    else "Not Assigned"
                ),

                "submission": submission
            })

    except Exception as e:

        mysql.connection.rollback()

        flash(
            f"Unable to load assignments: {e}",
            "danger"
        )

    finally:

        cursor.close()

    return render_template(
        "student/assignments.html",
        assignments=assignments,
        student=student
    )


# ============================================================
# VIEW ASSIGNMENT
# ============================================================

@student_assignment.route(
    "/view/<int:assignment_id>"
)
def view_assignment(assignment_id):

    if not student_logged_in():

        return redirect(
            url_for("student_auth.login")
        )

    cursor = mysql.connection.cursor()

    assignment = None
    submission = None
    student = None

    try:

        # ----------------------------------------------------
        # STUDENT
        # ----------------------------------------------------

        student = get_student(cursor)

        if not student:

            flash(
                "Student account not found.",
                "danger"
            )

            return redirect(
                url_for("student_auth.login")
            )

        student_id = student[0]

        # ----------------------------------------------------
        # ASSIGNMENT
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                a.id,
                a.title,
                a.description,
                a.total_marks,
                a.due_date,
                a.due_time,
                a.attachment,
                a.status,
                a.created_at,

                s.subject_code,
                s.subject_name,
                s.semester,

                t.full_name AS teacher_name

            FROM assignments a

            INNER JOIN subjects s
                ON a.subject_id = s.id

            LEFT JOIN teachers t
                ON a.teacher_id = t.id

            WHERE
                a.id = %s

                AND a.status = 'ACTIVE'

                AND s.semester = %s

                AND LOWER(TRIM(s.department))
                    = LOWER(TRIM(%s))

            LIMIT 1
            """,
            (
                assignment_id,
                student[5],
                student[4]
            )
        )

        assignment = cursor.fetchone()

        if not assignment:

            flash(
                "Assignment not found or not available for you.",
                "danger"
            )

            return redirect(
                url_for("student_assignment.index")
            )

        # ----------------------------------------------------
        # EXISTING SUBMISSION
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                answer,
                attachment,
                submitted_at,
                marks,
                feedback,
                status

            FROM assignment_submissions

            WHERE
                assignment_id = %s
                AND student_id = %s

            LIMIT 1
            """,
            (
                assignment_id,
                student_id
            )
        )

        submission = cursor.fetchone()

    except Exception as e:

        mysql.connection.rollback()

        flash(
            f"Unable to load assignment: {e}",
            "danger"
        )

        return redirect(
            url_for("student_assignment.index")
        )

    finally:

        cursor.close()

    return render_template(
        "student/assignment_detail.html",
        assignment=assignment,
        submission=submission,
        student=student
    )


# ============================================================
# SUBMIT ASSIGNMENT
# ============================================================

@student_assignment.route(
    "/submit/<int:assignment_id>",
    methods=["POST"]
)
def submit_assignment(assignment_id):

    if not student_logged_in():

        return redirect(
            url_for("student_auth.login")
        )

    cursor = mysql.connection.cursor()

    uploaded_file_path = None

    try:

        # ----------------------------------------------------
        # STUDENT
        # ----------------------------------------------------

        student = get_student(cursor)

        if not student:

            flash(
                "Student account not found.",
                "danger"
            )

            return redirect(
                url_for("student_auth.login")
            )

        student_id = student[0]

        # ----------------------------------------------------
        # VERIFY ASSIGNMENT
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                a.id,
                a.title,
                a.due_date,
                a.due_time,
                a.status,

                s.semester,
                s.department

            FROM assignments a

            INNER JOIN subjects s
                ON a.subject_id = s.id

            WHERE
                a.id = %s

                AND a.status = 'ACTIVE'

                AND s.semester = %s

                AND LOWER(TRIM(s.department))
                    = LOWER(TRIM(%s))

            LIMIT 1
            """,
            (
                assignment_id,
                student[5],
                student[4]
            )
        )

        assignment = cursor.fetchone()

        if not assignment:

            flash(
                "Assignment not found or unavailable.",
                "danger"
            )

            return redirect(
                url_for("student_assignment.index")
            )

        # ----------------------------------------------------
        # ANSWER
        # ----------------------------------------------------

        answer = request.form.get(
            "answer",
            ""
        ).strip()

        # ----------------------------------------------------
        # SUBMISSION FILE
        # ----------------------------------------------------

        submission_file = request.files.get(
            "submission_file"
        )

        filename = None

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not answer and (
            not submission_file
            or not submission_file.filename
        ):

            flash(
                "Please write an answer or upload a file.",
                "warning"
            )

            return redirect(
                url_for(
                    "student_assignment.view_assignment",
                    assignment_id=assignment_id
                )
            )

        # ----------------------------------------------------
        # FILE UPLOAD
        # ----------------------------------------------------

        if (
            submission_file
            and submission_file.filename
        ):

            if not allowed_submission_file(
                submission_file.filename
            ):

                flash(
                    "Invalid submission file type.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "student_assignment.view_assignment",
                        assignment_id=assignment_id
                    )
                )

            original_name = secure_filename(
                submission_file.filename
            )

            if not original_name:

                flash(
                    "Invalid submission filename.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "student_assignment.view_assignment",
                        assignment_id=assignment_id
                    )
                )

            extension = ""

            if "." in original_name:

                extension = (
                    original_name
                    .rsplit(".", 1)[1]
                    .lower()
                )

            filename = (
                uuid.uuid4().hex
                + "."
                + extension
            )

            upload_folder = (
                submission_upload_folder()
            )

            uploaded_file_path = os.path.join(
                upload_folder,
                filename
            )

            submission_file.save(
                uploaded_file_path
            )

        # ----------------------------------------------------
        # CHECK OLD SUBMISSION
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                attachment

            FROM assignment_submissions

            WHERE
                assignment_id = %s
                AND student_id = %s

            LIMIT 1
            """,
            (
                assignment_id,
                student_id
            )
        )

        old_submission = cursor.fetchone()

        # ====================================================
        # UPDATE EXISTING SUBMISSION
        # ====================================================

        if old_submission:

            old_submission_id = old_submission[0]

            old_attachment = old_submission[1]

            # Keep old file if no new file
            if not filename:

                filename = old_attachment

            cursor.execute(
                """
                UPDATE assignment_submissions

                SET
                    answer = %s,
                    attachment = %s,
                    submitted_at = NOW(),
                    marks = NULL,
                    feedback = NULL,
                    status = 'Submitted'

                WHERE id = %s
                """,
                (
                    answer if answer else None,
                    filename,
                    old_submission_id
                )
            )

            # ------------------------------------------------
            # Delete old file if replaced
            # ------------------------------------------------

            if (
                uploaded_file_path
                and old_attachment
                and old_attachment != filename
            ):

                old_path = os.path.join(
                    submission_upload_folder(),
                    os.path.basename(old_attachment)
                )

                if os.path.exists(old_path):

                    try:

                        os.remove(old_path)

                    except Exception:

                        pass

        # ====================================================
        # CREATE NEW SUBMISSION
        # ====================================================

        else:

            cursor.execute(
                """
                INSERT INTO assignment_submissions
                (
                    assignment_id,
                    student_id,
                    answer,
                    attachment,
                    submitted_at,
                    marks,
                    feedback,
                    status
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    NOW(),
                    NULL,
                    NULL,
                    'Submitted'
                )
                """,
                (
                    assignment_id,
                    student_id,
                    answer if answer else None,
                    filename
                )
            )

        mysql.connection.commit()

        flash(
            "Assignment submitted successfully.",
            "success"
        )

    except Exception as e:

        mysql.connection.rollback()

        # Delete uploaded file after failed DB operation
        if uploaded_file_path:

            try:

                if os.path.exists(
                    uploaded_file_path
                ):

                    os.remove(
                        uploaded_file_path
                    )

            except Exception:

                pass

        flash(
            f"Unable to submit assignment: {e}",
            "danger"
        )

    finally:

        cursor.close()

    return redirect(
        url_for(
            "student_assignment.view_assignment",
            assignment_id=assignment_id
        )
    )


# ============================================================
# DOWNLOAD ASSIGNMENT FILE
# ============================================================

@student_assignment.route(
    "/file/<int:assignment_id>"
)
def assignment_file(assignment_id):

    if not student_logged_in():

        return redirect(
            url_for("student_auth.login")
        )

    cursor = mysql.connection.cursor()

    result = None

    try:

        # ----------------------------------------------------
        # GET STUDENT
        # ----------------------------------------------------

        student = get_student(cursor)

        if not student:

            flash(
                "Student account not found.",
                "danger"
            )

            return redirect(
                url_for("student_auth.login")
            )

        # ----------------------------------------------------
        # GET ATTACHMENT
        # ----------------------------------------------------
        # IMPORTANT:
        # Database column is attachment.
        # NOT file_name.
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                a.attachment

            FROM assignments a

            INNER JOIN subjects s
                ON a.subject_id = s.id

            WHERE
                a.id = %s

                AND a.status = 'ACTIVE'

                AND s.semester = %s

                AND LOWER(TRIM(s.department))
                    = LOWER(TRIM(%s))

            LIMIT 1
            """,
            (
                assignment_id,
                student[5],
                student[4]
            )
        )

        result = cursor.fetchone()

    except Exception as e:

        mysql.connection.rollback()

        flash(
            f"Unable to download assignment: {e}",
            "danger"
        )

        return redirect(
            url_for("student_assignment.index")
        )

    finally:

        cursor.close()

    # --------------------------------------------------------
    # FILE NOT FOUND
    # --------------------------------------------------------

    if not result or not result[0]:

        flash(
            "Assignment file not found.",
            "warning"
        )

        return redirect(
            url_for("student_assignment.index")
        )

    # --------------------------------------------------------
    # CLEAN FILE NAME
    # --------------------------------------------------------

    stored_filename = os.path.basename(
        str(result[0])
    )

    file_path = os.path.join(
        assignment_upload_folder(),
        stored_filename
    )

    # --------------------------------------------------------
    # CHECK PHYSICAL FILE
    # --------------------------------------------------------

    if not os.path.isfile(file_path):

        flash(
            "Assignment file is missing from the server.",
            "danger"
        )

        return redirect(
            url_for("student_assignment.index")
        )

    # --------------------------------------------------------
    # ACTUAL DOWNLOAD
    # --------------------------------------------------------

    return send_from_directory(
        assignment_upload_folder(),
        stored_filename,
        as_attachment=True,
        download_name=stored_filename
    )


# ============================================================
# DOWNLOAD OWN SUBMISSION
# ============================================================

@student_assignment.route(
    "/submission-file/<int:submission_id>"
)
def submission_file(submission_id):

    if not student_logged_in():

        return redirect(
            url_for("student_auth.login")
        )

    cursor = mysql.connection.cursor()

    result = None

    try:

        student_id = session.get(
            "student_db_id"
        )

        cursor.execute(
            """
            SELECT
                attachment

            FROM assignment_submissions

            WHERE
                id = %s

                AND student_id = %s

            LIMIT 1
            """,
            (
                submission_id,
                student_id
            )
        )

        result = cursor.fetchone()

    except Exception as e:

        mysql.connection.rollback()

        flash(
            f"Unable to download submission: {e}",
            "danger"
        )

        return redirect(
            url_for("student_assignment.index")
        )

    finally:

        cursor.close()

    # --------------------------------------------------------
    # FILE NOT FOUND
    # --------------------------------------------------------

    if not result or not result[0]:

        flash(
            "Submission file not found.",
            "warning"
        )

        return redirect(
            url_for("student_assignment.index")
        )

    stored_filename = os.path.basename(
        str(result[0])
    )

    file_path = os.path.join(
        submission_upload_folder(),
        stored_filename
    )

    if not os.path.isfile(file_path):

        flash(
            "Submission file is missing from the server.",
            "danger"
        )

        return redirect(
            url_for("student_assignment.index")
        )

    # --------------------------------------------------------
    # ACTUAL DOWNLOAD
    # --------------------------------------------------------

    return send_from_directory(
        submission_upload_folder(),
        stored_filename,
        as_attachment=True,
        download_name=stored_filename
    )