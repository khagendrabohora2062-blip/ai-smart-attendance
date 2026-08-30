
# ============================================================
# TEACHER ASSIGNMENT MANAGEMENT
# File: routes/teacher_assignment.py
# ============================================================

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

import os
import uuid

from werkzeug.utils import secure_filename


# ============================================================
# BLUEPRINT
# ============================================================

teacher_assignment = Blueprint(
    "teacher_assignment",
    __name__,
    url_prefix="/teacher/assignments"
)


# ============================================================
# ALLOWED ASSIGNMENT FILES
# ============================================================

ALLOWED_EXTENSIONS = {
    "pdf",
    "doc",
    "docx",
    "txt",
    "jpg",
    "jpeg",
    "png",
    "webp"
}


# ============================================================
# ALLOWED SUBMISSION FILES
# ============================================================

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
# HELPERS
# ============================================================

def allowed_file(filename):
    return (
        bool(filename)
        and "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def allowed_submission_file(filename):
    return (
        bool(filename)
        and "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in SUBMISSION_ALLOWED_EXTENSIONS
    )


def teacher_logged_in():
    return "teacher_id" in session


# ============================================================
# GENERATE UNIQUE ASSIGNMENT ID
# ============================================================

def generate_assignment_id(cursor):
    """
    Generates a unique positive integer ID for assignments.

    This is used because the TiDB assignments.id column
    currently does NOT have AUTO_INCREMENT.
    """

    max_id = 2147483647

    for _ in range(20):

        # Generate a positive 32-bit integer
        new_id = uuid.uuid4().int % max_id

        # Make sure ID is never 0
        if new_id <= 0:
            new_id = 1

        cursor.execute(
            """
            SELECT id
            FROM assignments
            WHERE id = %s
            LIMIT 1
            """,
            (new_id,)
        )

        existing = cursor.fetchone()

        if not existing:
            return new_id

    raise RuntimeError(
        "Unable to generate a unique assignment ID."
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
# ASSIGNMENT LIST
# ============================================================

@teacher_assignment.route("/")
def index():

    if not teacher_logged_in():
        return redirect(
            url_for("teacher_auth.login")
        )

    teacher_id = session["teacher_id"]

    cursor = mysql.connection.cursor()

    assignments = []

    try:

        cursor.execute(
            """
            SELECT
                a.id,
                a.title,
                a.description,
                a.attachment,
                a.due_date,
                a.due_time,
                a.total_marks,
                a.status,
                a.created_at,
                s.subject_code,
                s.subject_name,
                s.semester
            FROM assignments a
            INNER JOIN subjects s
                ON a.subject_id = s.id
            WHERE a.teacher_id = %s
            ORDER BY a.created_at DESC
            """,
            (teacher_id,)
        )

        rows = cursor.fetchall()

        for row in rows:

            assignment_id = row[0]

            # ------------------------------------------------
            # TOTAL SUBMISSIONS
            # ------------------------------------------------

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM assignment_submissions
                WHERE assignment_id = %s
                """,
                (assignment_id,)
            )

            result = cursor.fetchone()

            submission_count = (
                result[0]
                if result
                else 0
            )

            # ------------------------------------------------
            # PENDING SUBMISSIONS
            # ------------------------------------------------

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM assignment_submissions
                WHERE assignment_id = %s
                AND status = 'Submitted'
                """,
                (assignment_id,)
            )

            result = cursor.fetchone()

            pending_count = (
                result[0]
                if result
                else 0
            )

            # ------------------------------------------------
            # ASSIGNMENT DICTIONARY
            # ------------------------------------------------

            assignments.append({
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "attachment": row[3],
                "due_date": row[4],
                "due_time": row[5],
                "total_marks": row[6],
                "status": row[7],
                "created_at": row[8],
                "subject_code": row[9],
                "subject_name": row[10],
                "semester": row[11],
                "submission_count": submission_count,
                "pending_count": pending_count
            })

    except Exception as e:

        mysql.connection.rollback()

        print(
            "Assignment index error:",
            e
        )

        flash(
            f"Unable to load assignments: {e}",
            "danger"
        )

        assignments = []

    finally:
        cursor.close()

    return render_template(
        "teacher/assignments.html",
        assignments=assignments
    )


# ============================================================
# CREATE ASSIGNMENT
# ============================================================

@teacher_assignment.route(
    "/create",
    methods=["GET", "POST"]
)
def create():

    if not teacher_logged_in():
        return redirect(
            url_for("teacher_auth.login")
        )

    teacher_id = session["teacher_id"]

    cursor = mysql.connection.cursor()

    subjects = []

    # ========================================================
    # LOAD SUBJECTS
    # ========================================================

    try:

        cursor.execute(
            """
            SELECT
                id,
                subject_code,
                subject_name,
                semester
            FROM subjects
            WHERE teacher_id = %s
            ORDER BY semester, subject_name
            """,
            (teacher_id,)
        )

        subjects = cursor.fetchall()

    except Exception as e:

        cursor.close()

        flash(
            f"Unable to load subjects: {e}",
            "danger"
        )

        return redirect(
            url_for("teacher_auth.dashboard")
        )

    # ========================================================
    # POST
    # ========================================================

    if request.method == "POST":

        subject_id = request.form.get(
            "subject_id",
            ""
        ).strip()

        title = request.form.get(
            "title",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        due_date = request.form.get(
            "due_date",
            ""
        ).strip()

        due_time = request.form.get(
            "due_time",
            ""
        ).strip()

        total_marks = request.form.get(
            "total_marks",
            ""
        ).strip()

        attachment = request.files.get(
            "attachment"
        )

        # ====================================================
        # VALIDATION
        # ====================================================

        if not subject_id:

            cursor.close()

            flash(
                "Please select a subject.",
                "danger"
            )

            return redirect(
                url_for("teacher_assignment.create")
            )

        if not title:

            cursor.close()

            flash(
                "Assignment title is required.",
                "danger"
            )

            return redirect(
                url_for("teacher_assignment.create")
            )

        if not due_date:

            cursor.close()

            flash(
                "Due date is required.",
                "danger"
            )

            return redirect(
                url_for("teacher_assignment.create")
            )

        # ====================================================
        # VERIFY SUBJECT
        # ====================================================

        try:

            subject_id_int = int(subject_id)

        except (
            ValueError,
            TypeError
        ):

            cursor.close()

            flash(
                "Invalid subject selected.",
                "danger"
            )

            return redirect(
                url_for("teacher_assignment.create")
            )

        cursor.execute(
            """
            SELECT
                id,
                subject_code,
                subject_name
            FROM subjects
            WHERE id = %s
            AND teacher_id = %s
            LIMIT 1
            """,
            (
                subject_id_int,
                teacher_id
            )
        )

        subject = cursor.fetchone()

        if not subject:

            cursor.close()

            flash(
                "Invalid subject selected.",
                "danger"
            )

            return redirect(
                url_for("teacher_assignment.create")
            )

        # ====================================================
        # TOTAL MARKS
        # ====================================================

        if not total_marks:

            total_marks = 100

        else:

            try:
                total_marks = int(total_marks)

            except (
                ValueError,
                TypeError
            ):

                total_marks = 100

        if total_marks < 1:
            total_marks = 100

        if total_marks > 1000:
            total_marks = 1000

        # ====================================================
        # FILE UPLOAD
        # ====================================================

        filename = None
        file_path = None

        if attachment and attachment.filename:

            if not allowed_file(
                attachment.filename
            ):

                cursor.close()

                flash(
                    "Invalid attachment file type.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "teacher_assignment.create"
                    )
                )

            original_filename = secure_filename(
                attachment.filename
            )

            if not original_filename:

                cursor.close()

                flash(
                    "Invalid attachment filename.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "teacher_assignment.create"
                    )
                )

            extension = ""

            if "." in original_filename:

                extension = (
                    original_filename
                    .rsplit(".", 1)[1]
                    .lower()
                )

            filename = (
                f"{uuid.uuid4().hex}.{extension}"
            )

            upload_folder = (
                assignment_upload_folder()
            )

            file_path = os.path.join(
                upload_folder,
                filename
            )

            try:

                attachment.save(
                    file_path
                )

            except Exception as e:

                cursor.close()

                flash(
                    f"Unable to save attachment: {e}",
                    "danger"
                )

                return redirect(
                    url_for(
                        "teacher_assignment.create"
                    )
                )

        # ====================================================
        # GENERATE ASSIGNMENT ID
        # ====================================================

        try:

            assignment_id = generate_assignment_id(
                cursor
            )

        except Exception as e:

            cursor.close()

            if file_path:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception:
                    pass

            flash(
                f"Unable to generate assignment ID: {e}",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher_assignment.create"
                )
            )

        # ====================================================
        # INSERT ASSIGNMENT
        # ====================================================

        try:

            cursor.execute(
                """
                INSERT INTO assignments
                (
                    id,
                    teacher_id,
                    subject_id,
                    title,
                    description,
                    attachment,
                    due_date,
                    due_time,
                    total_marks,
                    status
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
                    'ACTIVE'
                )
                """,
                (
                    assignment_id,
                    teacher_id,
                    subject_id_int,
                    title,
                    description if description else None,
                    filename,
                    due_date,
                    due_time if due_time else "23:59:59",
                    total_marks
                )
            )

            mysql.connection.commit()

        except Exception as e:

            mysql.connection.rollback()

            if file_path:

                try:

                    if os.path.exists(file_path):
                        os.remove(file_path)

                except Exception:
                    pass

            cursor.close()

            print(
                "Create assignment error:",
                e
            )

            flash(
                f"Failed to create assignment: {e}",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher_assignment.create"
                )
            )

        cursor.close()

        flash(
            "Assignment created successfully.",
            "success"
        )

        return redirect(
            url_for(
                "teacher_assignment.index"
            )
        )

    # ========================================================
    # GET
    # ========================================================

    cursor.close()

    return render_template(
        "teacher/assignment_form.html",
        assignment=None,
        subjects=subjects,
        mode="create"
    )


