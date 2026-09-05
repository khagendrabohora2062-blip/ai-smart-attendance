import os
import uuid

from io import BytesIO

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    current_app,
    send_file,
    abort
)

from werkzeug.utils import secure_filename

from extensions import mysql


# ============================================================
# STUDENT ASSIGNMENT
# File: routes/student_assignment.py
# ============================================================

student_assignment = Blueprint(
    "student_assignment",
    __name__,
    url_prefix="/student/assignments"
)


# ============================================================
# FILE TYPES
# ============================================================

ASSIGNMENT_EXTENSIONS = {
    "pdf",
    "doc",
    "docx",
    "txt",
    "jpg",
    "jpeg",
    "png",
    "webp"
}

SUBMISSION_EXTENSIONS = {
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
# LOGIN
# ============================================================

def student_logged_in():

    return bool(
        session.get("student_db_id")
    )


# ============================================================
# FILE VALIDATION
# ============================================================

def allowed_file(
    filename,
    extensions
):

    return (
        bool(filename)
        and "." in filename
        and filename.rsplit(
            ".",
            1
        )[1].lower() in extensions
    )


# ============================================================
# UPLOAD FOLDER
# ============================================================

def get_upload_folder(folder_name):

    folder = os.path.join(
        current_app.root_path,
        "static",
        "uploads",
        folder_name
    )

    os.makedirs(
        folder,
        exist_ok=True
    )

    return folder


# ============================================================
# STUDENT
# ============================================================

def get_student(cursor):

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
            session.get(
                "student_db_id"
            ),
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

        student = get_student(cursor)

        if not student:

            session.clear()

            return redirect(
                url_for("student_auth.login")
            )

        student_db_id = student[0]
        department = student[4]
        semester = student[5]

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

                s.id,
                s.subject_code,
                s.subject_name,
                s.semester,

                t.full_name

            FROM assignments a

            INNER JOIN subjects s
                ON a.subject_id = s.id

            LEFT JOIN teachers t
                ON a.teacher_id = t.id

            WHERE
                a.status = 'ACTIVE'

                AND LOWER(
                    TRIM(
                        COALESCE(
                            s.semester,
                            ''
                        )
                    )
                )
                =
                LOWER(
                    TRIM(
                        COALESCE(
                            %s,
                            ''
                        )
                    )
                )

                AND LOWER(
                    TRIM(
                        COALESCE(
                            s.department,
                            ''
                        )
                    )
                )
                =
                LOWER(
                    TRIM(
                        COALESCE(
                            %s,
                            ''
                        )
                    )
                )

            ORDER BY
                a.due_date ASC,
                a.due_time ASC,
                a.created_at DESC
            """,
            (
                semester,
                department
            )
        )

        rows = cursor.fetchall() or []

        for row in rows:

            cursor.execute(
                """
                SELECT
                    id,
                    answer,
                    attachment,
                    submitted_at,
                    marks,
                    feedback,
                    status,
                    attachment_data
                FROM assignment_submissions
                WHERE
                    assignment_id = %s
                    AND student_id = %s
                LIMIT 1
                """,
                (
                    row[0],
                    student_db_id
                )
            )

            submission = cursor.fetchone()

            assignments.append({

                "id": row[0],

                "title": row[1],

                "description": row[2],

                "total_marks": row[3],

                "due_date": row[4],

                "due_time": row[5],

                "attachment": row[6],

                "status": row[7],

                "created_at": row[8],

                "subject_id": row[9],

                "subject_code": row[10],

                "subject_name": row[11],

                "semester": row[12],

                "teacher_name":
                    row[13] or "Not Assigned",

                "submission":
                    submission

            })

        return render_template(
            "student/assignments.html",
            assignments=assignments,
            student=student
        )

    except Exception as e:

        try:
            mysql.connection.rollback()
        except Exception:
            pass

        print(
            "STUDENT ASSIGNMENT ERROR:",
            repr(e)
        )

        flash(
            "Unable to load assignments.",
            "danger"
        )

        return redirect(
            url_for("student_auth.dashboard")
        )

    finally:

        try:
            cursor.close()
        except Exception:
            pass


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

    try:

        student = get_student(cursor)

        if not student:

            return redirect(
                url_for("student_auth.login")
            )

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

                t.full_name

            FROM assignments a

            INNER JOIN subjects s
                ON a.subject_id = s.id

            LEFT JOIN teachers t
                ON a.teacher_id = t.id

            WHERE
                a.id = %s
                AND a.status = 'ACTIVE'

                AND LOWER(
                    TRIM(
                        COALESCE(
                            s.semester,
                            ''
                        )
                    )
                )
                =
                LOWER(
                    TRIM(
                        COALESCE(
                            %s,
                            ''
                        )
                    )
                )

                AND LOWER(
                    TRIM(
                        COALESCE(
                            s.department,
                            ''
                        )
                    )
                )
                =
                LOWER(
                    TRIM(
                        COALESCE(
                            %s,
                            ''
                        )
                    )
                )

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
                "warning"
            )

            return redirect(
                url_for(
                    "student_assignment.index"
                )
            )

        cursor.execute(
            """
            SELECT
                id,
                answer,
                attachment,
                submitted_at,
                marks,
                feedback,
                status,
                attachment_data
            FROM assignment_submissions
            WHERE
                assignment_id = %s
                AND student_id = %s
            LIMIT 1
            """,
            (
                assignment_id,
                student[0]
            )
        )

        submission = cursor.fetchone()

        return render_template(
            "student/assignment_detail.html",
            assignment=assignment,
            submission=submission,
            student=student
        )

    except Exception as e:

        print(
            "VIEW ASSIGNMENT ERROR:",
            repr(e)
        )

        flash(
            "Unable to load assignment.",
            "danger"
        )

        return redirect(
            url_for(
                "student_assignment.index"
            )
        )

    finally:

        try:
            cursor.close()
        except Exception:
            pass


# ============================================================
# SUBMIT ASSIGNMENT
# ============================================================

@student_assignment.route(
    "/submit/<int:assignment_id>",
    methods=["POST"]
)
def submit_assignment(
    assignment_id
):

    if not student_logged_in():

        return redirect(
            url_for("student_auth.login")
        )

    cursor = mysql.connection.cursor()

    try:

        student = get_student(cursor)

        if not student:

            return redirect(
                url_for("student_auth.login")
            )

        # ----------------------------------------------------
        # VERIFY ASSIGNMENT
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                a.id
            FROM assignments a

            INNER JOIN subjects s
                ON a.subject_id = s.id

            WHERE
                a.id = %s
                AND a.status = 'ACTIVE'

                AND LOWER(
                    TRIM(
                        COALESCE(
                            s.semester,
                            ''
                        )
                    )
                )
                =
                LOWER(
                    TRIM(
                        COALESCE(
                            %s,
                            ''
                        )
                    )
                )

                AND LOWER(
                    TRIM(
                        COALESCE(
                            s.department,
                            ''
                        )
                    )
                )
                =
                LOWER(
                    TRIM(
                        COALESCE(
                            %s,
                            ''
                        )
                    )
                )

            LIMIT 1
            """,
            (
                assignment_id,
                student[5],
                student[4]
            )
        )

        if not cursor.fetchone():

            flash(
                "Assignment is not available.",
                "danger"
            )

            return redirect(
                url_for(
                    "student_assignment.index"
                )
            )

        answer = request.form.get(
            "answer",
            ""
        ).strip()

        uploaded_file = request.files.get(
            "submission_file"
        )

        filename = None
        file_data = None

        # ----------------------------------------------------
        # FILE
        # ----------------------------------------------------

        if (
            uploaded_file
            and uploaded_file.filename
        ):

            if not allowed_file(
                uploaded_file.filename,
                SUBMISSION_EXTENSIONS
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

            original = secure_filename(
                uploaded_file.filename
            )

            if not original:

                flash(
                    "Invalid filename.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "student_assignment.view_assignment",
                        assignment_id=assignment_id
                    )
                )

            extension = (
                original.rsplit(
                    ".",
                    1
                )[1].lower()
            )

            filename = (
                uuid.uuid4().hex
                + "."
                + extension
            )

            file_data = uploaded_file.read()

            if not file_data:

                flash(
                    "Uploaded file is empty.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "student_assignment.view_assignment",
                        assignment_id=assignment_id
                    )
                )

        # ----------------------------------------------------
        # ANSWER OR FILE REQUIRED
        # ----------------------------------------------------

        if not answer and not file_data:

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
        # EXISTING SUBMISSION
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
                student[0]
            )
        )

        old = cursor.fetchone()

        if old:

            if file_data is not None:

                cursor.execute(
                    """
                    UPDATE assignment_submissions
                    SET
                        answer = %s,
                        attachment = %s,
                        attachment_data = %s,
                        submitted_at = NOW(),
                        marks = NULL,
                        feedback = NULL,
                        status = 'Submitted'
                    WHERE id = %s
                    """,
                    (
                        answer or None,
                        filename,
                        file_data,
                        old[0]
                    )
                )

            else:

                cursor.execute(
                    """
                    UPDATE assignment_submissions
                    SET
                        answer = %s,
                        submitted_at = NOW(),
                        marks = NULL,
                        feedback = NULL,
                        status = 'Submitted'
                    WHERE id = %s
                    """,
                    (
                        answer or None,
                        old[0]
                    )
                )

        else:

            cursor.execute(
                """
                INSERT INTO assignment_submissions
                (
                    assignment_id,
                    student_id,
                    answer,
                    attachment,
                    attachment_data,
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
                    %s,
                    NOW(),
                    NULL,
                    NULL,
                    'Submitted'
                )
                """,
                (
                    assignment_id,
                    student[0],
                    answer or None,
                    filename,
                    file_data
                )
            )

        mysql.connection.commit()

        flash(
            "Assignment submitted successfully.",
            "success"
        )

    except Exception as e:

        try:
            mysql.connection.rollback()
        except Exception:
            pass

        print(
            "SUBMIT ASSIGNMENT ERROR:",
            repr(e)
        )

        flash(
            "Unable to submit assignment.",
            "danger"
        )

    finally:

        try:
            cursor.close()
        except Exception:
            pass

    return redirect(
        url_for(
            "student_assignment.view_assignment",
            assignment_id=assignment_id
        )
    )


