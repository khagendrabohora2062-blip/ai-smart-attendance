from config import db


class Attendance(db.Model):

    __tablename__ = "attendance"


    id = db.Column(
        db.Integer,
        primary_key=True
    )


    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id"),
        nullable=False
    )


    subject_id = db.Column(
        db.Integer,
        db.ForeignKey("subjects.id")
    )


    date = db.Column(
        db.Date,
        nullable=False
    )


    status = db.Column(
        db.String(20),
        default="Present"
    )


    method = db.Column(
        db.String(20)
    )


    created_at = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp()
    )


    def __repr__(self):
        return f"<Attendance {self.student_id}>"