# ============================================================
# EDIT ASSIGNMENT
# ============================================================

@teacher_assignment.route(
    "/edit/<int:assignment_id>",
    methods=["GET", "POST"]
)
def edit(assignment_id):

    if not teacher_logged_in():

        return redirect(
            url_for("teacher_auth.login")
        )

    teacher_id = session["teacher_id"]

    cursor = mysql.connection.cursor()

    try:

        # ====================================================
        # GET ASSIGNMENT
        # ====================================================

        cursor.execute(
            """
            SELECT
                id,
                teacher_id,
                subject_id,
                title,
                description,
                attachment,
                due_date,
                due_time,
                total_marks,
                status
            FROM assignments
            WHERE id = %s
            AND teacher_id = %s
            LIMIT 1
            """,
            (
                assignment_id,
                teacher_id
            )
        )

        assignment = cursor.fetchone()

        if not assignment:

            flash(
                "Assignment not found.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher_assignment.index"
                )
            )

        # ====================================================
        # GET SUBJECTS
        # ====================================================

        cursor.execute(
            """
            SELECT
                id,
                subject_code,
                subject_name,
                semester
            FROM subjects
            WHERE teacher_id = %s
            ORDER BY semester, subject_name
            """,
            (teacher_id,)
        )

        subjects = cursor.fetchall()

        # ====================================================
        # POST
        # ====================================================

        if request.method == "POST":

            subject_id = request.form.get(
                "subject_id",
                ""
            ).strip()

            title = request.form.get(
                "title",
                ""
            ).strip()

            description = request.form.get(
                "description",
                ""
            ).strip()

            due_date = request.form.get(
                "due_date",
                ""
            ).strip()

            due_time = request.form.get(
                "due_time",
                "23:59:59"
            ).strip()

            total_marks = request.form.get(
                "total_marks",
                "100"
            ).strip()

            status = request.form.get(
                "status",
                "ACTIVE"
            ).strip()

            attachment = request.files.get(
                "attachment"
            )

            # =================================================
            # VALIDATION
            # =================================================

            if not subject_id:

                flash(
                    "Please select a subject.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "teacher_assignment.edit",
                        assignment_id=assignment_id
                    )
                )

            if not title:

                flash(
                    "Assignment title is required.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "teacher_assignment.edit",
                        assignment_id=assignment_id
                    )
                )

            if not due_date:

                flash(
                    "Due date is required.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "teacher_assignment.edit",
                        assignment_id=assignment_id
                    )
                )

            # =================================================
            # VERIFY SUBJECT
            # =================================================

            try:

                subject_id_int = int(subject_id)

            except (
                ValueError,
                TypeError
            ):

                flash(
                    "Invalid subject selected.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "teacher_assignment.edit",
                        assignment_id=assignment_id
                    )
                )

            cursor.execute(
                """
                SELECT id
                FROM subjects
                WHERE id = %s
                AND teacher_id = %s
                LIMIT 1
                """,
                (
                    subject_id_int,
                    teacher_id
                )
            )

            subject = cursor.fetchone()

            if not subject:

                flash(
                    "Invalid subject selected.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "teacher_assignment.edit",
                        assignment_id=assignment_id
                    )
                )

            # =================================================
            # TOTAL MARKS
            # =================================================

            try:

                total_marks = int(
                    total_marks
                )

            except (
                ValueError,
                TypeError
            ):

                total_marks = 100

            if total_marks < 1:
                total_marks = 100

            if total_marks > 1000:
                total_marks = 1000

            # =================================================
            # STATUS
            # =================================================

            if status not in {
                "ACTIVE",
                "INACTIVE"
            }:

                status = "ACTIVE"

            # =================================================
            # KEEP OLD ATTACHMENT
            # =================================================

            old_attachment = assignment[5]

            new_filename = old_attachment

            new_file_path = None

            # =================================================
            # NEW ATTACHMENT
            # =================================================

            if (
                attachment
                and attachment.filename
            ):

                if not allowed_file(
                    attachment.filename
                ):

                    flash(
                        "Invalid attachment file type.",
                        "danger"
                    )

                    return redirect(
                        url_for(
                            "teacher_assignment.edit",
                            assignment_id=assignment_id
                        )
                    )

                original_filename = secure_filename(
                    attachment.filename
                )

                if not original_filename:

                    flash(
                        "Invalid attachment filename.",
                        "danger"
                    )

                    return redirect(
                        url_for(
                            "teacher_assignment.edit",
                            assignment_id=assignment_id
                        )
                    )

                extension = ""

                if "." in original_filename:

                    extension = (
                        original_filename
                        .rsplit(".", 1)[1]
                        .lower()
                    )

                new_filename = (
                    f"{uuid.uuid4().hex}.{extension}"
                )

                new_file_path = os.path.join(
                    assignment_upload_folder(),
                    new_filename
                )

                try:

                    attachment.save(
                        new_file_path
                    )

                except Exception as e:

                    flash(
                        f"Unable to save attachment: {e}",
                        "danger"
                    )

                    return redirect(
                        url_for(
                            "teacher_assignment.edit",
                            assignment_id=assignment_id
                        )
                    )

            # =================================================
            # UPDATE DATABASE
            # =================================================

            try:

                cursor.execute(
                    """
                    UPDATE assignments
                    SET
                        subject_id = %s,
                        title = %s,
                        description = %s,
                        attachment = %s,
                        due_date = %s,
                        due_time = %s,
                        total_marks = %s,
                        status = %s
                    WHERE id = %s
                    AND teacher_id = %s
                    """,
                    (
                        subject_id_int,
                        title,
                        description if description else None,
                        new_filename,
                        due_date,
                        due_time if due_time else "23:59:59",
                        total_marks,
                        status,
                        assignment_id,
                        teacher_id
                    )
                )

                mysql.connection.commit()

            except Exception as e:

                mysql.connection.rollback()

                # Delete newly uploaded file
                if new_file_path:

                    try:

                        if os.path.exists(
                            new_file_path
                        ):
                            os.remove(
                                new_file_path
                            )

                    except Exception:
                        pass

                flash(
                    f"Unable to update assignment: {e}",
                    "danger"
                )

                return redirect(
                    url_for(
                        "teacher_assignment.edit",
                        assignment_id=assignment_id
                    )
                )

            # =================================================
            # DELETE OLD FILE
            # =================================================

            if (
                new_filename != old_attachment
                and old_attachment
            ):

                old_path = os.path.join(
                    assignment_upload_folder(),
                    old_attachment
                )

                try:

                    if os.path.exists(
                        old_path
                    ):
                        os.remove(
                            old_path
                        )

                except Exception as e:

                    print(
                        "Old assignment file delete error:",
                        e
                    )

            flash(
                "Assignment updated successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "teacher_assignment.index"
                )
            )

        # ====================================================
        # GET PAGE
        # ====================================================

        return render_template(
            "teacher/assignment_form.html",
            assignment=assignment,
            subjects=subjects,
            mode="edit"
        )

    except Exception as e:

        mysql.connection.rollback()

        flash(
            f"Unable to edit assignment: {e}",
            "danger"
        )

        return redirect(
            url_for(
                "teacher_assignment.index"
            )
        )

    finally:

        cursor.close()


