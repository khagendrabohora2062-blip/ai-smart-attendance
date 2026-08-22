from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    request,
    flash,
    send_file
)

from extensions import mysql

from openpyxl import Workbook
from io import BytesIO

from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle
)

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch


attendance = Blueprint(
    "attendance",
    __name__,
    url_prefix="/attendance"
)


# ==========================================================
# Attendance Session List
# ==========================================================
@attendance.route("/")
def index():

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT
            attendance_sessions.id,
            subjects.subject_name,
            teachers.full_name,
            attendance_sessions.session_date,
            attendance_sessions.start_time,
            attendance_sessions.end_time,
            attendance_sessions.session_status

        FROM attendance_sessions

        INNER JOIN subjects
            ON attendance_sessions.subject_id = subjects.id

        INNER JOIN teachers
            ON attendance_sessions.teacher_id = teachers.id

        ORDER BY attendance_sessions.id DESC
    """)

    sessions = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin/attendance.html",
        sessions=sessions
    )


# ==========================================================
# Add Attendance Session
# ==========================================================
@attendance.route("/add", methods=["GET", "POST"])
def add_session():

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    cursor = mysql.connection.cursor()

    if request.method == "POST":

        subject_id = request.form["subject_id"]
        teacher_id = request.form["teacher_id"]
        session_date = request.form["session_date"]
        start_time = request.form["start_time"]
        end_time = request.form["end_time"]
        session_status = request.form["session_status"]

        cursor.execute("""
            INSERT INTO attendance_sessions
            (
                subject_id,
                teacher_id,
                session_date,
                start_time,
                end_time,
                session_status
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
        """, (
            subject_id,
            teacher_id,
            session_date,
            start_time,
            end_time,
            session_status
        ))

        mysql.connection.commit()

        flash(
            "Attendance Session created successfully!",
            "success"
        )

        cursor.close()

        return redirect(
            url_for("attendance.index")
        )

    cursor.execute("""
        SELECT
            id,
            subject_name
        FROM subjects
        ORDER BY subject_name
    """)

    subjects = cursor.fetchall()

    cursor.execute("""
        SELECT
            id,
            full_name
        FROM teachers
        ORDER BY full_name
    """)

    teachers = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin/add_attendance.html",
        subjects=subjects,
        teachers=teachers
    )
# ==========================================================
# Edit Attendance Session
# ==========================================================
@attendance.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_session(id):

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    cursor = mysql.connection.cursor()

    if request.method == "POST":

        subject_id = request.form["subject_id"]
        teacher_id = request.form["teacher_id"]
        session_date = request.form["session_date"]
        start_time = request.form["start_time"]
        end_time = request.form["end_time"]
        session_status = request.form["session_status"]

        cursor.execute("""
            UPDATE attendance_sessions
            SET
                subject_id=%s,
                teacher_id=%s,
                session_date=%s,
                start_time=%s,
                end_time=%s,
                session_status=%s
            WHERE id=%s
        """, (
            subject_id,
            teacher_id,
            session_date,
            start_time,
            end_time,
            session_status,
            id
        ))

        mysql.connection.commit()

        flash(
            "Attendance Session updated successfully!",
            "success"
        )

        cursor.close()

        return redirect(
            url_for("attendance.index")
        )

    cursor.execute("""
        SELECT
            id,
            subject_id,
            teacher_id,
            session_date,
            start_time,
            end_time,
            session_status
        FROM attendance_sessions
        WHERE id=%s
    """, (id,))

    attendance_session = cursor.fetchone()

    cursor.execute("""
        SELECT
            id,
            subject_name
        FROM subjects
        ORDER BY subject_name
    """)

    subjects = cursor.fetchall()

    cursor.execute("""
        SELECT
            id,
            full_name
        FROM teachers
        ORDER BY full_name
    """)

    teachers = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin/edit_attendance.html",
        attendance_session=attendance_session,
        subjects=subjects,
        teachers=teachers
    )


# ==========================================================
# Delete Attendance Session
# ==========================================================
@attendance.route("/delete/<int:id>")
def delete_session(id):

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    cursor = mysql.connection.cursor()

    cursor.execute(
        """
        DELETE FROM attendance_sessions
        WHERE id=%s
        """,
        (id,)
    )

    mysql.connection.commit()

    cursor.close()

    flash(
        "Attendance Session deleted successfully!",
        "success"
    )

    return redirect(
        url_for("attendance.index")
    )
# ==========================================================
# Attendance Report
# ==========================================================
@attendance.route("/report")
def report():

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    search = request.args.get("search", "").strip()
    date = request.args.get("date", "").strip()
    method = request.args.get("method", "").strip()

    cursor = mysql.connection.cursor()

    query = """
        SELECT

            attendance.id,

            students.photo,

            students.student_id,

            students.full_name,

            students.department,

            attendance.attendance_date,

            DAYNAME(attendance.attendance_date) AS day_name,

            attendance.attendance_time,

            attendance.attendance_method,

            attendance.status

        FROM attendance

        INNER JOIN students
            ON attendance.student_id = students.id

        WHERE 1=1
    """

    params = []

    # ----------------------------------
    # Search
    # ----------------------------------
    if search:

        query += """
            AND
            (
                students.student_id LIKE %s
                OR students.full_name LIKE %s
            )
        """

        params.append(f"%{search}%")
        params.append(f"%{search}%")

    # ----------------------------------
    # Filter by Date
    # ----------------------------------
    if date:

        query += """
            AND attendance.attendance_date=%s
        """

        params.append(date)

    # ----------------------------------
    # Filter by Method
    # ----------------------------------
    if method:

        query += """
            AND attendance.attendance_method=%s
        """

        params.append(method)

    query += """
        ORDER BY
        attendance.attendance_date DESC,
        attendance.attendance_time DESC
    """

    cursor.execute(
        query,
        tuple(params)
    )

    attendance_data = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin/attendance_report.html",
        attendance=attendance_data
    )
# ==========================================================
# Export Attendance Report to Excel
# ==========================================================
@attendance.route("/export/excel")
def export_excel():

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT

            students.student_id,

            students.full_name,

            students.department,

            attendance.attendance_date,

            DAYNAME(attendance.attendance_date),

            attendance.attendance_time,

            attendance.attendance_method,

            attendance.status

        FROM attendance

        INNER JOIN students
            ON attendance.student_id = students.id

        ORDER BY
            attendance.attendance_date DESC,
            attendance.attendance_time DESC
    """)

    data = cursor.fetchall()

    cursor.close()

    workbook = Workbook()

    sheet = workbook.active

    sheet.title = "Attendance Report"

    headers = [
        "Student ID",
        "Full Name",
        "Department",
        "Date",
        "Day",
        "Time",
        "Method",
        "Status"
    ]

    for col, header in enumerate(headers, start=1):

        sheet.cell(
            row=1,
            column=col
        ).value = header

    row_no = 2

    for row in data:

        for col_no, value in enumerate(row, start=1):

            sheet.cell(
                row=row_no,
                column=col_no
            ).value = value

        row_no += 1

    output = BytesIO()

    workbook.save(output)

    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="attendance_report.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ==========================================================
