from flask import Flask
import os

from config import Config
from extensions import mysql


# =========================================================
# CREATE APPLICATION
# =========================================================

def create_app():

    app = Flask(__name__)

    # =====================================================
    # CONFIGURATION
    # =====================================================

    app.config.from_object(Config)

    # =====================================================
    # MYSQL
    # =====================================================

    mysql.init_app(app)

    # =====================================================
    # UPLOAD FOLDERS
    # =====================================================

    upload_folder = os.path.join(
        app.root_path,
        "static",
        "uploads"
    )

    assignment_folder = os.path.join(
        upload_folder,
        "assignments"
    )

    submission_folder = os.path.join(
        upload_folder,
        "assignment_submissions"
    )

    student_folder = os.path.join(
        upload_folder,
        "students"
    )

    # Create folders automatically
    os.makedirs(upload_folder, exist_ok=True)
    os.makedirs(assignment_folder, exist_ok=True)
    os.makedirs(submission_folder, exist_ok=True)
    os.makedirs(student_folder, exist_ok=True)

    app.config["UPLOAD_FOLDER"] = upload_folder
    app.config["ASSIGNMENT_UPLOAD_FOLDER"] = assignment_folder
    app.config["SUBMISSION_UPLOAD_FOLDER"] = submission_folder
    app.config["STUDENT_UPLOAD_FOLDER"] = student_folder

    # =====================================================
    # IMPORT BLUEPRINTS
    # =====================================================

    # -----------------------------------------------------
    # Authentication
    # -----------------------------------------------------

    from routes.auth import auth
    from routes.student_auth import student_auth
    from routes.teacher_auth import teacher_auth

    # -----------------------------------------------------
    # Home
    # -----------------------------------------------------

    from routes.home import home

    # -----------------------------------------------------
    # Admin
    # -----------------------------------------------------

    from routes.admin import admin
    from routes.admin_syllabus import admin_syllabus
    from routes.admin_face import admin_face
    from routes.admin_notice import admin_notice
    from routes.admin_marksheet import admin_marksheet

    # -----------------------------------------------------
    # Student
    # -----------------------------------------------------

    from routes.student import students
    from routes.student_assignment import student_assignment
    from routes.student_routine import student_routine
    from routes.student_notice import student_notice
    from routes.student_result import student_result
    from routes.student_syllabus import student_syllabus

    # -----------------------------------------------------
    # Teacher
    # -----------------------------------------------------

    from routes.teacher import teachers
    from routes.teacher_assignment import teacher_assignment
    from routes.teacher_routine import teacher_routine

    # -----------------------------------------------------
    # Subjects
    # -----------------------------------------------------

    from routes.subject import subjects

    # -----------------------------------------------------
    # Routine
    # -----------------------------------------------------

    from routes.routine import routine

    # -----------------------------------------------------
    # Attendance
    # -----------------------------------------------------

    from routes.attendance import attendance
    from routes.attendance_session import attendance_session
    from routes.teacher_attendance import teacher_attendance

    # -----------------------------------------------------
    # Face Recognition
    # -----------------------------------------------------

    from routes.face import face
    from routes.teacher_face import teacher_face
    from routes.admin_face import admin_face

    # -----------------------------------------------------
    # QR Attendance
    # -----------------------------------------------------

    from routes.qr import qr
    from routes.teacher_qr import teacher_qr

    # -----------------------------------------------------
    # Feedback
    # -----------------------------------------------------

    from routes.feedback import feedback

    from routes.teacher_syllabus import teacher_syllabus
    from routes.teacher_notice import teacher_notice

    # =====================================================
    # REGISTER BLUEPRINTS
    # =====================================================

    # -----------------------------------------------------
    # HOME
    # -----------------------------------------------------

    app.register_blueprint(home)

    # -----------------------------------------------------
    # AUTHENTICATION
    # -----------------------------------------------------

    app.register_blueprint(auth)
    app.register_blueprint(student_auth)
    app.register_blueprint(teacher_auth)

    # -----------------------------------------------------
    # ADMIN
    # -----------------------------------------------------

    app.register_blueprint(admin)
    app.register_blueprint(admin_face)
    app.register_blueprint(admin_syllabus)
    app.register_blueprint(admin_notice)
    app.register_blueprint(admin_marksheet)

    # -----------------------------------------------------
    # STUDENT
    # -----------------------------------------------------

    app.register_blueprint(students)
    app.register_blueprint(student_assignment)
    app.register_blueprint(student_routine)
    app.register_blueprint(student_notice)
    app.register_blueprint(student_result)
    app.register_blueprint(student_syllabus)

    # -----------------------------------------------------
    # TEACHER
    # -----------------------------------------------------

    app.register_blueprint(teachers)
    app.register_blueprint(teacher_assignment)
    app.register_blueprint(teacher_routine)

    # -----------------------------------------------------
    # SUBJECTS
    # -----------------------------------------------------

    app.register_blueprint(subjects)

    # -----------------------------------------------------
    # ROUTINE
    # -----------------------------------------------------

    app.register_blueprint(routine)

    # -----------------------------------------------------
    # ATTENDANCE
    # -----------------------------------------------------

    app.register_blueprint(attendance)
    app.register_blueprint(attendance_session)
    app.register_blueprint(teacher_attendance)

    # -----------------------------------------------------
    # FACE RECOGNITION
    # -----------------------------------------------------

    app.register_blueprint(face)
    app.register_blueprint(teacher_face)

    # -----------------------------------------------------
    # QR ATTENDANCE
    # -----------------------------------------------------

    app.register_blueprint(qr)
    app.register_blueprint(teacher_qr)

    # -----------------------------------------------------
    # FEEDBACK
    # -----------------------------------------------------

    app.register_blueprint(feedback)


    app.register_blueprint(teacher_syllabus)
    app.register_blueprint(teacher_notice)

    # =====================================================
    # RETURN APPLICATION
    # =====================================================

    return app


# =========================================================
# CREATE APPLICATION
# =========================================================

app = create_app()


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=True
    )