from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    send_file
)

from extensions import mysql

from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer
)

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

import io


# ============================================================
# STUDENT PORTAL BLUEPRINT
# ============================================================

student_portal = Blueprint(
    "student_portal",
    __name__,
    url_prefix="/student"
)


# ============================================================
# STUDENT LOGIN
# ============================================================

@student_portal.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    # --------------------------------------------------------
    # Already logged in
    # --------------------------------------------------------

    if "student_id" in session:

        return redirect(
            url_for(
                "student_portal.dashboard"
            )
        )


    # --------------------------------------------------------
    # POST LOGIN
    # --------------------------------------------------------

    if request.method == "POST":

        student_id = request.form.get(
            "student_id",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()


        # ----------------------------------------------------
        # Validation
        # ----------------------------------------------------

        if not student_id or not password:

            flash(
                "Please enter Student ID and Password.",
                "warning"
            )

            return redirect(
                url_for(
                    "student_portal.login"
                )
            )


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
                WHERE student_id=%s
                AND password=%s
                LIMIT 1
                """,
                (
                    student_id,
                    password
                )
            )

            student = cursor.fetchone()


        except Exception as e:

            flash(
                f"Login error: {e}",
                "danger"
            )

            student = None


        finally:

            cursor.close()


        # ----------------------------------------------------
        # Invalid Login
        # ----------------------------------------------------

        if not student:

            flash(
                "Invalid Student ID or Password.",
                "danger"
            )

            return redirect(
                url_for(
                    "student_portal.login"
                )
            )


        # ====================================================
        # CREATE STUDENT SESSION
        # ====================================================

        session["student_db_id"] = student[0]

        session["student_id"] = student[1]

        session["student_name"] = student[2]

        session["student_email"] = student[3]

        session["student_department"] = student[5]

        session["student_semester"] = student[6]

        session["student_section"] = student[7]

        session["student_photo"] = student[8]


        # ====================================================
        # REDIRECT
        # ====================================================

        return redirect(
            url_for(
                "student_portal.dashboard"
            )
        )


    # ========================================================
    # LOGIN PAGE
    # ========================================================

    return render_template(
        "student/login.html"
    )


# ============================================================
# STUDENT DASHBOARD
# ============================================================

@student_portal.route(
    "/dashboard"
)
def dashboard():

    if "student_id" not in session:

        return redirect(
            url_for(
                "student_portal.login"
            )
        )


    student_db_id = session["student_db_id"]


    cursor = mysql.connection.cursor()


    try:

        # ====================================================
        # STUDENT INFORMATION
        # ====================================================

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
            WHERE id=%s
            LIMIT 1
            """,
            (
                student_db_id,
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
                url_for(
                    "student_portal.login"
                )
            )


        # ====================================================
        # TOTAL ATTENDANCE
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM attendance
            WHERE student_id=%s
            """,
            (
                student_db_id,
            )
        )

        total = cursor.fetchone()[0] or 0


        # ====================================================
        # PRESENT
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM attendance
            WHERE student_id=%s
            AND status='Present'
            """,
            (
                student_db_id,
            )
        )

        present = cursor.fetchone()[0] or 0


        # ====================================================
        # ABSENT
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM attendance
            WHERE student_id=%s
            AND status='Absent'
            """,
            (
                student_db_id,
            )
        )

        absent = cursor.fetchone()[0] or 0


        # ====================================================
        # ATTENDANCE PERCENTAGE
        # ====================================================

        if total > 0:

            percentage = round(
                (present / total) * 100,
                2
            )

        else:

            percentage = 0


        # ====================================================
        # RECENT ATTENDANCE
        # ====================================================

        cursor.execute(
            """
            SELECT

                a.attendance_date,

                a.attendance_time,

                sub.subject_code,

                sub.subject_name,

                a.attendance_method,

                a.status

            FROM attendance a

            INNER JOIN attendance_sessions s
                ON a.session_id=s.id

            INNER JOIN subjects sub
                ON s.subject_id=sub.id

            WHERE a.student_id=%s

            ORDER BY
                a.attendance_date DESC,
                a.attendance_time DESC

            LIMIT 10
            """,
            (
                student_db_id,
            )
        )

        recent_attendance = cursor.fetchall()


        # ====================================================
        # SUBJECT-WISE ATTENDANCE
        # ====================================================

        cursor.execute(
            """
            SELECT

                sub.subject_code,

                sub.subject_name,

                COUNT(a.id) AS total,

                COALESCE(
                    SUM(a.status='Present'),
                    0
                ) AS present,

                COALESCE(
                    SUM(a.status='Absent'),
                    0
                ) AS absent

            FROM attendance a

            INNER JOIN attendance_sessions s
                ON a.session_id=s.id

            INNER JOIN subjects sub
                ON s.subject_id=sub.id

            WHERE a.student_id=%s

            GROUP BY
                sub.id,
                sub.subject_code,
                sub.subject_name

            ORDER BY
                sub.subject_code
            """,
            (
                student_db_id,
            )
        )

        subject_attendance = cursor.fetchall()


    except Exception as e:

        mysql.connection.rollback()

        flash(
            f"Dashboard loading error: {e}",
            "danger"
        )

        student = None

        total = 0

        present = 0

        absent = 0

        percentage = 0

        recent_attendance = []

        subject_attendance = []


    finally:

        cursor.close()


    return render_template(
        "student/dashboard.html",

        student=student,

        total=total,

        present=present,

        absent=absent,

        percentage=percentage,

        recent_attendance=recent_attendance,

        subject_attendance=subject_attendance
    )


# ============================================================
# MY ATTENDANCE
# ============================================================

@student_portal.route(
    "/attendance"
)
def attendance():

    if "student_id" not in session:

        return redirect(
            url_for(
                "student_portal.login"
            )
        )


    student_db_id = session["student_db_id"]


    cursor = mysql.connection.cursor()


    try:

        cursor.execute(
            """
            SELECT

                a.id,

                a.attendance_date,

                a.attendance_time,

                sub.subject_code,

                sub.subject_name,

                a.attendance_method,

                a.status,

                a.remarks

            FROM attendance a

            INNER JOIN attendance_sessions s
                ON a.session_id=s.id

            INNER JOIN subjects sub
                ON s.subject_id=sub.id

            WHERE a.student_id=%s

            ORDER BY

                a.attendance_date DESC,

                a.attendance_time DESC
            """,
            (
                student_db_id,
            )
        )

        records = cursor.fetchall()


        # ====================================================
        # COUNTS
        # ====================================================

        cursor.execute(
            """
            SELECT

                COUNT(*),

                COALESCE(
                    SUM(status='Present'),
                    0
                ),

                COALESCE(
                    SUM(status='Absent'),
                    0
                )

            FROM attendance

            WHERE student_id=%s
            """,
            (
                student_db_id,
            )
        )

        counts = cursor.fetchone()


        total = counts[0] or 0

        present = counts[1] or 0

        absent = counts[2] or 0


        if total > 0:

            percentage = round(
                (present / total) * 100,
                2
            )

        else:

            percentage = 0


    except Exception as e:

        mysql.connection.rollback()

        flash(
            f"Attendance loading error: {e}",
            "danger"
        )

        records = []

        total = 0

        present = 0

        absent = 0

        percentage = 0


    finally:

        cursor.close()


    return render_template(
        "student/attendance.html",

        records=records,

        total=total,

        present=present,

        absent=absent,

        percentage=percentage
    )


# ============================================================
# DOWNLOAD ATTENDANCE PDF
# ============================================================

@student_portal.route(
    "/attendance/download/pdf"
)
def download_attendance_pdf():

    if "student_id" not in session:

        return redirect(
            url_for(
                "student_portal.login"
            )
        )


    student_db_id = session["student_db_id"]


    cursor = mysql.connection.cursor()


    try:

        cursor.execute(
            """
            SELECT

                a.attendance_date,

                a.attendance_time,

                sub.subject_code,

                sub.subject_name,

                a.attendance_method,

                a.status

            FROM attendance a

            INNER JOIN attendance_sessions s
                ON a.session_id=s.id

            INNER JOIN subjects sub
                ON s.subject_id=sub.id

            WHERE a.student_id=%s

            ORDER BY

                a.attendance_date DESC,

                a.attendance_time DESC
            """,
            (
                student_db_id,
            )
        )

        rows = cursor.fetchall()


        # ====================================================
        # TOTAL COUNTS
        # ====================================================

        cursor.execute(
            """
            SELECT

                COUNT(*),

                COALESCE(
                    SUM(status='Present'),
                    0
                ),

                COALESCE(
                    SUM(status='Absent'),
                    0
                )

            FROM attendance

            WHERE student_id=%s
            """,
            (
                student_db_id,
            )
        )

        counts = cursor.fetchone()


    except Exception as e:

        flash(
            f"PDF generation error: {e}",
            "danger"
        )

        return redirect(
            url_for(
                "student_portal.attendance"
            )
        )


    finally:

        cursor.close()


    total = counts[0] or 0

    present = counts[1] or 0

    absent = counts[2] or 0


    if total > 0:

        percentage = round(
            (present / total) * 100,
            2
        )

    else:

        percentage = 0


    # ========================================================
    # CREATE PDF
    # ========================================================

    buffer = io.BytesIO()


    doc = SimpleDocTemplate(
        buffer,

        rightMargin=25,

        leftMargin=25,

        topMargin=30,

        bottomMargin=30
    )


    styles = getSampleStyleSheet()

    elements = []


    elements.append(
        Paragraph(
            "<b>AI Smart Attendance System</b>",
            styles["Title"]
        )
    )


    elements.append(
        Spacer(1, 8)
    )


    elements.append(
        Paragraph(
            "<b>Student Attendance Report</b>",
            styles["Heading2"]
        )
    )


    elements.append(
        Spacer(1, 10)
    )


    elements.append(
        Paragraph(
            f"<b>Student ID:</b> "
            f"{session.get('student_id', '-')}",
            styles["Normal"]
        )
    )


    elements.append(
        Paragraph(
            f"<b>Name:</b> "
            f"{session.get('student_name', '-')}",
            styles["Normal"]
        )
    )


    elements.append(
        Paragraph(
            f"<b>Department:</b> "
            f"{session.get('student_department', '-')}",
            styles["Normal"]
        )
    )


    elements.append(
        Paragraph(
            f"<b>Semester:</b> "
            f"{session.get('student_semester', '-')}",
            styles["Normal"]
        )
    )


    elements.append(
        Spacer(1, 10)
    )


    elements.append(
        Paragraph(
            f"<b>Total:</b> {total} &nbsp;&nbsp; "
            f"<b>Present:</b> {present} &nbsp;&nbsp; "
            f"<b>Absent:</b> {absent} &nbsp;&nbsp; "
            f"<b>Percentage:</b> {percentage}%",
            styles["Normal"]
        )
    )


    elements.append(
        Spacer(1, 15)
    )


    # ========================================================
    # TABLE
    # ========================================================

    data = [[
        "Date",
        "Time",
        "Subject",
        "Method",
        "Status"
    ]]


    for row in rows:

        data.append([
            str(row[0]),
            str(row[1]),
            f"{row[2]} - {row[3]}",
            str(row[4]),
            str(row[5])
        ])


    if len(data) == 1:

        data.append([
            "-",
            "-",
            "No attendance records",
            "-",
            "-"
        ])


    table = Table(
        data,
        repeatRows=1
    )


    table.setStyle(
        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.darkblue
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),

            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),

            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER"
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),

            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                7
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, 0),
                8
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, 0),
                8
            )

        ])
    )


    elements.append(table)


    doc.build(elements)

    buffer.seek(0)


    return send_file(
        buffer,

        as_attachment=True,

        download_name=(
            f"Student_Attendance_Report_"
            f"{session.get('student_id', 'student')}.pdf"
        ),

        mimetype="application/pdf"
    )


# ============================================================
# STUDENT PROFILE
# ============================================================

@student_portal.route(
    "/profile"
)
def profile():

    if "student_id" not in session:

        return redirect(
            url_for(
                "student_portal.login"
            )
        )


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
                photo,
                created_at

            FROM students

            WHERE id=%s

            LIMIT 1
            """,
            (
                session["student_db_id"],
            )
        )

        student = cursor.fetchone()


    finally:

        cursor.close()


    return render_template(
        "student/profile.html",
        student=student
    )


