from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

from werkzeug.security import (
    check_password_hash,
    generate_password_hash
)

from extensions import mysql
from werkzeug.utils import secure_filename

import os
import uuid


# =========================================================
# STUDENT AUTH BLUEPRINT
# =========================================================

student_auth = Blueprint(
    "student_auth",
    __name__,
    url_prefix="/student"
)


# =========================================================
# SAFE NUMBER HELPER
# =========================================================

def safe_float(value, default=0.0):
    """
    Safely convert MySQL Decimal/int/float/string/None
    into a real float.

    This prevents errors such as:
    'must be real number, not str'
    """

    if value is None:
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# =========================================================
# GET CURRENT STUDENT
# =========================================================

def get_current_student():

    if "student_db_id" not in session:
        return None

    student_db_id = session["student_db_id"]

    cursor = mysql.connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                id,
                student_id,
                full_name,
                email,
                phone,
                department,
                semester,
                section,
                photo
            FROM students
            WHERE id = %s
            LIMIT 1
            """,
            (student_db_id,)
        )

        student = cursor.fetchone()

        return student

    except Exception:
        return None

    finally:
        cursor.close()


# =========================================================
# STUDENT LOGIN
# =========================================================

@student_auth.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    # -----------------------------------------------------
    # ALREADY LOGGED IN
    # -----------------------------------------------------

    if "student_db_id" in session:
        return redirect(
            url_for("student_auth.dashboard")
        )

    # -----------------------------------------------------
    # POST LOGIN
    # -----------------------------------------------------

    if request.method == "POST":

        student_id = request.form.get(
            "student_id",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()

        # -------------------------------------------------
        # EMPTY FIELDS
        # -------------------------------------------------

        if not student_id or not password:

            flash(
                "Student ID and password are required.",
                "danger"
            )

            return render_template(
                "student/login.html"
            )

        cursor = mysql.connection.cursor()

        try:

            # -------------------------------------------------
            # FIND STUDENT
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT
                    id,
                    student_id,
                    full_name,
                    email,
                    phone,
                    department,
                    semester,
                    section,
                    password,
                    photo
                FROM students
                WHERE student_id = %s
                LIMIT 1
                """,
                (student_id,)
            )

            student = cursor.fetchone()

        except Exception as e:

            mysql.connection.rollback()

            print(
                "STUDENT LOGIN ERROR:",
                repr(e)
            )

            cursor.close()

            flash(
                "Unable to process login. Please try again.",
                "danger"
            )

            return render_template(
                "student/login.html"
            )

        finally:

            try:
                cursor.close()
            except Exception:
                pass

        # -------------------------------------------------
        # STUDENT NOT FOUND
        # -------------------------------------------------

        if not student:

            flash(
                "Invalid Student ID or password.",
                "danger"
            )

            return render_template(
                "student/login.html"
            )

        # -------------------------------------------------
        # PASSWORD
        # -------------------------------------------------

        stored_password = student[8]

        password_valid = False

        if stored_password:

            stored_password = str(
                stored_password
            )

            # Try hashed password
            try:

                password_valid = check_password_hash(
                    stored_password,
                    password
                )

            except Exception:

                password_valid = False

            # Support old plain-text password
            if not password_valid:

                password_valid = (
                    stored_password == password
                )

        # -------------------------------------------------
        # INVALID PASSWORD
        # -------------------------------------------------

        if not password_valid:

            flash(
                "Invalid Student ID or password.",
                "danger"
            )

            return render_template(
                "student/login.html"
            )

        # =================================================
        # REMOVE OTHER ROLE SESSIONS
        # =================================================

        session.pop(
            "admin_id",
            None
        )

        session.pop(
            "admin_name",
            None
        )

        session.pop(
            "admin_username",
            None
        )

        session.pop(
            "admin_profile_photo",
            None
        )

        session.pop(
            "teacher_id",
            None
        )

        # =================================================
        # CREATE STUDENT SESSION
        # =================================================

        session["student_db_id"] = student[0]
        session["student_id"] = student[1]
        session["student_name"] = student[2]
        session["student_email"] = student[3]
        session["student_department"] = student[5]
        session["student_semester"] = student[6]
        session["student_section"] = student[7]
        session["student_photo"] = student[9]

        session.permanent = True

        # -------------------------------------------------
        # UPGRADE OLD PLAIN TEXT PASSWORD
        # -------------------------------------------------

        if stored_password == password:

            try:

                new_hash = generate_password_hash(
                    password
                )

                cursor = mysql.connection.cursor()

                cursor.execute(
                    """
                    UPDATE students
                    SET password = %s
                    WHERE id = %s
                    """,
                    (
                        new_hash,
                        student[0]
                    )
                )

                mysql.connection.commit()

                cursor.close()

            except Exception as e:

                mysql.connection.rollback()

                print(
                    "PASSWORD HASH UPGRADE ERROR:",
                    repr(e)
                )

        # -------------------------------------------------
        # LOGIN SUCCESS
        # -------------------------------------------------

        flash(
            "Welcome, " + str(student[2]) + "!",
            "success"
        )

        return redirect(
            url_for(
                "student_auth.dashboard"
            )
        )

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    return render_template(
        "student/login.html"
    )


