const video = document.getElementById("video");
const canvas = document.getElementById("canvas");

const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");

const studentName = document.getElementById("studentName");
const studentId = document.getElementById("studentId");
const status = document.getElementById("status");
const confidence = document.getElementById("confidence");

const cameraMessage = document.getElementById("cameraMessage");
const cameraError = document.getElementById("cameraError");

let stream = null;
let interval = null;
let processing = false;
let stopped = false;


// ============================================================
// START BROWSER CAMERA
// ============================================================

async function startCamera() {

    try {

        stopped = false;

        cameraError.classList.add("d-none");
        cameraError.innerText = "";

        if (
            !navigator.mediaDevices ||
            !navigator.mediaDevices.getUserMedia
        ) {

            throw new Error(
                "Browser camera is not supported."
            );
        }


        // ----------------------------------------------------
        // Stop old camera
        // ----------------------------------------------------

        if (stream) {

            stream.getTracks().forEach(
                track => track.stop()
            );

            stream = null;
        }


        // ----------------------------------------------------
        // OPEN DEVICE CAMERA
        // ----------------------------------------------------

        stream = await navigator.mediaDevices.getUserMedia({

            video: {
                facingMode: {
                    ideal: "user"
                },

                width: {
                    ideal: 1280
                },

                height: {
                    ideal: 720
                }
            },

            audio: false
        });


        // ----------------------------------------------------
        // SHOW CAMERA
        // ----------------------------------------------------

        video.srcObject = stream;

        await video.play();


        cameraMessage.style.display = "none";

        status.innerText = "Camera Started";

        status.className =
            "badge bg-success";


        startBtn.disabled = true;

        stopBtn.disabled = false;


        // ----------------------------------------------------
        // START FACE SCANNING
        // ----------------------------------------------------

        if (interval) {

            clearInterval(
                interval
            );
        }


        interval = setInterval(
            captureFrame,
            900
        );


    } catch (error) {

        console.error(
            "Camera Error:",
            error
        );


        cameraMessage.style.display =
            "flex";


        status.innerText =
            "Camera Error";

        status.className =
            "badge bg-danger";


        cameraError.innerText =
            "Camera access failed: "
            +
            error.message
            +
            ". Allow camera permission and try again.";


        cameraError.classList.remove(
            "d-none"
        );
    }
}


// ============================================================
// STOP CAMERA
// ============================================================

function stopCamera() {

    stopped = true;


    if (interval) {

        clearInterval(
            interval
        );

        interval = null;
    }


    if (stream) {

        stream.getTracks().forEach(
            track => track.stop()
        );

        stream = null;
    }


    video.srcObject = null;


    cameraMessage.innerText =
        'Click "Start Camera"';


    cameraMessage.style.display =
        "flex";


    status.innerText =
        "Camera Off";

    status.className =
        "badge bg-secondary";


    startBtn.disabled =
        false;

    stopBtn.disabled =
        true;


    processing =
        false;
}


// ============================================================
// CAPTURE FRAME
// ============================================================

function captureFrame() {

    if (
        stopped ||
        !stream ||
        processing
    ) {

        return;
    }


    if (
        video.readyState < 2 ||
        video.videoWidth <= 0 ||
        video.videoHeight <= 0
    ) {

        return;
    }


    processing = true;


    canvas.width =
        video.videoWidth;

    canvas.height =
        video.videoHeight;


    const ctx =
        canvas.getContext(
            "2d",
            {
                willReadFrequently: true
            }
        );


    ctx.drawImage(
        video,
        0,
        0,
        canvas.width,
        canvas.height
    );


    canvas.toBlob(
        sendFrame,
        "image/jpeg",
        0.85
    );
}


// ============================================================
// SEND FRAME TO FLASK
// ============================================================

function sendFrame(blob) {

    if (
        !blob ||
        stopped
    ) {

        processing = false;

        return;
    }


    const formData =
        new FormData();


    formData.append(
        "image",
        blob,
        "browser-camera.jpg"
    );


    formData.append(
        "session_id",
        sessionId
    );


    fetch(
        "/teacher/face/recognize",
        {
            method: "POST",

            body: formData,

            credentials: "same-origin",

            headers: {
                "X-Requested-With":
                    "XMLHttpRequest"
            }
        }
    )


    .then(
        response => {

            if (!response.ok) {

                return response.json()
                    .catch(
                        () => {
                            throw new Error(
                                "Server error: "
                                +
                                response.status
                            );
                        }
                    )
                    .then(
                        data => {
                            throw new Error(
                                data.status
                                ||
                                "Server error: "
                                +
                                response.status
                            );
                        }
                    );
            }


            return response.json();
        }
    )


    .then(
        data => {

            // ----------------------------------------------
            // STUDENT NAME
            // ----------------------------------------------

            studentName.innerText =
                data.name
                ||
                "Waiting...";


            // ----------------------------------------------
            // STUDENT ID
            // ----------------------------------------------

            studentId.innerText =
                data.student_id
                ||
                "-";


            // ----------------------------------------------
            // CONFIDENCE
            // ----------------------------------------------

            confidence.innerText =
                (
                    data.confidence
                    ||
                    0
                )
                +
                "%";


            // ----------------------------------------------
            // STATUS
            // ----------------------------------------------

            status.innerText =
                data.status
                ||
                "Processing";


            const currentStatus =
                (
                    data.status
                    ||
                    ""
                )
                .toLowerCase();


            // ----------------------------------------------
            // SUCCESS
            // ----------------------------------------------

            if (data.success) {

                status.className =
                    "badge bg-success";

            }

            // ----------------------------------------------
            // CONFIRMING
            // ----------------------------------------------

            else if (
                currentStatus.includes(
                    "confirm"
                )
            ) {

                status.className =
                    "badge bg-warning text-dark";

            }

            // ----------------------------------------------
            // ALREADY MARKED
            // ----------------------------------------------

            else if (
                currentStatus.includes(
                    "already"
                )
            ) {

                status.className =
                    "badge bg-info text-dark";

            }

            // ----------------------------------------------
            // NO FACE
            // ----------------------------------------------

            else if (
                currentStatus.includes(
                    "no face"
                )
            ) {

                status.className =
                    "badge bg-secondary";

            }

            // ----------------------------------------------
            // UNKNOWN
            // ----------------------------------------------

            else if (
                currentStatus.includes(
                    "unknown"
                )
            ) {

                status.className =
                    "badge bg-danger";

            }

            // ----------------------------------------------
            // OTHER
            // ----------------------------------------------

            else {

                status.className =
                    "badge bg-danger";
            }
        }
    )


    .catch(
        error => {

            console.error(
                "Face request error:",
                error
            );

            if (!stopped) {

                status.innerText =
                    error.message
                    ||
                    "Connection error";

                status.className =
                    "badge bg-danger";
            }
        }
    )


    .finally(
        () => {

            processing =
                false;
        }
    );
}


// ============================================================
// BUTTON EVENTS
// ============================================================

startBtn.addEventListener(
    "click",
    startCamera
);


stopBtn.addEventListener(
    "click",
    stopCamera
);


// ============================================================
// INITIAL STATE
// ============================================================

stopBtn.disabled =
    true;


// ============================================================
// PAGE LEAVE
// ============================================================

window.addEventListener(
    "beforeunload",
    stopCamera
);