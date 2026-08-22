from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    flash
)

from utils.capture_faces import capture_faces
from utils.recognize_face import recognize_face
from utils.train_model import train_faces


face = Blueprint(
    "face",
    __name__,
    url_prefix="/face"
)


# =====================================================
# Face Recognition Dashboard
# =====================================================
@face.route("/")
def dashboard():

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    return render_template(
        "admin/face_dashboard.html"
    )


# =====================================================
# Register Face
# =====================================================
@face.route("/register/<int:student_id>")
def register_face(student_id):

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    try:

        flash(
            "Camera is opening...",
            "info"
        )

        count = capture_faces(
            str(student_id),
            total_images=50
        )

        if count >= 50:

            flash(
                "Training Face Model...",
                "info"
            )

            train_faces()

            flash(
                "Face Registered Successfully.",
                "success"
            )

        else:

            flash(
                f"Only {count} images captured.",
                "warning"
            )

    except Exception as e:

        flash(
            f"Face Error : {e}",
            "danger"
        )

    return redirect(
        url_for("students.index")
    )


# =====================================================
# Train Model
# =====================================================
@face.route("/train")
def train_model():

    if "admin_id" not in session:
        return redirect(url_for("auth.login"))

    try:

        train_faces()

        flash(
            "Face Model Trained Successfully.",
            "success"
        )

    except Exception as e:

        flash(
            f"Training Error : {e}",
            "danger"
        )

    return redirect(
        url_for("face.dashboard")
    )
# =====================================================
# Start Face Attendance
# =====================================================
@face.route("/attendance")
def start_face_attendance():

    flash(
        "Please open an attendance session from the Teacher Panel first.",
        "warning"
    )

    return redirect(url_for("face.dashboard"))