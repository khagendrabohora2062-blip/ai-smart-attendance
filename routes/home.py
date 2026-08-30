
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from extensions import mysql


# =====================================================
# HOME BLUEPRINT
# =====================================================

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

    try:

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
        # LATEST FEEDBACK
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


    except Exception as e:

        print(
            "HOME PAGE ERROR:",
            repr(e)
        )

        flash(
            "Unable to load home page.",
            "danger"
        )

        return render_template(
            "landing/index.html",
            total_students=0,
            total_teachers=0,
            total_subjects=0,
            today_attendance=0,
            feedbacks=[]
        )


    finally:

        cursor.close()


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

    # =================================================
    # SHOW CONTACT PAGE
    # =================================================

    if request.method == "GET":

        return render_template(
            "landing/contact.html"
        )


    # =================================================
    # GET FORM DATA
    # =================================================

    name = request.form.get(
        "name",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip()

    subject = request.form.get(
        "subject",
        ""
    ).strip()

    message = request.form.get(
        "message",
        ""
    ).strip()


    # =================================================
    # VALIDATION
    # =================================================

    if not name:

        flash(
            "Please enter your name.",
            "danger"
        )

        return redirect(
            url_for("home.contact")
        )


    if not email:

        flash(
            "Please enter your email address.",
            "danger"
        )

        return redirect(
            url_for("home.contact")
        )


    if not subject:

        flash(
            "Please enter a subject.",
            "danger"
        )

        return redirect(
            url_for("home.contact")
        )


    if not message:

        flash(
            "Please enter your message.",
            "danger"
        )

        return redirect(
            url_for("home.contact")
        )


    # =================================================
    # DATABASE INSERT
    # =================================================

    cursor = mysql.connection.cursor()

    try:

        # =================================================
        # MANUALLY GENERATE NEXT ID
        # =================================================

        cursor.execute("""
            SELECT COALESCE(MAX(id), 0) + 1
            FROM contact_messages
        """)

        next_id = cursor.fetchone()[0]


        # =================================================
        # INSERT CONTACT MESSAGE
        # =================================================

        cursor.execute("""
            INSERT INTO contact_messages
            (
                id,
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
                %s,
                %s
            )
        """, (
            next_id,
            name,
            email,
            subject,
            message
        ))


        # =================================================
        # COMMIT
        # =================================================

        mysql.connection.commit()


        flash(
            "Your message has been sent successfully.",
            "success"
        )


    except Exception as e:

        mysql.connection.rollback()

        print(
            "CONTACT MESSAGE ERROR:",
            repr(e)
        )

        flash(
            "Unable to send your message. Please try again.",
            "danger"
        )


    finally:

        cursor.close()


    # =================================================
    # RETURN TO CONTACT PAGE
    # =================================================

    return redirect(
        url_for("home.contact")
    )


# =====================================================
# FEEDBACK PAGE
# =====================================================

@home.route(
    "/feedback",
    methods=["GET", "POST"]
)
def feedback_page():

    # =================================================
    # GET REQUEST
    # =================================================

    if request.method == "GET":

        cursor = mysql.connection.cursor()

        try:

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


        except Exception as e:

            print(
                "FEEDBACK LOAD ERROR:",
                repr(e)
            )

            feedbacks = []


        finally:

            cursor.close()


        return render_template(
            "landing/feedback.html",
            feedbacks=feedbacks
        )


    # =================================================
    # GET FEEDBACK FORM DATA
    # =================================================

    name = request.form.get(
        "name",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip()

    rating = request.form.get(
        "rating",
        ""
    ).strip()

    message = request.form.get(
        "message",
        ""
    ).strip()


    # =================================================
    # VALIDATION
    # =================================================

    if not name:

        flash(
            "Please enter your name.",
            "danger"
        )

        return redirect(
            url_for("home.feedback_page")
        )


    if not rating:

        flash(
            "Please select a rating.",
            "danger"
        )

        return redirect(
            url_for("home.feedback_page")
        )


    if not message:

        flash(
            "Please write your feedback.",
            "danger"
        )

        return redirect(
            url_for("home.feedback_page")
        )


    # =================================================
    # VALIDATE RATING
    # =================================================

    try:

        rating_value = int(rating)

    except (ValueError, TypeError):

        flash(
            "Invalid rating.",
            "danger"
        )

        return redirect(
            url_for("home.feedback_page")
        )


    if rating_value < 1 or rating_value > 5:

        flash(
            "Rating must be between 1 and 5.",
            "danger"
        )

        return redirect(
            url_for("home.feedback_page")
        )


    # =================================================
    # INSERT FEEDBACK
    # =================================================

    cursor = mysql.connection.cursor()

    try:

        # =================================================
        # MANUALLY GENERATE NEXT ID
        # =================================================

        cursor.execute("""
            SELECT COALESCE(MAX(id), 0) + 1
            FROM feedback
        """)

        next_feedback_id = cursor.fetchone()[0]


        # =================================================
        # INSERT
        # =================================================

        cursor.execute("""
            INSERT INTO feedback
            (
                id,
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
                %s,
                %s
            )
        """, (
            next_feedback_id,
            name,
            email,
            rating_value,
            message
        ))


        # =================================================
        # COMMIT
        # =================================================

        mysql.connection.commit()


        flash(
            "Thank you for your valuable feedback!",
            "success"
        )


    except Exception as e:

        mysql.connection.rollback()

        print(
            "FEEDBACK INSERT ERROR:",
            repr(e)
        )

        flash(
            "Unable to submit feedback. Please try again.",
            "danger"
        )


    finally:

        cursor.close()


    # =================================================
    # RETURN TO FEEDBACK PAGE
    # =================================================

    return redirect(
        url_for("home.feedback_page")
    )
