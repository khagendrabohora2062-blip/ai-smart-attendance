
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


    # =================================================
    # DATABASE INSERT
    # =================================================

    cursor = mysql.connection.cursor()

    try:

        # -------------------------------------------------
        # GENERATE NEXT ID
        # -------------------------------------------------
        #
        # feedback.id is NOT AUTO_INCREMENT.
        # Therefore we generate the ID ourselves.
        #
        # FOR UPDATE locks the selected MAX(id) result
        # during this transaction and reduces the chance
        # of duplicate IDs from simultaneous requests.
        # -------------------------------------------------

        cursor.execute("""
            SELECT COALESCE(MAX(id), 0) + 1
            FROM feedback
            FOR UPDATE
        """)

        result = cursor.fetchone()

        if not result or result[0] is None:

            next_id = 1

        else:

            next_id = int(result[0])


        # -------------------------------------------------
        # INSERT FEEDBACK
        # -------------------------------------------------

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
            email if email else None,
            rating_value,
            message
        ))


        # -------------------------------------------------
        # COMMIT
        # -------------------------------------------------

        mysql.connection.commit()


        flash(
            "Thank you for your valuable feedback!",
            "success"
        )


    except Exception as e:

        # -------------------------------------------------
        # ROLLBACK
        # -------------------------------------------------

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


    # -------------------------------------------------
    # RETURN TO HOME PAGE
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
    # DATABASE
    # -------------------------------------------------

    cursor = mysql.connection.cursor()

    try:

        # -------------------------------------------------
        # DELETE FEEDBACK
        # -------------------------------------------------

        cursor.execute("""
            DELETE FROM feedback
            WHERE id = %s
        """, (
            id,
        ))


        # -------------------------------------------------
        # COMMIT
        # -------------------------------------------------

        mysql.connection.commit()


        # -------------------------------------------------
        # CHECK DELETE RESULT
        # -------------------------------------------------

        if cursor.rowcount > 0:

            flash(
                "Feedback deleted successfully!",
                "success"
            )

        else:

            flash(
                "Feedback record was not found.",
                "warning"
            )


    except Exception as e:

        mysql.connection.rollback()

        print(
            "DELETE FEEDBACK ERROR:",
            repr(e)
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

