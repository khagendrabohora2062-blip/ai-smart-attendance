import cv2
import winsound


def start_qr_scanner(callback=None):

    detector = cv2.QRCodeDetector()

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        raise Exception("Cannot access camera.")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    scanned_codes = set()

    while True:

        success, frame = cap.read()

        if not success:
            break

        data, bbox, _ = detector.detectAndDecode(frame)

        # ==========================
        # Draw QR Box
        # ==========================
        if bbox is not None:

            bbox = bbox.astype(int)

            for i in range(len(bbox[0])):

                cv2.line(
                    frame,
                    tuple(bbox[0][i]),
                    tuple(bbox[0][(i + 1) % len(bbox[0])]),
                    (0, 255, 0),
                    3
                )

        # ==========================
        # QR Detected
        # ==========================
        if data:

            qr_data = data.strip()

            if qr_data not in scanned_codes:

                scanned_codes.add(qr_data)

                winsound.Beep(1200, 300)

                result = None

                if callback:
                    result = callback(qr_data)

                if result:

                    if result["success"]:
                        color = (0, 255, 0)
                    else:
                        color = (0, 0, 255)

                    cv2.putText(
                        frame,
                        result["message"],
                        (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        color,
                        2
                    )

                    cv2.putText(
                        frame,
                        f"ID : {result['student_id']}",
                        (20, 80),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (255, 255, 255),
                        2
                    )

                    cv2.putText(
                        frame,
                        f"Name : {result['name']}",
                        (20, 120),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (255, 255, 255),
                        2
                    )

                    cv2.imshow(
                        "AI Smart Attendance - Continuous QR Scanner",
                        frame
                    )

                    cv2.waitKey(1500)

        # ==========================
        # Instructions
        # ==========================
        cv2.putText(
            frame,
            "Continuous QR Scanner",
            (20, 170),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 0),
            2
        )

        cv2.putText(
            frame,
            "Show Student QR Code",
            (20, 210),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )

        cv2.putText(
            frame,
            "Press Q to Exit",
            (20, 250),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2
        )

        cv2.imshow(
            "AI Smart Attendance - Continuous QR Scanner",
            frame
        )

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

    cap.release()

    cv2.destroyAllWindows()