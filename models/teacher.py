from config import db


class Teacher(db.Model):

    __tablename__ = "teachers"


    id = db.Column(
        db.Integer,
        primary_key=True
    )


    teacher_id = db.Column(
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
        unique=True,
        nullable=False
    )


    phone = db.Column(
        db.String(20)
    )


    department = db.Column(
        db.String(100)
    )


    password = db.Column(
        db.String(255),
        nullable=False
    )


    created_at = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp()
    )


    def __repr__(self):
        return f"<Teacher {self.full_name}>"