# =========================================================
# STUDENT PROFILE
# =========================================================

@student_auth.route(
    "/profile",
    methods=["GET", "POST"]
)
def profile():

    # -----------------------------------------------------
    # LOGIN CHECK
    # -----------------------------------------------------

    if "student_db_id" not in session:

        return redirect(
            url_for(
                "student_auth.login"
            )
        )

    student_db_id = session["student_db_id"]

    cursor = mysql.connection.cursor()

    try:

        # =================================================
        # POST - UPDATE PROFILE
        # =================================================

        if request.method == "POST":

            full_name = request.form.get(
                "full_name",
                ""
            ).strip()

            email = request.form.get(
                "email",
                ""
            ).strip()

            phone = request.form.get(
                "phone",
                ""
            ).strip()

            if not full_name:

                flash(
                    "Full name is required.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "student_auth.profile"
                    )
                )

            # -------------------------------------------------
            # OLD PHOTO
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT photo
                FROM students
                WHERE id = %s
                LIMIT 1
                """,
                (student_db_id,)
            )

            old_result = cursor.fetchone()

            old_photo = (
                old_result[0]
                if old_result
                else None
            )

            new_photo = old_photo

            # -------------------------------------------------
            # PHOTO UPLOAD
            # -------------------------------------------------

            photo = request.files.get(
                "photo"
            )

            if photo and photo.filename:

                original_name = secure_filename(
                    photo.filename
                )

                allowed_extensions = {
                    "jpg",
                    "jpeg",
                    "png",
                    "webp"
                }

                extension = (
                    original_name
                    .rsplit(".", 1)[1]
                    .lower()
                    if "." in original_name
                    else ""
                )

                if extension not in allowed_extensions:

                    flash(
                        "Only JPG, JPEG, PNG and WEBP images are allowed.",
                        "danger"
                    )

                    return redirect(
                        url_for(
                            "student_auth.profile"
                        )
                    )

                upload_folder = os.path.join(
                    "static",
                    "uploads",
                    "students"
                )

                os.makedirs(
                    upload_folder,
                    exist_ok=True
                )

                new_photo = (
                    str(uuid.uuid4())
                    + "."
                    + extension
                )

                photo_path = os.path.join(
                    upload_folder,
                    new_photo
                )

                photo.save(
                    photo_path
                )

                # Delete old photo
                if old_photo:

                    old_photo_path = os.path.join(
                        upload_folder,
                        old_photo
                    )

                    if os.path.exists(
                        old_photo_path
                    ):

                        try:
                            os.remove(
                                old_photo_path
                            )
                        except Exception:
                            pass

            # -------------------------------------------------
            # UPDATE DATABASE
            # -------------------------------------------------

            cursor.execute(
                """
                UPDATE students
                SET
                    full_name = %s,
                    email = %s,
                    phone = %s,
                    photo = %s
                WHERE id = %s
                """,
                (
                    full_name,
                    email,
                    phone,
                    new_photo,
                    student_db_id
                )
            )

            mysql.connection.commit()

            # -------------------------------------------------
            # UPDATE SESSION
            # -------------------------------------------------

            session["student_name"] = full_name
            session["student_email"] = email
            session["student_photo"] = new_photo

            flash(
                "Profile updated successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "student_auth.profile"
                )
            )

        # =================================================
        # GET PROFILE
        # =================================================

        cursor.execute(
            """
            SELECT
                id,
                student_id,
                full_name,
                email,
                phone,
                department,
                semester,
                section,
                photo
            FROM students
            WHERE id = %s
            LIMIT 1
            """,
            (student_db_id,)
        )

        student = cursor.fetchone()

        if not student:

            session.clear()

            return redirect(
                url_for(
                    "student_auth.login"
                )
            )

        return render_template(
            "student/profile.html",
            student=student
        )

    except Exception as e:

        mysql.connection.rollback()

        print(
            "STUDENT PROFILE ERROR:",
            repr(e)
        )

        flash(
            "Unable to update profile. Please try again.",
            "danger"
        )

        return redirect(
            url_for(
                "student_auth.profile"
            )
        )

    finally:

        cursor.close()


# =========================================================
# STUDENT DASHBOARD
# =========================================================

@student_auth.route(
    "/dashboard"
)
def dashboard():

    # -----------------------------------------------------
    # LOGIN CHECK
    # -----------------------------------------------------

    if "student_db_id" not in session:

        return redirect(
            url_for(
                "student_auth.login"
            )
        )

    student_db_id = session["student_db_id"]

    cursor = mysql.connection.cursor()

    try:

        # =================================================
        # STUDENT INFORMATION
        # =================================================

        cursor.execute(
            """
            SELECT
                id,
                student_id,
                full_name,
                email,
                phone,
                department,
                semester,
                section,
                photo
            FROM students
            WHERE id = %s
            LIMIT 1
            """,
            (student_db_id,)
        )

        student = cursor.fetchone()

        if not student:

            session.clear()

            return redirect(
                url_for(
                    "student_auth.login"
                )
            )

        # =================================================
        # TOTAL SUBJECTS
        # =================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM subjects
            WHERE semester = %s
            """,
            (student[6],)
        )

        total_subjects = (
            cursor.fetchone()[0] or 0
        )

        # =================================================
        # TOTAL PRESENT
        # =================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM attendance
            WHERE student_id = %s
            AND status = 'Present'
            """,
            (student_db_id,)
        )

        total_present = (
            cursor.fetchone()[0] or 0
        )

        # =================================================
        # TOTAL ABSENT
        # =================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM attendance
            WHERE student_id = %s
            AND status = 'Absent'
            """,
            (student_db_id,)
        )

        total_absent = (
            cursor.fetchone()[0] or 0
        )

        # =================================================
        # TOTAL ATTENDANCE
        # =================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM attendance
            WHERE student_id = %s
            """,
            (student_db_id,)
        )

        total_attendance = (
            cursor.fetchone()[0] or 0
        )

        # =================================================
        # ATTENDANCE PERCENTAGE
        # =================================================

        if total_attendance > 0:

            attendance_percentage = round(
                (
                    total_present /
                    total_attendance
                ) * 100,
                1
            )

        else:

            attendance_percentage = 0

        # =================================================
        # TODAY ATTENDANCE
        # =================================================

        cursor.execute(
            """
            SELECT
                a.id,
                a.attendance_date,
                a.attendance_time,
                a.attendance_method,
                a.status,
                s.subject_code,
                s.subject_name
            FROM attendance a

            LEFT JOIN attendance_sessions ats
                ON a.session_id = ats.id

            LEFT JOIN subjects s
                ON ats.subject_id = s.id

            WHERE a.student_id = %s

            AND a.attendance_date = CURDATE()

            ORDER BY
                a.attendance_time DESC
            """,
            (student_db_id,)
        )

        today_attendance = cursor.fetchall()

        # =================================================
        # RECENT ATTENDANCE
        # =================================================

        cursor.execute(
            """
            SELECT
                a.id,
                a.attendance_date,
                a.attendance_time,
                a.attendance_method,
                a.status,
                s.subject_code,
                s.subject_name
            FROM attendance a

            LEFT JOIN attendance_sessions ats
                ON a.session_id = ats.id

            LEFT JOIN subjects s
                ON ats.subject_id = s.id

            WHERE a.student_id = %s

            ORDER BY
                a.attendance_date DESC,
                a.attendance_time DESC

            LIMIT 10
            """,
            (student_db_id,)
        )

        recent_attendance = cursor.fetchall()

        # =================================================
        # SUBJECT-WISE ATTENDANCE
        # =================================================

        cursor.execute(
            """
            SELECT
                s.id,
                s.subject_code,
                s.subject_name,

                COUNT(a.id) AS total_classes,

                SUM(
                    CASE
                        WHEN a.status = 'Present'
                        THEN 1
                        ELSE 0
                    END
                ) AS present_count,

                SUM(
                    CASE
                        WHEN a.status = 'Absent'
                        THEN 1
                        ELSE 0
                    END
                ) AS absent_count

            FROM subjects s

            LEFT JOIN attendance_sessions ats
                ON ats.subject_id = s.id

            LEFT JOIN attendance a
                ON a.session_id = ats.id
                AND a.student_id = %s

            WHERE s.semester = %s

            GROUP BY
                s.id,
                s.subject_code,
                s.subject_name

            ORDER BY
                s.subject_code
            """,
            (
                student_db_id,
                student[6]
            )
        )

        subject_attendance_raw = cursor.fetchall()

    except Exception as e:

        mysql.connection.rollback()

        print(
            "STUDENT DASHBOARD ERROR:",
            repr(e)
        )

        cursor.close()

        flash(
            "Unable to load dashboard.",
            "danger"
        )

        return redirect(
            url_for(
                "student_auth.login"
            )
        )

    finally:

        try:
            cursor.close()
        except Exception:
            pass

    # =====================================================
    # PROCESS SUBJECT ATTENDANCE
    # =====================================================

    subject_attendance = []

    for row in subject_attendance_raw:

        total_classes = int(
            row[3] or 0
        )

        present_count = int(
            row[4] or 0
        )

        absent_count = int(
            row[5] or 0
        )

        if total_classes > 0:

            percentage = round(
                (
                    present_count /
                    total_classes
                ) * 100,
                1
            )

        else:

            percentage = 0

        subject_attendance.append({

            "id": row[0],

            "code": row[1],

            "name": row[2],

            "total": total_classes,

            "present": present_count,

            "absent": absent_count,

            "percentage": percentage

        })

    # =====================================================
    # RENDER
    # =====================================================

    return render_template(
        "student/dashboard.html",

        student=student,

        total_subjects=total_subjects,

        total_present=total_present,

        total_absent=total_absent,

        total_attendance=total_attendance,

        attendance_percentage=attendance_percentage,

        today_attendance=today_attendance,

        recent_attendance=recent_attendance,

        subject_attendance=subject_attendance
    )


# =========================================================
# STUDENT SUBJECTS
# =========================================================

@student_auth.route(
    "/subjects"
)
def subjects():

    if "student_db_id" not in session:
        return redirect(
            url_for(
                "student_auth.login"
            )
        )

    student_db_id = session["student_db_id"]

    cursor = mysql.connection.cursor()

    try:

        # =================================================
        # STUDENT
        # =================================================

        cursor.execute(
            """
            SELECT
                id,
                student_id,
                full_name,
                email,
                phone,
                department,
                semester,
                section,
                photo
            FROM students
            WHERE id = %s
            LIMIT 1
            """,
            (student_db_id,)
        )

        student = cursor.fetchone()

        if not student:

            session.clear()

            return redirect(
                url_for(
                    "student_auth.login"
                )
            )

        semester = student[6]

        # =================================================
        # SUBJECTS
        # =================================================

        cursor.execute(
            """
            SELECT
                s.id,
                s.subject_code,
                s.subject_name,
                s.semester,

                COALESCE(
                    t.full_name,
                    'Not Assigned'
                ) AS teacher_name,

                COUNT(a.id) AS total_classes,

                COALESCE(
                    SUM(
                        CASE
                            WHEN a.status = 'Present'
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS present_count,

                COALESCE(
                    SUM(
                        CASE
                            WHEN a.status = 'Absent'
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS absent_count

            FROM subjects s

            LEFT JOIN teachers t
                ON s.teacher_id = t.id

            LEFT JOIN attendance_sessions ats
                ON ats.subject_id = s.id

            LEFT JOIN attendance a
                ON a.session_id = ats.id
                AND a.student_id = %s

            WHERE s.semester = %s

            GROUP BY
                s.id,
                s.subject_code,
                s.subject_name,
                s.semester,
                t.full_name

            ORDER BY
                s.subject_code
            """,
            (
                student_db_id,
                semester
            )
        )

        subject_rows = cursor.fetchall()

    except Exception as e:

        mysql.connection.rollback()

        print(
            "STUDENT SUBJECT ERROR:",
            repr(e)
        )

        cursor.close()

        flash(
            "Unable to load subjects.",
            "danger"
        )

        return redirect(
            url_for(
                "student_auth.dashboard"
            )
        )

    finally:

        try:
            cursor.close()
        except Exception:
            pass

    # =====================================================
    # PROCESS
    # =====================================================

    subject_list = []

    for row in subject_rows:

        total_classes = int(
            row[5] or 0
        )

        present_count = int(
            row[6] or 0
        )

        absent_count = int(
            row[7] or 0
        )

        teacher_name = (
            row[4]
            if row[4]
            else "Not Assigned"
        )

        if total_classes > 0:

            percentage = round(
                (
                    present_count /
                    total_classes
                ) * 100,
                1
            )

        else:

            percentage = 0

        subject_list.append({

            "id": row[0],

            "code": row[1],

            "name": row[2],

            "semester": row[3],

            "teacher_name": teacher_name,

            "total": total_classes,

            "present": present_count,

            "absent": absent_count,

            "percentage": percentage

        })

    return render_template(
        "student/subjects.html",
        student=student,
        subjects=subject_list
    )


# =========================================================
# STUDENT ATTENDANCE
# =========================================================

@student_auth.route(
    "/attendance"
)
def attendance():

    if "student_db_id" not in session:
        return redirect(
            url_for(
                "student_auth.login"
            )
        )

    student_db_id = session["student_db_id"]

    cursor = mysql.connection.cursor()

    try:

        # =================================================
        # STUDENT
        # =================================================

        cursor.execute(
            """
            SELECT
                id,
                student_id,
                full_name,
                email,
                phone,
                department,
                semester,
                section,
                photo
            FROM students
            WHERE id = %s
            LIMIT 1
            """,
            (student_db_id,)
        )

        student = cursor.fetchone()

        if not student:

            session.clear()

            return redirect(
                url_for(
                    "student_auth.login"
                )
            )

        # =================================================
        # ATTENDANCE RECORDS
        # =================================================

        cursor.execute(
            """
            SELECT
                a.id,
                a.attendance_date,
                a.attendance_time,
                a.attendance_method,
                a.status,
                s.subject_code,
                s.subject_name

            FROM attendance a

            LEFT JOIN attendance_sessions ats
                ON a.session_id = ats.id

            LEFT JOIN subjects s
                ON ats.subject_id = s.id

            WHERE a.student_id = %s

            ORDER BY
                a.attendance_date DESC,
                a.attendance_time DESC
            """,
            (student_db_id,)
        )

        attendance_records = cursor.fetchall()

    except Exception as e:

        mysql.connection.rollback()

        print(
            "STUDENT ATTENDANCE ERROR:",
            repr(e)
        )

        cursor.close()

        flash(
            "Unable to load attendance.",
            "danger"
        )

        return redirect(
            url_for(
                "student_auth.dashboard"
            )
        )

    finally:

        try:
            cursor.close()
        except Exception:
            pass

    # =====================================================
    # STATISTICS
    # =====================================================

    total_records = len(
        attendance_records
    )

    total_present = 0

    total_absent = 0

    for record in attendance_records:

        status = str(
            record[4] or ""
        ).strip().lower()

        if status == "present":

            total_present += 1

        elif status == "absent":

            total_absent += 1

    if total_records > 0:

        attendance_percentage = round(
            (
                total_present /
                total_records
            ) * 100,
            1
        )

    else:

        attendance_percentage = 0

    return render_template(
        "student/attendance.html",

        student=student,

        attendance_records=attendance_records,

        total_records=total_records,

        total_present=total_present,

        total_absent=total_absent,

        attendance_percentage=attendance_percentage
    )


# =========================================================
# STUDENT REPORT
# =========================================================

@student_auth.route(
    "/report"
)
def report():

    if "student_db_id" not in session:

        return redirect(
            url_for(
                "student_auth.login"
            )
        )

    return redirect(
        url_for(
            "student_auth.attendance"
        )
    )


# =========================================================
# STUDENT MARKSHEET
# =========================================================
@student_auth.route("/marksheet")
def marksheet():

    # -----------------------------------------------------
    # LOGIN CHECK
    # -----------------------------------------------------
    if "student_db_id" not in session:
        return redirect(
            url_for("student_auth.login")
        )

    student_db_id = session["student_db_id"]

    cursor = mysql.connection.cursor()

    try:

        # =================================================
        # GET STUDENT INFORMATION
        # =================================================
        cursor.execute(
            """
            SELECT
                id,
                student_id,
                full_name,
                email,
                phone,
                department,
                semester,
                section,
                photo
            FROM students
            WHERE id = %s
            LIMIT 1
            """,
            (student_db_id,)
        )

        student = cursor.fetchone()

        if not student:
            session.clear()

            return redirect(
                url_for("student_auth.login")
            )

        # =================================================
        # GET MARKSHEET
        # =================================================
        cursor.execute(
            """
            SELECT
                m.id,
                s.subject_code,
                s.subject_name,
                s.theory_full_marks,
                s.practical_full_marks,
                s.full_marks,
                s.pass_marks,
                m.theory_marks,
                m.practical_marks,
                m.total_marks,
                m.grade,
                m.grade_point,
                m.remarks,
                m.created_at,
                m.updated_at
            FROM marksheets m
            INNER JOIN subjects s
                ON s.id = m.subject_id
            WHERE m.student_id = %s
            ORDER BY s.subject_code ASC
            """,
            (student_db_id,)
        )

        raw_marksheets = cursor.fetchall()

        # =================================================
        # SAFE NUMBER CONVERTER
        # =================================================
        def to_number(value, default=0.0):

            if value is None:
                return default

            try:
                # bytes -> string
                if isinstance(value, bytes):
                    value = value.decode("utf-8", errors="ignore")

                value = str(value).strip()

                if value == "":
                    return default

                return float(value)

            except (ValueError, TypeError):
                return default

        # =================================================
        # PROCESS MARKSHEET
        # =================================================
        marksheets = []

        total_full_marks = 0.0
        total_obtained_marks = 0.0

        total_grade_points = 0.0
        grade_point_count = 0

        passed_subjects = 0
        failed_subjects = 0

        for original_row in raw_marksheets:

            row = list(original_row)

            # -------------------------------------------------
            # FULL MARKS
            # -------------------------------------------------
            theory_full_marks = to_number(row[3])
            practical_full_marks = to_number(row[4])
            full_marks = to_number(row[5])
            pass_marks = to_number(row[6])

            # -------------------------------------------------
            # OBTAINED MARKS
            # -------------------------------------------------
            theory_marks = to_number(row[7])
            practical_marks = to_number(row[8])
            total_marks = to_number(row[9])

            # -------------------------------------------------
            # GRADE
            # -------------------------------------------------
            grade = (
                str(row[10]).strip()
                if row[10] is not None
                else ""
            )

            # -------------------------------------------------
            # GRADE POINT
            # -------------------------------------------------
            grade_point = None

            if row[11] is not None:

                try:

                    if isinstance(row[11], bytes):
                        gp_value = row[11].decode(
                            "utf-8",
                            errors="ignore"
                        )
                    else:
                        gp_value = str(row[11]).strip()

                    if gp_value != "":
                        grade_point = float(gp_value)

                except (ValueError, TypeError):
                    grade_point = None

            # -------------------------------------------------
            # REMARKS
            # -------------------------------------------------
            remarks = (
                str(row[12]).strip()
                if row[12] is not None
                else ""
            )

            # -------------------------------------------------
            # REBUILD ROW
            # -------------------------------------------------
            processed_row = (
                row[0],                  # id
                row[1],                  # subject code
                row[2],                  # subject name
                theory_full_marks,       # theory full
                practical_full_marks,    # practical full
                full_marks,              # full marks
                pass_marks,              # pass marks
                theory_marks,            # theory obtained
                practical_marks,         # practical obtained
                total_marks,             # total obtained
                grade,                   # grade
                grade_point,             # grade point
                remarks,                 # remarks
                row[13],                 # created_at
                row[14]                  # updated_at
            )

            marksheets.append(processed_row)

            # -------------------------------------------------
            # TOTALS
            # -------------------------------------------------
            total_full_marks += full_marks
            total_obtained_marks += total_marks

            # -------------------------------------------------
            # PASS / FAIL
            # -------------------------------------------------
            if total_marks >= pass_marks:
                passed_subjects += 1
            else:
                failed_subjects += 1

            # -------------------------------------------------
            # GPA
            # -------------------------------------------------
            if grade_point is not None:

                total_grade_points += grade_point
                grade_point_count += 1

        # =================================================
        # OVERALL PERCENTAGE
        # =================================================
        if total_full_marks > 0:

            overall_percentage = round(
                (
                    total_obtained_marks /
                    total_full_marks
                ) * 100,
                2
            )

        else:

            overall_percentage = 0.0

        # =================================================
        # AVERAGE GPA
        # =================================================
        if grade_point_count > 0:

            average_gpa = round(
                total_grade_points /
                grade_point_count,
                2
            )

        else:

            average_gpa = 0.0

        # =================================================
        # TOTAL SUBJECTS
        # =================================================
        total_marksheets = len(marksheets)

        # =================================================
        # CLOSE CURSOR
        # =================================================
        cursor.close()

        # =================================================
        # RENDER
        # =================================================
        return render_template(
            "student/marksheet.html",

            student=student,

            marksheets=marksheets,

            total_subjects=total_marksheets,

            passed_subjects=passed_subjects,

            failed_subjects=failed_subjects,

            total_full_marks=total_full_marks,

            total_obtained_marks=total_obtained_marks,

            overall_percentage=overall_percentage,

            average_gpa=average_gpa
        )

    except Exception as e:

        # -------------------------------------------------
        # DATABASE ROLLBACK
        # -------------------------------------------------
        try:
            mysql.connection.rollback()
        except Exception:
            pass

        # -------------------------------------------------
        # CLOSE CURSOR
        # -------------------------------------------------
        try:
            cursor.close()
        except Exception:
            pass

        # -------------------------------------------------
        # PRINT REAL ERROR IN TERMINAL
        # -------------------------------------------------
        print("\n========================================")
        print("STUDENT MARKSHEET ERROR")
        print("========================================")
        print("ERROR TYPE :", type(e).__name__)
        print("ERROR      :", str(e))
        print("========================================\n")

        # -------------------------------------------------
        # USER MESSAGE
        # -------------------------------------------------
        flash(
            "Unable to load marksheet. Please try again.",
            "danger"
        )

        return redirect(
            url_for("student_auth.dashboard")
        )


# =========================================================
# STUDENT CHANGE PASSWORD
# =========================================================

@student_auth.route(
    "/change-password",
    methods=["GET", "POST"]
)
def change_password():

    # =====================================================
    # LOGIN CHECK
    # =====================================================

    if "student_db_id" not in session:

        return redirect(
            url_for(
                "student_auth.login"
            )
        )

    student_db_id = session["student_db_id"]

    cursor = mysql.connection.cursor()

    try:

        # =================================================
        # GET STUDENT
        # =================================================

        cursor.execute(
            """
            SELECT
                id,
                student_id,
                full_name,
                photo
            FROM students
            WHERE id = %s
            LIMIT 1
            """,
            (student_db_id,)
        )

        student = cursor.fetchone()

        if not student:

            session.clear()

            return redirect(
                url_for(
                    "student_auth.login"
                )
            )

        student_id = student[1]

        student_name = student[2]

        student_photo = student[3]

        # =================================================
        # POST
        # =================================================

        if request.method == "POST":

            current_password = request.form.get(
                "current_password",
                ""
            ).strip()

            new_password = request.form.get(
                "new_password",
                ""
            ).strip()

            confirm_password = request.form.get(
                "confirm_password",
                ""
            ).strip()

            # -------------------------------------------------
            # EMPTY
            # -------------------------------------------------

            if (
                not current_password
                or not new_password
                or not confirm_password
            ):

                flash(
                    "All password fields are required.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "student_auth.change_password"
                    )
                )

            # -------------------------------------------------
            # LENGTH
            # -------------------------------------------------

            if len(new_password) < 8:

                flash(
                    "New password must be at least 8 characters.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "student_auth.change_password"
                    )
                )

            # -------------------------------------------------
            # MATCH
            # -------------------------------------------------

            if new_password != confirm_password:

                flash(
                    "New passwords do not match.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "student_auth.change_password"
                    )
                )

            # =================================================
            # GET CURRENT PASSWORD
            # =================================================

            cursor.execute(
                """
                SELECT password
                FROM students
                WHERE id = %s
                LIMIT 1
                """,
                (student_db_id,)
            )

            result = cursor.fetchone()

            if not result:

                flash(
                    "Student account not found.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "student_auth.login"
                    )
                )

            stored_password = result[0]

            password_valid = False

            # -------------------------------------------------
            # HASHED PASSWORD
            # -------------------------------------------------

            if stored_password:

                try:

                    password_valid = check_password_hash(
                        str(stored_password),
                        current_password
                    )

                except Exception:

                    password_valid = False

                # -------------------------------------------------
                # OLD PLAINTEXT SUPPORT
                # -------------------------------------------------

                if not password_valid:

                    password_valid = (
                        str(stored_password)
                        == current_password
                    )

            # -------------------------------------------------
            # WRONG PASSWORD
            # -------------------------------------------------

            if not password_valid:

                flash(
                    "Current password is incorrect.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "student_auth.change_password"
                    )
                )

            # =================================================
            # NEW PASSWORD HASH
            # =================================================

            new_password_hash = generate_password_hash(
                new_password
            )

            # =================================================
            # UPDATE
            # =================================================

            cursor.execute(
                """
                UPDATE students
                SET password = %s
                WHERE id = %s
                """,
                (
                    new_password_hash,
                    student_db_id
                )
            )

            mysql.connection.commit()

            flash(
                "Password changed successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "student_auth.dashboard"
                )
            )

        # =================================================
        # GET
        # =================================================

        return render_template(
            "student/change_password.html",
            student=student,
            student_id=student_id,
            student_name=student_name,
            student_photo=student_photo
        )

    except Exception as e:

        mysql.connection.rollback()

        print(
            "STUDENT CHANGE PASSWORD ERROR:",
            repr(e)
        )

        flash(
            "Unable to change password. Please try again.",
            "danger"
        )

        return redirect(
            url_for(
                "student_auth.change_password"
            )
        )

    finally:

        try:
            cursor.close()
        except Exception:
            pass


# =========================================================
# STUDENT LOGOUT
# =========================================================

@student_auth.route(
    "/logout"
)
def logout():

    # -----------------------------------------------------
    # REMOVE ONLY STUDENT SESSION
    # -----------------------------------------------------

    session.pop(
        "student_db_id",
        None
    )

    session.pop(
        "student_id",
        None
    )

    session.pop(
        "student_name",
        None
    )

    session.pop(
        "student_email",
        None
    )

    session.pop(
        "student_department",
        None
    )

    session.pop(
        "student_semester",
        None
    )

    session.pop(
        "student_section",
        None
    )

    session.pop(
        "student_photo",
        None
    )

    # -----------------------------------------------------
    # NO FLASH MESSAGE
    # -----------------------------------------------------
    # Do NOT use flash() here.
    #
    # Therefore student login page will NOT show:
    # "You have been logged out successfully."
    # -----------------------------------------------------

    return redirect(
        url_for(
            "student_auth.login"
        )
    )