# ============================================================
# TOGGLE STATUS
# ============================================================

@teacher_assignment.route(
    "/toggle/<int:assignment_id>",
    methods=["POST"]
)
def toggle_status(assignment_id):

    if not teacher_logged_in():

        return redirect(
            url_for("teacher_auth.login")
        )

    teacher_id = session["teacher_id"]

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT status
            FROM assignments
            WHERE id = %s
            AND teacher_id = %s
            LIMIT 1
            """,
            (
                assignment_id,
                teacher_id
            )
        )

        assignment = cursor.fetchone()

        if not assignment:

            flash(
                "Assignment not found.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher_assignment.index"
                )
            )

        current_status = assignment[0]

        new_status = (
            "INACTIVE"
            if current_status == "ACTIVE"
            else "ACTIVE"
        )

        cursor.execute(
            """
            UPDATE assignments
            SET status = %s
            WHERE id = %s
            AND teacher_id = %s
            """,
            (
                new_status,
                assignment_id,
                teacher_id
            )
        )

        mysql.connection.commit()

        flash(
            f"Assignment marked as {new_status.lower()}.",
            "success"
        )

    except Exception as e:

        mysql.connection.rollback()

        flash(
            f"Unable to update assignment status: {e}",
            "danger"
        )

    finally:

        cursor.close()

    return redirect(
        url_for(
            "teacher_assignment.index"
        )
    )


# ============================================================
# VIEW SUBMISSIONS
# ============================================================

@teacher_assignment.route(
    "/submissions/<int:assignment_id>"
)
def submissions(assignment_id):

    if not teacher_logged_in():

        return redirect(
            url_for("teacher_auth.login")
        )

    teacher_id = session["teacher_id"]

    cursor = mysql.connection.cursor()

    assignment = None

    submissions_list = []

    try:

        # ====================================================
        # ASSIGNMENT
        # ====================================================

        cursor.execute(
            """
            SELECT
                a.id,
                a.teacher_id,
                a.subject_id,
                a.title,
                a.description,
                a.attachment,
                a.due_date,
                a.due_time,
                a.created_at,
                a.total_marks,
                a.status,
                s.subject_code,
                s.subject_name,
                s.semester
            FROM assignments a
            INNER JOIN subjects s
                ON a.subject_id = s.id
            WHERE a.id = %s
            AND a.teacher_id = %s
            LIMIT 1
            """,
            (
                assignment_id,
                teacher_id
            )
        )

        assignment = cursor.fetchone()

        if not assignment:

            flash(
                "Assignment not found.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher_assignment.index"
                )
            )

        # ====================================================
        # SUBMISSIONS
        # ====================================================

        cursor.execute(
            """
            SELECT
                sub.id,
                sub.assignment_id,
                sub.student_id,
                sub.answer,
                sub.attachment,
                sub.submitted_at,
                sub.marks,
                sub.feedback,
                sub.status,
                st.student_id,
                st.full_name,
                st.email,
                st.photo
            FROM assignment_submissions sub
            INNER JOIN students st
                ON sub.student_id = st.id
            WHERE sub.assignment_id = %s
            ORDER BY sub.submitted_at DESC
            """,
            (assignment_id,)
        )

        submissions_list = cursor.fetchall()

    except Exception as e:

        mysql.connection.rollback()

        flash(
            f"Unable to load submissions: {e}",
            "danger"
        )

    finally:

        cursor.close()

    return render_template(
        "teacher/assignment_submissions.html",
        assignment=assignment,
        submissions=submissions_list
    )


# ============================================================
# GRADE SUBMISSION
# ============================================================

@teacher_assignment.route(
    "/grade/<int:submission_id>",
    methods=["GET", "POST"]
)
def grade_submission(submission_id):

    if not teacher_logged_in():

        return redirect(
            url_for("teacher_auth.login")
        )

    teacher_id = session["teacher_id"]

    cursor = mysql.connection.cursor()

    submission = None

    try:

        # ====================================================
        # GET SUBMISSION
        # ====================================================

        cursor.execute(
            """
            SELECT
                sub.id,
                sub.assignment_id,
                sub.student_id,
                sub.answer,
                sub.attachment,
                sub.submitted_at,
                sub.marks,
                sub.feedback,
                sub.status,
                st.student_id,
                st.full_name,
                st.email,
                a.title,
                a.total_marks,
                a.teacher_id
            FROM assignment_submissions sub
            INNER JOIN students st
                ON sub.student_id = st.id
            INNER JOIN assignments a
                ON sub.assignment_id = a.id
            WHERE sub.id = %s
            AND a.teacher_id = %s
            LIMIT 1
            """,
            (
                submission_id,
                teacher_id
            )
        )

        submission = cursor.fetchone()

        if not submission:

            flash(
                "Submission not found.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher_assignment.index"
                )
            )

        # ====================================================
        # POST
        # ====================================================

        if request.method == "POST":

            marks = request.form.get(
                "marks",
                ""
            ).strip()

            feedback = request.form.get(
                "feedback",
                ""
            ).strip()

            status = request.form.get(
                "status",
                "Graded"
            ).strip()

            # =================================================
            # MARKS
            # =================================================

            if marks == "":

                marks = None

            else:

                try:

                    marks = float(
                        marks
                    )

                except (
                    ValueError,
                    TypeError
                ):

                    flash(
                        "Please enter valid marks.",
                        "danger"
                    )

                    return redirect(
                        url_for(
                            "teacher_assignment.grade_submission",
                            submission_id=submission_id
                        )
                    )

            # =================================================
            # MAX MARKS
            # submission index 13 = total_marks
            # =================================================

            max_marks = submission[13]

            if marks is not None:

                if marks < 0:

                    flash(
                        "Marks cannot be negative.",
                        "danger"
                    )

                    return redirect(
                        url_for(
                            "teacher_assignment.grade_submission",
                            submission_id=submission_id
                        )
                    )

                if marks > max_marks:

                    flash(
                        f"Marks cannot be greater than {max_marks}.",
                        "danger"
                    )

                    return redirect(
                        url_for(
                            "teacher_assignment.grade_submission",
                            submission_id=submission_id
                        )
                    )

            # =================================================
            # STATUS
            # =================================================

            if status not in {
                "Submitted",
                "Graded",
                "Returned"
            }:

                status = "Graded"

            # =================================================
            # UPDATE
            # =================================================

            cursor.execute(
                """
                UPDATE assignment_submissions
                SET
                    marks = %s,
                    feedback = %s,
                    status = %s
                WHERE id = %s
                """,
                (
                    marks,
                    feedback if feedback else None,
                    status,
                    submission_id
                )
            )

            mysql.connection.commit()

            flash(
                "Submission updated successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "teacher_assignment.submissions",
                    assignment_id=submission[1]
                )
            )

    except Exception as e:

        mysql.connection.rollback()

        flash(
            f"Unable to grade submission: {e}",
            "danger"
        )

    finally:

        cursor.close()

    return render_template(
        "teacher/grade_assignment.html",
        submission=submission
    )


# ============================================================
# DOWNLOAD ASSIGNMENT ATTACHMENT
# ============================================================

@teacher_assignment.route(
    "/attachment/<int:assignment_id>"
)
def download(assignment_id):

    if not teacher_logged_in():

        return redirect(
            url_for("teacher_auth.login")
        )

    teacher_id = session["teacher_id"]

    cursor = mysql.connection.cursor()

    assignment = None

    try:

        cursor.execute(
            """
            SELECT attachment
            FROM assignments
            WHERE id = %s
            AND teacher_id = %s
            LIMIT 1
            """,
            (
                assignment_id,
                teacher_id
            )
        )

        assignment = cursor.fetchone()

    except Exception as e:

        mysql.connection.rollback()

        flash(
            f"Unable to load attachment: {e}",
            "danger"
        )

    finally:

        cursor.close()

    if not assignment or not assignment[0]:

        flash(
            "Assignment attachment not found.",
            "danger"
        )

        return redirect(
            url_for(
                "teacher_assignment.index"
            )
        )

    return send_from_directory(
        assignment_upload_folder(),
        assignment[0],
        as_attachment=False
    )


# ============================================================
# DOWNLOAD STUDENT SUBMISSION FILE
# ============================================================

@teacher_assignment.route(
    "/submission-file/<int:submission_id>"
)
def submission_file(submission_id):

    if not teacher_logged_in():

        return redirect(
            url_for("teacher_auth.login")
        )

    teacher_id = session["teacher_id"]

    cursor = mysql.connection.cursor()

    submission = None

    try:

        cursor.execute(
            """
            SELECT
                sub.attachment
            FROM assignment_submissions sub
            INNER JOIN assignments a
                ON sub.assignment_id = a.id
            WHERE sub.id = %s
            AND a.teacher_id = %s
            LIMIT 1
            """,
            (
                submission_id,
                teacher_id
            )
        )

        submission = cursor.fetchone()

    except Exception as e:

        mysql.connection.rollback()

        flash(
            f"Unable to load submission file: {e}",
            "danger"
        )

    finally:

        cursor.close()

    if not submission or not submission[0]:

        flash(
            "Submission attachment not found.",
            "danger"
        )

        return redirect(
            url_for(
                "teacher_assignment.index"
            )
        )

    return send_from_directory(
        submission_upload_folder(),
        submission[0],
        as_attachment=False
    )


# ============================================================
# DELETE ASSIGNMENT
# ============================================================

@teacher_assignment.route(
    "/delete/<int:assignment_id>",
    methods=["POST"]
)
def delete(assignment_id):

    if not teacher_logged_in():

        return redirect(
            url_for("teacher_auth.login")
        )

    teacher_id = session["teacher_id"]

    cursor = mysql.connection.cursor()

    old_attachment = None

    submission_files = []

    try:

        # ====================================================
        # GET ASSIGNMENT
        # ====================================================

        cursor.execute(
            """
            SELECT attachment
            FROM assignments
            WHERE id = %s
            AND teacher_id = %s
            LIMIT 1
            """,
            (
                assignment_id,
                teacher_id
            )
        )

        assignment = cursor.fetchone()

        if not assignment:

            flash(
                "Assignment not found.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher_assignment.index"
                )
            )

        old_attachment = assignment[0]

        # ====================================================
        # GET SUBMISSION FILES
        # ====================================================

        cursor.execute(
            """
            SELECT attachment
            FROM assignment_submissions
            WHERE assignment_id = %s
            """,
            (assignment_id,)
        )

        submission_files = cursor.fetchall()

        # ====================================================
        # DELETE SUBMISSIONS
        # ====================================================

        cursor.execute(
            """
            DELETE FROM assignment_submissions
            WHERE assignment_id = %s
            """,
            (assignment_id,)
        )

        # ====================================================
        # DELETE ASSIGNMENT
        # ====================================================

        cursor.execute(
            """
            DELETE FROM assignments
            WHERE id = %s
            AND teacher_id = %s
            """,
            (
                assignment_id,
                teacher_id
            )
        )

        mysql.connection.commit()

        # ====================================================
        # DELETE ASSIGNMENT FILE
        # ====================================================

        if old_attachment:

            old_path = os.path.join(
                assignment_upload_folder(),
                old_attachment
            )

            if os.path.exists(old_path):

                try:

                    os.remove(
                        old_path
                    )

                except Exception as e:

                    print(
                        "Assignment file delete error:",
                        e
                    )

        # ====================================================
        # DELETE SUBMISSION FILES
        # ====================================================

        for row in submission_files:

            filename = row[0]

            if filename:

                submission_path = os.path.join(
                    submission_upload_folder(),
                    filename
                )

                if os.path.exists(
                    submission_path
                ):

                    try:

                        os.remove(
                            submission_path
                        )

                    except Exception as e:

                        print(
                            "Submission file delete error:",
                            e
                        )

        flash(
            "Assignment deleted successfully.",
            "success"
        )

    except Exception as e:

        mysql.connection.rollback()

        flash(
            f"Unable to delete assignment: {e}",
            "danger"
        )

    finally:

        cursor.close()

    return redirect(
        url_for(
            "teacher_assignment.index"
        )
    )