# ============================================================
# ASSIGNMENT FILE
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

    try:

        student = get_student(cursor)

        if not student:
            abort(404)

        cursor.execute(
            """
            SELECT
                a.attachment,
                a.attachment_data

            FROM assignments a

            INNER JOIN subjects s
                ON a.subject_id = s.id

            WHERE
                a.id = %s
                AND a.status = 'ACTIVE'

                AND LOWER(
                    TRIM(
                        COALESCE(
                            s.semester,
                            ''
                        )
                    )
                )
                =
                LOWER(
                    TRIM(
                        COALESCE(
                            %s,
                            ''
                        )
                    )
                )

                AND LOWER(
                    TRIM(
                        COALESCE(
                            s.department,
                            ''
                        )
                    )
                )
                =
                LOWER(
                    TRIM(
                        COALESCE(
                            %s,
                            ''
                        )
                    )
                )

            LIMIT 1
            """,
            (
                assignment_id,
                student[5],
                student[4]
            )
        )

        row = cursor.fetchone()

    finally:

        try:
            cursor.close()
        except Exception:
            pass

    if not row:

        abort(404)

    filename = os.path.basename(
        str(row[0] or "")
    )

    file_data = row[1]

    if not filename:

        filename = (
            f"assignment_{assignment_id}"
        )

    # ----------------------------------------------------
    # DATABASE FILE
    # ----------------------------------------------------

    if file_data:

        return send_file(
            BytesIO(bytes(file_data)),
            mimetype="application/octet-stream",
            as_attachment=True,
            download_name=filename
        )

    # ----------------------------------------------------
    # OLD PHYSICAL FILE
    # ----------------------------------------------------

    path = os.path.join(
        get_upload_folder("assignments"),
        filename
    )

    if os.path.isfile(path):

        return send_file(
            path,
            as_attachment=True,
            download_name=filename
        )

    flash(
        "Assignment file is not available. "
        "Please ask the teacher to migrate or re-upload it.",
        "danger"
    )

    return redirect(
        url_for(
            "student_assignment.index"
        )
    )


# ============================================================
# STUDENT SUBMISSION FILE
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

    try:

        cursor.execute(
            """
            SELECT
                attachment,
                attachment_data
            FROM assignment_submissions
            WHERE
                id = %s
                AND student_id = %s
            LIMIT 1
            """,
            (
                submission_id,
                session["student_db_id"]
            )
        )

        row = cursor.fetchone()

    finally:

        try:
            cursor.close()
        except Exception:
            pass

    if not row:

        abort(404)

    filename = os.path.basename(
        str(row[0] or "")
    )

    file_data = row[1]

    if not filename:

        filename = (
            f"submission_{submission_id}"
        )

    if file_data:

        return send_file(
            BytesIO(bytes(file_data)),
            mimetype="application/octet-stream",
            as_attachment=True,
            download_name=filename
        )

    path = os.path.join(
        get_upload_folder(
            "assignment_submissions"
        ),
        filename
    )

    if os.path.isfile(path):

        return send_file(
            path,
            as_attachment=True,
            download_name=filename
        )

    flash(
        "Your submitted file is not available on the server.",
        "danger"
    )

    return redirect(
        url_for(
            "student_assignment.index"
        )
    )