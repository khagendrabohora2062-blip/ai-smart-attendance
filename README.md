# AI Smart Attendance System

An AI-based Smart Attendance System designed to simplify and automate student attendance management using Face Recognition and QR Code scanning.

The system provides separate functionality for administrators, teachers, and students, with session-based attendance management and attendance reporting.

---

## 📌 Project Overview

The AI Smart Attendance System is developed to reduce manual attendance work and improve the accuracy and efficiency of attendance management.

Teachers can create attendance sessions for their assigned subjects. During an active session, student attendance can be recorded using:

- Face Recognition
- QR Code
- Manual attendance

When an attendance session is closed, students who were not marked Present are automatically marked as Absent.

The system also provides attendance reports and export functionality.

---

## ✨ Main Features

### 👨‍💼 Admin Features

- Admin login
- Student management
- Teacher management
- Subject management
- Attendance session management
- Attendance monitoring
- Attendance records management

### 👨‍🏫 Teacher Features

- Teacher authentication
- Teacher dashboard
- View assigned subjects
- Create attendance sessions
- Open and close attendance sessions
- QR-based attendance
- Face Recognition attendance
- Manual absent marking
- Automatic absent marking when a session is closed
- Session-wise attendance reports
- Attendance statistics
- Excel export
- PDF export

### 👨‍🎓 Student Features

- Student information management
- Student identification through unique Student ID
- Face data support for Face Recognition attendance
- QR Code based identification

---

## 📝 Attendance Workflow

The attendance process works as follows:

```text
Teacher Login
     ↓
Select Subject
     ↓
Open Attendance Session
     ↓
Student Attendance
     ├── Face Recognition
     ├── QR Code
     └── Manual
     ↓
Teacher Closes Session
     ↓
Students Without Attendance
     ↓
Automatically Marked Absent
     ↓
Attendance Report
     ↓
Excel / PDF Export