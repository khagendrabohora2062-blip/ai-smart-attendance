from config import db


class Student(db.Model):

    __tablename__ = "students"


    id = db.Column(
        db.Integer,
        primary_key=True
    )


    student_id = db.Column(
        db.String(20),
        unique=True,
        nullable=False
    )


    full_name = db.Column(
        db.String(100),
        nullable=False
    )


    email = db.Column(
        db.String(100),
        unique=True
    )


    phone = db.Column(
        db.String(20)
    )


    department = db.Column(
        db.String(100)
    )


    face_encoding = db.Column(
        db.Text
    )


    created_at = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp()
    )


    def __repr__(self):
        return f"<Student {self.full_name}>"