# Export Attendance Report to PDF
# ==========================================================
@attendance.route("/export/pdf")
def export_pdf():

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT

            students.student_id,

            students.full_name,

            students.department,

            attendance.attendance_date,

            DAYNAME(attendance.attendance_date),

            attendance.attendance_time,

            attendance.attendance_method,

            attendance.status

        FROM attendance

        INNER JOIN students
            ON attendance.student_id = students.id

        ORDER BY
            attendance.attendance_date DESC,
            attendance.attendance_time DESC
    """)

    data = cursor.fetchall()

    cursor.close()

    output = BytesIO()

    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20
    )

    table_data = [[
        "Student ID",
        "Name",
        "Department",
        "Date",
        "Day",
        "Time",
        "Method",
        "Status"
    ]]

    for row in data:

        table_data.append([
            str(row[0]),
            str(row[1]),
            str(row[2]),
            str(row[3]),
            str(row[4]),
            str(row[5]),
            str(row[6]),
            str(row[7])
        ])

    table = Table(
        table_data,
        colWidths=[
            1.0 * inch,
            1.5 * inch,
            1.2 * inch,
            0.9 * inch,
            0.8 * inch,
            0.9 * inch,
            0.8 * inch,
            0.8 * inch
        ]
    )

    table.setStyle(TableStyle([

        ("BACKGROUND", (0,0), (-1,0), colors.darkblue),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),

        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),

        ("FONTSIZE", (0,0), (-1,-1), 9),

        ("GRID", (0,0), (-1,-1), 0.5, colors.black),

        ("BACKGROUND", (0,1), (-1,-1), colors.beige),

        ("ALIGN", (0,0), (-1,-1), "CENTER"),

        ("BOTTOMPADDING", (0,0), (-1,0), 8)

    ]))

    document.build([table])

    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="attendance_report.pdf",
        mimetype="application/pdf"
    )
# ==========================================================
# Attendance Statistics API
# ==========================================================
@attendance.route("/statistics")
def statistics():

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    cursor = mysql.connection.cursor()

    # Total Attendance
    cursor.execute("""
        SELECT COUNT(*)
        FROM attendance
    """)
    total_attendance = cursor.fetchone()[0]

    # Today's Attendance
    cursor.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE attendance_date = CURDATE()
    """)
    today_attendance = cursor.fetchone()[0]

    # Face Attendance
    cursor.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE attendance_method='FACE'
    """)
    face_attendance = cursor.fetchone()[0]

    # QR Attendance
    cursor.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE attendance_method='QR'
    """)
    qr_attendance = cursor.fetchone()[0]

    # Manual Attendance
    cursor.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE attendance_method='MANUAL'
    """)
    manual_attendance = cursor.fetchone()[0]

    cursor.close()

    return {
        "total": total_attendance,
        "today": today_attendance,
        "face": face_attendance,
        "qr": qr_attendance,
        "manual": manual_attendance
    }

# ==========================================================
# Monthly Attendance Summary
# ==========================================================
@attendance.route("/monthly-summary")
def monthly_summary():

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT

            MONTHNAME(attendance_date) AS month,

            COUNT(*) AS total

        FROM attendance

        GROUP BY
            YEAR(attendance_date),
            MONTH(attendance_date)

        ORDER BY
            YEAR(attendance_date),
            MONTH(attendance_date)
    """)

    monthly_data = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin/monthly_attendance.html",
        monthly_data=monthly_data
    )


# ==========================================================
# Department Wise Attendance
# ==========================================================
@attendance.route("/department-summary")
def department_summary():

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT

            students.department,

            COUNT(attendance.id)

        FROM attendance

        INNER JOIN students
            ON attendance.student_id = students.id

        GROUP BY students.department

        ORDER BY students.department
    """)

    department_data = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin/department_attendance.html",
        department_data=department_data
    )


# ==========================================================
# Student Attendance Percentage
# ==========================================================
@attendance.route("/student-percentage")
def student_percentage():

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT

            students.student_id,

            students.full_name,

            students.department,

            COUNT(attendance.id) AS total_attendance

        FROM students

        LEFT JOIN attendance
            ON students.id = attendance.student_id

        GROUP BY students.id

        ORDER BY total_attendance DESC
    """)

    student_data = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin/student_percentage.html",
        students=student_data
    )