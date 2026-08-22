from flask import (
    Blueprint,
    request,
    redirect,
    flash,
    url_for,
    session
)

from extensions import mysql


# =====================================================
# FEEDBACK BLUEPRINT
# =====================================================

feedback = Blueprint(
    "feedback",
    __name__,
    url_prefix="/feedback"
)


# =====================================================
# SUBMIT FEEDBACK
# =====================================================

@feedback.route("/", methods=["POST"])
def submit_feedback():

    # -------------------------------------------------
    # GET FORM DATA
    # -------------------------------------------------

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


    # -------------------------------------------------
    # VALIDATION
    # -------------------------------------------------

    if not name:

        flash(
            "Please enter your name.",
            "danger"
        )

        return redirect(
            url_for("home.index")
        )


    if not rating:

        flash(
            "Please select a rating.",
            "danger"
        )

        return redirect(
            url_for("home.index")
        )


    if not message:

        flash(
            "Please write your feedback.",
            "danger"
        )

        return redirect(
            url_for("home.index")
        )


    # -------------------------------------------------
    # VALIDATE RATING
    # -------------------------------------------------

    try:

        rating_value = int(rating)

    except (ValueError, TypeError):

        flash(
            "Invalid rating.",
            "danger"
        )

        return redirect(
            url_for("home.index")
        )


    if rating_value < 1 or rating_value > 5:

        flash(
            "Rating must be between 1 and 5.",
            "danger"
        )

        return redirect(
            url_for("home.index")
        )


    # -------------------------------------------------
    # INSERT FEEDBACK
    # -------------------------------------------------

    cursor = mysql.connection.cursor()

    try:

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
            rating_value,
            message
        ))


        mysql.connection.commit()


        flash(
            "Thank you for your valuable feedback!",
            "success"
        )


    except Exception as e:

        mysql.connection.rollback()

        print(
            "Feedback Error:",
            e
        )

        flash(
            "Unable to submit feedback. Please try again.",
            "danger"
        )


    finally:

        cursor.close()


    # -------------------------------------------------
    # RETURN TO LANDING PAGE
    # -------------------------------------------------

    return redirect(
        url_for("home.index")
    )


# =====================================================
# DELETE FEEDBACK
# ADMIN ONLY
# =====================================================

@feedback.route(
    "/delete/<int:id>",
    methods=["GET", "POST"]
)
def delete_feedback(id):

    # -------------------------------------------------
    # CHECK ADMIN LOGIN
    # -------------------------------------------------

    if "admin_id" not in session:

        flash(
            "Please login as administrator.",
            "danger"
        )

        return redirect(
            url_for("auth.login")
        )


    # -------------------------------------------------
    # DELETE FEEDBACK
    # -------------------------------------------------

    cursor = mysql.connection.cursor()

    try:

        cursor.execute("""
            DELETE FROM feedback
            WHERE id = %s
        """, (
            id,
        ))


        mysql.connection.commit()


        flash(
            "Feedback deleted successfully!",
            "success"
        )


    except Exception as e:

        mysql.connection.rollback()

        print(
            "Delete Feedback Error:",
            e
        )

        flash(
            "Unable to delete feedback.",
            "danger"
        )


    finally:

        cursor.close()


    # -------------------------------------------------
    # RETURN TO ADMIN FEEDBACK PAGE
    # -------------------------------------------------

    return redirect(
        url_for("admin.feedbacks")
    )