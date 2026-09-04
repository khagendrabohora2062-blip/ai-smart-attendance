from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    flash,
    request,
    jsonify
)

from extensions import mysql

from utils.capture_faces import (
    capture_face_image
)

from utils.train_model import (
    train_faces
)


# ============================================================
# FACE BLUEPRINT
# ============================================================

face = Blueprint(
    "face",
    __name__,
    url_prefix="/face"
)


# ============================================================
# FACE DASHBOARD
# ============================================================

@face.route("/")
def dashboard():

    if "admin_id" not in session:

        return redirect(
            url_for("auth.login")
        )


    return render_template(
        "admin/face_dashboard.html"
    )


# ============================================================
# REGISTER FACE
# ============================================================

@face.route(
    "/register/<int:student_id>"
)
def register_face(student_id):

    if "admin_id" not in session:

        return redirect(
            url_for("auth.login")
        )


    return render_template(
        "admin/face_dashboard.html",
        student_id=student_id
    )


# ============================================================
# CAPTURE FACE IMAGE
# Browser Camera -> Flask -> Dataset
# ============================================================

@face.route(
    "/capture-image",
    methods=["POST"]
)
def capture_image():

    if "admin_id" not in session:

        return jsonify({
            "success": False,
            "message": "Unauthorized."
        }), 401


    try:

        # ====================================================
        # USER ENTERED STUDENT ID
        # ====================================================

        entered_student_id = request.form.get(
            "student_id"
        )


        if not entered_student_id:

            return jsonify({
                "success": False,
                "message":
                    "Student ID is required."
            }), 400


        entered_student_id = (
            str(entered_student_id)
            .strip()
        )


        # ====================================================
        # IMAGE NUMBER
        # ====================================================

        image_number = request.form.get(
            "image_number"
        )


        if not image_number:

            return jsonify({
                "success": False,
                "message":
                    "Image number is required."
            }), 400


        try:

            image_number = int(
                image_number
            )

        except ValueError:

            return jsonify({
                "success": False,
                "message":
                    "Invalid image number."
            }), 400


        # ====================================================
        # IMAGE
        # ====================================================

        image = request.files.get(
            "image"
        )


        if image is None:

            return jsonify({
                "success": False,
                "message":
                    "Face image is required."
            }), 400


        image_bytes = image.read()


        if not image_bytes:

            return jsonify({
                "success": False,
                "message":
                    "Empty image received."
            }), 400


        # ====================================================
        # FIND STUDENT
        #
        # IMPORTANT:
        #
        # User enters student_id
        #
        # Database:
        #
        # id = internal database ID
        # student_id = student's actual ID
        #
        # Dataset MUST use database id.
        # ====================================================

        cursor = mysql.connection.cursor()


        try:

            cursor.execute(
                """
                SELECT
                    id,
                    student_id,
                    full_name
                FROM students
                WHERE student_id=%s
                LIMIT 1
                """,
                (
                    entered_student_id,
                )
            )


            student = cursor.fetchone()


        finally:

            cursor.close()


        # ====================================================
        # STUDENT NOT FOUND
        # ====================================================

        if not student:

            return jsonify({
                "success": False,
                "message":
                    "Student ID not found in database."
            }), 404


        # ====================================================
        # DATABASE ID
        # ====================================================

        student_db_id = int(
            student[0]
        )

        student_code = str(
            student[1]
        )

        student_name = student[2]


        # ====================================================
        # CAPTURE USING DATABASE ID
        #
        # Example:
        #
        # students:
        #
        # id = 7
        # student_id = 24001
        #
        # dataset:
        #
        # dataset/7/
        #
        # NOT:
        #
        # dataset/24001/
        # ====================================================

        result = capture_face_image(
            student_id=student_db_id,
            image_bytes=image_bytes,
            image_number=image_number
        )


        # ====================================================
        # ADD STUDENT INFO TO RESPONSE
        # ====================================================

        result["student_db_id"] = (
            student_db_id
        )

        result["student_id"] = (
            student_code
        )

        result["student_name"] = (
            student_name
        )


        return jsonify(
            result
        )


    except Exception as e:

        print(
            "FACE CAPTURE ERROR:",
            str(e)
        )


        return jsonify({
            "success": False,
            "message":
                f"Face capture error: {str(e)}"
        }), 500


# ============================================================
# TRAIN MODEL
# ============================================================

@face.route(
    "/train"
)
def train_model():

    if "admin_id" not in session:

        return redirect(
            url_for("auth.login")
        )


    try:

        result = train_faces()


        if result:

            flash(
                "Face Model Trained Successfully.",
                "success"
            )

        else:

            flash(
                "Face Model Training Failed. "
                "Check dataset and console.",
                "danger"
            )


    except Exception as e:

        print(
            "FACE TRAINING ERROR:",
            str(e)
        )


        flash(
            f"Training Error: {e}",
            "danger"
        )


    return redirect(
        url_for(
            "face.dashboard"
        )
    )


# ============================================================
# START FACE ATTENDANCE
# ============================================================

@face.route(
    "/attendance"
)
def start_face_attendance():

    if "admin_id" not in session:

        return redirect(
            url_for("auth.login")
        )


    flash(
        "Please open an attendance session "
        "from the Teacher Panel first.",
        "warning"
    )


    return redirect(
        url_for(
            "face.dashboard"
        )
    )