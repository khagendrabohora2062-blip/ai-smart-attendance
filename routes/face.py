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

from utils.capture_faces import capture_face_image
from utils.recognize_face import recognize_face
from utils.train_model import train_faces


face = Blueprint(
    "face",
    __name__,
    url_prefix="/face"
)


# ============================================================
# FACE RECOGNITION DASHBOARD
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
# REGISTER FACE PAGE
# ============================================================

@face.route("/register/<int:student_id>")
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

        # ----------------------------------------------------
        # Student ID
        # ----------------------------------------------------

        student_id = request.form.get(
            "student_id"
        )

        if not student_id:

            return jsonify({
                "success": False,
                "message": "Student ID is required."
            }), 400


        # ----------------------------------------------------
        # Image Number
        # ----------------------------------------------------

        image_number = request.form.get(
            "image_number"
        )

        if not image_number:

            return jsonify({
                "success": False,
                "message": "Image number is required."
            }), 400


        # ----------------------------------------------------
        # Uploaded Image
        # ----------------------------------------------------

        image = request.files.get(
            "image"
        )

        if image is None:

            return jsonify({
                "success": False,
                "message": "Face image is required."
            }), 400


        # ----------------------------------------------------
        # Read Image
        # ----------------------------------------------------

        image_bytes = image.read()

        if not image_bytes:

            return jsonify({
                "success": False,
                "message": "Empty image received."
            }), 400


        # ----------------------------------------------------
        # Process Face
        # ----------------------------------------------------

        result = capture_face_image(
            student_id=student_id,
            image_bytes=image_bytes,
            image_number=int(image_number)
        )


        # ----------------------------------------------------
        # Return Result
        # ----------------------------------------------------

        return jsonify(result)


    except ValueError:

        return jsonify({
            "success": False,
            "message": "Invalid image number."
        }), 400


    except Exception as e:

        print(
            "FACE CAPTURE ERROR:",
            str(e)
        )

        return jsonify({
            "success": False,
            "message": f"Face capture error: {str(e)}"
        }), 500


# ============================================================
# TRAIN FACE MODEL
# ============================================================

@face.route("/train")
def train_model():

    if "admin_id" not in session:
        return redirect(
            url_for("auth.login")
        )

    try:

        train_faces()

        flash(
            "Face Model Trained Successfully.",
            "success"
        )

    except Exception as e:

        print(
            "FACE TRAINING ERROR:",
            str(e)
        )

        flash(
            f"Training Error : {e}",
            "danger"
        )

    return redirect(
        url_for("face.dashboard")
    )


# ============================================================
# START FACE ATTENDANCE
# ============================================================

@face.route("/attendance")
def start_face_attendance():

    if "admin_id" not in session:
        return redirect(
            url_for("auth.login")
        )

    flash(
        "Please open an attendance session from the Teacher Panel first.",
        "warning"
    )

    return redirect(
        url_for("face.dashboard")
    )