from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from extensions import mysql


home = Blueprint(
    "home",
    __name__
)


# =====================================================
# HOME PAGE
# =====================================================

@home.route("/")
def index():

    cursor = mysql.connection.cursor()

    # =================================================
    # TOTAL STUDENTS
    # =================================================

    cursor.execute("""
        SELECT COUNT(*)
        FROM students
    """)

    total_students = cursor.fetchone()[0]


    # =================================================
    # TOTAL TEACHERS
    # =================================================

    cursor.execute("""
        SELECT COUNT(*)
        FROM teachers
    """)

    total_teachers = cursor.fetchone()[0]


    # =================================================
    # TOTAL SUBJECTS
    # =================================================

    cursor.execute("""
        SELECT COUNT(*)
        FROM subjects
    """)

    total_subjects = cursor.fetchone()[0]


    # =================================================
    # TODAY'S ATTENDANCE
    # =================================================

    cursor.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE attendance_date = CURDATE()
    """)

    today_attendance = cursor.fetchone()[0]


    # =================================================
    # REAL USER FEEDBACK / TESTIMONIALS
    # =================================================

    cursor.execute("""
        SELECT
            name,
            rating,
            message,
            created_at
        FROM feedback
        ORDER BY id DESC
        LIMIT 6
    """)

    feedbacks = cursor.fetchall()


    cursor.close()


    # =================================================
    # SEND DATA TO LANDING PAGE
    # =================================================

    return render_template(
        "landing/index.html",

        total_students=total_students,

        total_teachers=total_teachers,

        total_subjects=total_subjects,

        today_attendance=today_attendance,

        feedbacks=feedbacks
    )


# =====================================================
# ABOUT PAGE
# =====================================================

@home.route("/about")
def about():

    return render_template(
        "landing/about.html"
    )


# =====================================================
# CONTACT PAGE
# =====================================================

@home.route(
    "/contact",
    methods=["GET", "POST"]
)
def contact():

    if request.method == "POST":

        name = request.form.get("name", "").strip()

        email = request.form.get("email", "").strip()

        subject = request.form.get("subject", "").strip()

        message = request.form.get("message", "").strip()


        # ---------------------------------------------
        # BASIC VALIDATION
        # ---------------------------------------------

        if not name or not email or not subject or not message:

            flash(
                "Please fill in all required fields.",
                "danger"
            )

            return redirect(
                url_for("home.contact")
            )


        cursor = mysql.connection.cursor()


        cursor.execute("""
            INSERT INTO contact_messages
            (
                name,
                email,
                subject,
                message
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s
            )
        """, (
            name,
            email,
            subject,
            message
        ))


        mysql.connection.commit()

        cursor.close()


        flash(
            "Your message has been sent successfully.",
            "success"
        )


        return redirect(
            url_for("home.contact")
        )


    return render_template(
        "landing/contact.html"
    )


# =====================================================
# FEEDBACK PAGE
# =====================================================

@home.route(
    "/feedback",
    methods=["GET", "POST"]
)
def feedback():

    if request.method == "POST":

        name = request.form.get("name", "").strip()

        email = request.form.get("email", "").strip()

        rating = request.form.get("rating")

        message = request.form.get("message", "").strip()


        # ---------------------------------------------
        # VALIDATION
        # ---------------------------------------------

        if not name or not rating or not message:

            flash(
                "Please fill in all required feedback fields.",
                "danger"
            )

            return redirect(
                url_for("home.feedback")
            )


        cursor = mysql.connection.cursor()


        cursor.execute("""
            INSERT INTO feedback
            (
                name,
                email,
                rating,
                message
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s
            )
        """, (
            name,
            email,
            rating,
            message
        ))


        mysql.connection.commit()

        cursor.close()


        flash(
            "Thank you for your feedback!",
            "success"
        )


        return redirect(
            url_for("home.feedback")
        )


    # =================================================
    # GET LATEST FEEDBACK
    # =================================================

    cursor = mysql.connection.cursor()


    cursor.execute("""
        SELECT
            name,
            rating,
            message,
            created_at
        FROM feedback
        ORDER BY id DESC
        LIMIT 10
    """)


    feedbacks = cursor.fetchall()


    cursor.close()


    return render_template(
        "landing/feedback.html",
        feedbacks=feedbacks
    )