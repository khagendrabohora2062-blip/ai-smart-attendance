CREATE TABLE IF NOT EXISTS assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,

    teacher_id INT NOT NULL,
    subject_id INT NOT NULL,

    title VARCHAR(255) NOT NULL,
    description TEXT,

    attachment VARCHAR(255) DEFAULT NULL,

    due_date DATE NOT NULL,
    due_time TIME NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_assignment_teacher
        FOREIGN KEY (teacher_id)
        REFERENCES teachers(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_assignment_subject
        FOREIGN KEY (subject_id)
        REFERENCES subjects(id)
        ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS assignment_submissions (
    id INT AUTO_INCREMENT PRIMARY KEY,

    assignment_id INT NOT NULL,
    student_id INT NOT NULL,

    answer TEXT,

    attachment VARCHAR(255) DEFAULT NULL,

    submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    marks DECIMAL(5,2) DEFAULT NULL,

    feedback TEXT,

    status ENUM(
        'Submitted',
        'Graded',
        'Returned'
    ) DEFAULT 'Submitted',

    UNIQUE KEY unique_assignment_student
        (assignment_id, student_id),

    CONSTRAINT fk_submission_assignment
        FOREIGN KEY (assignment_id)
        REFERENCES assignments(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_submission_student
        FOREIGN KEY (student_id)
        REFERENCES students(id)
        ON DELETE CASCADE
);