# ============================================================
# CHANGE PASSWORD
# ============================================================

@student_portal.route(
    "/change-password",
    methods=["GET", "POST"]
)
def change_password():

    if "student_id" not in session:

        return redirect(
            url_for(
                "student_portal.login"
            )
        )


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


        if not current_password:

            flash(
                "Enter your current password.",
                "warning"
            )

            return redirect(
                url_for(
                    "student_portal.change_password"
                )
            )


        if not new_password:

            flash(
                "Enter a new password.",
                "warning"
            )

            return redirect(
                url_for(
                    "student_portal.change_password"
                )
            )


        if new_password != confirm_password:

            flash(
                "New password and Confirm password do not match.",
                "danger"
            )

            return redirect(
                url_for(
                    "student_portal.change_password"
                )
            )


        cursor = mysql.connection.cursor()


        try:

            cursor.execute(
                """
                SELECT password
                FROM students
                WHERE id=%s
                LIMIT 1
                """,
                (
                    session["student_db_id"],
                )
            )

            student = cursor.fetchone()


            if not student:

                flash(
                    "Student account not found.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "student_portal.login"
                    )
                )


            if student[0] != current_password:

                flash(
                    "Current password is incorrect.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "student_portal.change_password"
                    )
                )


            cursor.execute(
                """
                UPDATE students

                SET password=%s

                WHERE id=%s
                """,
                (
                    new_password,
                    session["student_db_id"]
                )
            )


            mysql.connection.commit()


            flash(
                "Password changed successfully.",
                "success"
            )


            return redirect(
                url_for(
                    "student_portal.profile"
                )
            )


        except Exception as e:

            mysql.connection.rollback()

            flash(
                f"Password change error: {e}",
                "danger"
            )


        finally:

            cursor.close()


    return render_template(
        "student/change_password.html"
    )


# ============================================================
# STUDENT LOGOUT
# ============================================================

@student_portal.route(
    "/logout"
)
def logout():

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


    flash(
        "Student logged out successfully.",
        "success"
    )


    return redirect(
        url_for(
            "student_portal.login"
        )
    )