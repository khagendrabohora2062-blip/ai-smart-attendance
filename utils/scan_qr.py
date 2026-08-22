import cv2
from app import create_app
from utils.qr_attendance import mark_qr_attendance


def scan_qr():

    detector = cv2.QRCodeDetector()

    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not camera.isOpened():
        print("Error: Cannot open camera.")
        return None

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print("QR Scanner Started...")
    print("Show QR Code to Camera")
    print("Press ESC to Exit")

    while True:

        success, frame = camera.read()

        if not success:
            break

        # Mirror image
        frame = cv2.flip(frame, 1)

        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Improve detection
        gray = cv2.GaussianBlur(gray, (3, 3), 0)

        data, points, _ = detector.detectAndDecode(gray)

        if data != "":

            if points is not None:

                points = points.astype(int)

                for i in range(4):

                    pt1 = tuple(points[0][i])

                    pt2 = tuple(points[0][(i + 1) % 4])

                    cv2.line(frame, pt1, pt2, (0, 255, 0), 3)

            cv2.putText(
                frame,
                f"Student : {data}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )

            cv2.imshow("QR Attendance Scanner", frame)

            cv2.waitKey(1500)

            camera.release()
            cv2.destroyAllWindows()

            return data

        cv2.putText(
            frame,
            "Show QR Code",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            2
        )

        cv2.imshow("QR Attendance Scanner", frame)

        key = cv2.waitKey(1) & 0xFF

        if key == 27:
            break

    camera.release()
    cv2.destroyAllWindows()

    return None


if __name__ == "__main__":

    app = create_app()

    with app.app_context():

        student_code = scan_qr()

        if student_code:

            success, message = mark_qr_attendance(student_code)

            print(message)

        else:

            print("No QR Code Detected.")