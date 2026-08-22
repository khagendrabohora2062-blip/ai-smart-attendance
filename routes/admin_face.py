from flask import Blueprint, render_template

admin_face = Blueprint(
    "admin_face",
    __name__,
    url_prefix="/admin/face"
)


@admin_face.route("/")
def index():
    return render_template("admin/face_register.html")