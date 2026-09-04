from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app
)

from extensions import mysql


home = Blueprint(
    "home",
    __name__
)


# =========================================================
# PRIVATE HELPERS
# =========================================================

def _home_stats(cursor):
    """
    Load public landing-page statistics.
    """

    cursor.execute("""
        SELECT COUNT(*)
        FROM students
    """)

    total_students = int(
        cursor.fetchone()[0] or 0
    )


    cursor.execute("""
        SELECT COUNT(*)
        FROM teachers
    """)

    total_teachers = int(
        cursor.fetchone()[0] or 0
    )


    cursor.execute("""
        SELECT COUNT(*)
        FROM subjects
    """)

    total_subjects = int(
        cursor.fetchone()[0] or 0
    )


    cursor.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE attendance_date = CURDATE()
    """)

    today_attendance = int(
        cursor.fetchone()[0] or 0
    )


    return (
        total_students,
        total_teachers,
        total_subjects,
        today_attendance
    )


def _latest_feedback(cursor, limit=6):
    """
    Return recent feedback in a clean
    template-friendly structure.
    """

    cursor.execute("""
        SELECT
            name,
            rating,
            message,
            created_at
        FROM feedback
        ORDER BY id DESC
        LIMIT %s
    """, (
        limit,
    ))

    rows = cursor.fetchall() or []

    feedbacks = []

    for row in rows:

        created_at = row[3]

        if hasattr(
            created_at,
            "strftime"
        ):
            created_at = created_at.strftime(
                "%d %b %Y"
            )

        elif created_at:
            created_at = str(
                created_at
            )

        feedbacks.append({
            "name": row[0],
            "rating": int(
                row[1] or 0
            ),
            "message": row[2] or "",
            "created_at": (
                created_at or ""
            )
        })

    return feedbacks


# =========================================================
# HOME PAGE
# =========================================================

@home.route("/")
def index():

    cursor = mysql.connection.cursor()

    try:

        (
            total_students,
            total_teachers,
            total_subjects,
            today_attendance
        ) = _home_stats(
            cursor
        )

        feedbacks = _latest_feedback(
            cursor,
            limit=6
        )

        return render_template(
            "landing/index.html",
            total_students=total_students,
            total_teachers=total_teachers,
            total_subjects=total_subjects,
            today_attendance=today_attendance,
            feedbacks=feedbacks
        )

    except Exception:

        current_app.logger.exception(
            "HOME PAGE ERROR"
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


# =========================================================
# ABOUT
# =========================================================

@home.route("/about")
def about():

    return render_template(
        "landing/about.html"
    )


# =========================================================
# CONTACT
# =========================================================

@home.route(
    "/contact",
    methods=[
        "GET",
        "POST"
    ]
)
def contact():

    if request.method == "GET":

        return render_template(
            "landing/contact.html"
        )


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


    # -----------------------------------------------------
    # Validation
    # -----------------------------------------------------

    if not name:

        flash(
            "Please enter your name.",
            "danger"
        )

        return redirect(
            url_for(
                "home.contact"
            )
        )


    if not email:

        flash(
            "Please enter your email address.",
            "danger"
        )

        return redirect(
            url_for(
                "home.contact"
            )
        )


    if (
        "@" not in email
        or "." not in email.rsplit(
            "@",
            1
        )[-1]
    ):

        flash(
            "Please enter a valid email address.",
            "danger"
        )

        return redirect(
            url_for(
                "home.contact"
            )
        )


    if not subject:

        flash(
            "Please enter a subject.",
            "danger"
        )

        return redirect(
            url_for(
                "home.contact"
            )
        )


    if not message:

        flash(
            "Please enter your message.",
            "danger"
        )

        return redirect(
            url_for(
                "home.contact"
            )
        )


    # -----------------------------------------------------
    # Database
    # -----------------------------------------------------

    cursor = mysql.connection.cursor()

    try:

        cursor.execute("""
            SELECT
                COALESCE(MAX(id), 0) + 1
            FROM contact_messages
            FOR UPDATE
        """)

        next_id = int(
            cursor.fetchone()[0] or 1
        )


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


        mysql.connection.commit()


        flash(
            "Your message has been sent successfully.",
            "success"
        )


    except Exception:

        mysql.connection.rollback()

        current_app.logger.exception(
            "CONTACT MESSAGE ERROR"
        )

        flash(
            "Unable to send your message. Please try again.",
            "danger"
        )


    finally:

        cursor.close()


    return redirect(
        url_for(
            "home.contact"
        )
    )


# =========================================================
# FEEDBACK PAGE
# =========================================================

@home.route(
    "/feedback",
    methods=[
        "GET",
        "POST"
    ]
)
def feedback_page():

    # -----------------------------------------------------
    # Legacy direct POST support
    # -----------------------------------------------------

    if request.method == "POST":

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


        if not name:

            flash(
                "Please enter your name.",
                "danger"
            )

            return redirect(
                url_for(
                    "home.feedback_page"
                )
            )


        if not rating:

            flash(
                "Please select a rating.",
                "danger"
            )

            return redirect(
                url_for(
                    "home.feedback_page"
                )
            )


        if not message:

            flash(
                "Please write your feedback.",
                "danger"
            )

            return redirect(
                url_for(
                    "home.feedback_page"
                )
            )


        try:

            rating_value = int(
                rating
            )

        except (
            ValueError,
            TypeError
        ):

            flash(
                "Invalid rating.",
                "danger"
            )

            return redirect(
                url_for(
                    "home.feedback_page"
                )
            )


        if (
            rating_value < 1
            or rating_value > 5
        ):

            flash(
                "Rating must be between 1 and 5.",
                "danger"
            )

            return redirect(
                url_for(
                    "home.feedback_page"
                )
            )


        cursor = mysql.connection.cursor()

        try:

            cursor.execute("""
                SELECT
                    COALESCE(MAX(id), 0) + 1
                FROM feedback
                FOR UPDATE
            """)

            next_id = int(
                cursor.fetchone()[0] or 1
            )


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
                next_id,
                name,
                email or None,
                rating_value,
                message
            ))


            mysql.connection.commit()


            flash(
                "Thank you for your valuable feedback!",
                "success"
            )


        except Exception:

            mysql.connection.rollback()

            current_app.logger.exception(
                "FEEDBACK INSERT ERROR"
            )

            flash(
                "Unable to submit feedback. Please try again.",
                "danger"
            )


        finally:

            cursor.close()


        return redirect(
            url_for(
                "home.feedback_page"
            )
        )


    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    cursor = mysql.connection.cursor()

    try:

        feedbacks = _latest_feedback(
            cursor,
            limit=10
        )

    except Exception:

        current_app.logger.exception(
            "FEEDBACK LOAD ERROR"
        )

        feedbacks = []

    finally:

        cursor.close()


    return render_template(
        "landing/feedback.html",
        feedbacks=feedbacks
    )