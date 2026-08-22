import cv2
import time


# ============================================================
# TEACHER QR SCANNER
# ============================================================

def start_teacher_qr_scanner(process_qr):

    # ========================================================
    # QR DETECTOR
    # ========================================================

    detector = cv2.QRCodeDetector()


    # ========================================================
    # CAMERA
    # ========================================================

    camera = cv2.VideoCapture(0)


    # ========================================================
    # CAMERA CHECK
    # ========================================================

    if not camera.isOpened():

        raise Exception(
            "Cannot open webcam. Check camera permission or camera index."
        )


    # ========================================================
    # CAMERA SETTINGS
    # ========================================================

    camera.set(
        cv2.CAP_PROP_FRAME_WIDTH,
        1280
    )

    camera.set(
        cv2.CAP_PROP_FRAME_HEIGHT,
        720
    )


    # ========================================================
    # VARIABLES
    # ========================================================

    last_qr = ""

    last_scan_time = 0

    result_message = "Show Student QR Code"

    result_student = ""

    result_name = ""

    result_color = (255, 255, 255)

    result_time = 0


    # ========================================================
    # SCANNER LOOP
    # ========================================================

    while True:

        success, frame = camera.read()


        # ====================================================
        # CAMERA FRAME ERROR
        # ====================================================

        if not success:

            print(
                "Unable to read camera frame."
            )

            break


        # ====================================================
        # MIRROR CAMERA
        # ====================================================

        frame = cv2.flip(
            frame,
            1
        )


        # ====================================================
        # DETECT QR
        # ====================================================

        data, points, _ = detector.detectAndDecode(
            frame
        )


        # ====================================================
        # QR BOX
        # ====================================================

        if points is not None:

            points = points.astype(int)

            pts = points[0]


            for i in range(len(pts)):

                pt1 = tuple(
                    pts[i]
                )

                pt2 = tuple(
                    pts[
                        (i + 1) % len(pts)
                    ]
                )


                cv2.line(
                    frame,
                    pt1,
                    pt2,
                    (0, 255, 0),
                    3
                )


        # ====================================================
        # HEADER
        # ====================================================

        cv2.rectangle(
            frame,
            (0, 0),
            (frame.shape[1], 75),
            (20, 30, 45),
            -1
        )


        cv2.putText(
            frame,
            "TEACHER QR ATTENDANCE",
            (20, 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.85,
            (0, 255, 255),
            2
        )


        cv2.putText(
            frame,
            "Scan Student QR Code",
            (20, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.60,
            (255, 255, 255),
            1
        )


        # ====================================================
        # QR DETECTED
        # ====================================================

        if data:

            data = data.strip()

            current_time = time.time()


            # =================================================
            # PREVENT REPEATED SCANNING
            # =================================================

            if (
                data != last_qr
                or
                current_time - last_scan_time > 3
            ):


                print(
                    "QR DETECTED:",
                    data
                )


                # =============================================
                # PROCESS QR
                # =============================================

                result = process_qr(
                    data
                )


                # =============================================
                # SAVE LAST SCAN
                # =============================================

                last_qr = data

                last_scan_time = current_time

                result_time = current_time


                # =============================================
                # RESULT
                # =============================================

                result_student = result.get(
                    "student_id",
                    ""
                )

                result_name = result.get(
                    "name",
                    ""
                )

                result_message = result.get(
                    "message",
                    "Unknown Result"
                )


                # =============================================
                # RESULT COLOR
                # =============================================

                if result.get("success"):

                    result_color = (
                        0,
                        255,
                        0
                    )

                    print(
                        "QR ATTENDANCE SUCCESS:",
                        result_name
                    )

                else:

                    result_color = (
                        0,
                        0,
                        255
                    )

                    print(
                        "QR ATTENDANCE:",
                        result_message
                    )


        # ====================================================
        # RESULT PANEL
        # ====================================================

        if result_time > 0:

            elapsed = (
                time.time()
                - result_time
            )

        else:

            elapsed = 999


        # Show result for 4 seconds

        if elapsed < 4:

            panel_y = 100

            panel_height = 150


            cv2.rectangle(
                frame,
                (
                    15,
                    panel_y
                ),
                (
                    frame.shape[1] - 15,
                    panel_y + panel_height
                ),
                (15, 23, 42),
                -1
            )


            # ================================================
            # STUDENT ID
            # ================================================

            if result_student:

                cv2.putText(
                    frame,
                    "Student ID: "
                    + result_student,
                    (35, 135),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (255, 255, 255),
                    2
                )


            # ================================================
            # NAME
            # ================================================

            if result_name:

                cv2.putText(
                    frame,
                    "Name: "
                    + result_name,
                    (35, 170),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (255, 255, 255),
                    2
                )


            # ================================================
            # MESSAGE
            # ================================================

            cv2.putText(
                frame,
                result_message,
                (35, 210),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                result_color,
                2
            )


        else:

            # =================================================
            # DEFAULT MESSAGE
            # =================================================

            cv2.putText(
                frame,
                "Waiting for QR...",
                (35, 130),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (255, 255, 255),
                2
            )


        # ====================================================
        # FOOTER
        # ====================================================

        cv2.rectangle(
            frame,
            (
                0,
                frame.shape[0] - 45
            ),
            (
                frame.shape[1],
                frame.shape[0]
            ),
            (20, 30, 45),
            -1
        )


        cv2.putText(
            frame,
            "Press Q or ESC to close scanner",
            (
                20,
                frame.shape[0] - 15
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.60,
            (255, 255, 255),
            1
        )


        # ====================================================
        # CAMERA WINDOW
        # ====================================================

        cv2.imshow(
            "Teacher QR Attendance",
            frame
        )


        # ====================================================
        # KEYBOARD
        # ====================================================

        key = cv2.waitKey(1) & 0xFF


        if (
            key == 27
            or
            key == ord("q")
            or
            key == ord("Q")
        ):

            break


    # ========================================================
    # RELEASE CAMERA
    # ========================================================

    camera.release()


    cv2.destroyAllWindows()