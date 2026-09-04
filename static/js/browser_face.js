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

/*
============================================================
SESSION ID
============================================================
*/

const currentSessionId =
    typeof sessionId !== "undefined"
        ? sessionId
        : "";


/*
============================================================
LAST PRESENT STUDENT
============================================================
*/

let lastPresentStudentId = "";
let lastPresentTime = 0;


/*
============================================================
START CAMERA
============================================================
*/

async function startCamera() {

    try {

        stopped = false;
        processing = false;

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


        /*
        --------------------------------------------------------
        STOP OLD CAMERA
        --------------------------------------------------------
        */

        if (stream) {

            stream.getTracks().forEach(
                track => track.stop()
            );

            stream = null;
        }


        /*
        --------------------------------------------------------
        OPEN CAMERA
        --------------------------------------------------------
        */

        stream =
            await navigator.mediaDevices.getUserMedia({

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


        /*
        --------------------------------------------------------
        SHOW CAMERA
        --------------------------------------------------------
        */

        video.srcObject = stream;

        video.muted = true;
        video.playsInline = true;

        await video.play();


        if (cameraMessage) {
            cameraMessage.style.display = "none";
        }


        status.innerText = "Camera Started";
        status.className = "badge bg-success";


        startBtn.disabled = true;
        stopBtn.disabled = false;


        /*
        --------------------------------------------------------
        CLEAR OLD INTERVAL
        --------------------------------------------------------
        */

        if (interval) {

            clearInterval(interval);
            interval = null;

        }


        /*
        --------------------------------------------------------
        START FACE SCANNING
        --------------------------------------------------------
        */

        interval = setInterval(
            captureFrame,
            1000
        );


    } catch (error) {

        console.error(
            "Camera Error:",
            error
        );


        if (cameraMessage) {
            cameraMessage.style.display = "flex";
        }


        status.innerText = "Camera Error";
        status.className = "badge bg-danger";


        cameraError.innerText =
            "Camera access failed: " +
            error.message +
            ". Allow camera permission and try again.";


        cameraError.classList.remove(
            "d-none"
        );


        startBtn.disabled = false;
        stopBtn.disabled = true;

    }

}


/*
============================================================
STOP CAMERA
============================================================
*/

function stopCamera() {

    stopped = true;
    processing = false;


    /*
    --------------------------------------------------------
    STOP SCANNING
    --------------------------------------------------------
    */

    if (interval) {

        clearInterval(interval);
        interval = null;

    }


    /*
    --------------------------------------------------------
    STOP CAMERA STREAM
    --------------------------------------------------------
    */

    if (stream) {

        stream.getTracks().forEach(
            track => track.stop()
        );

        stream = null;

    }


    if (video) {
        video.srcObject = null;
    }


    /*
    --------------------------------------------------------
    UI
    --------------------------------------------------------
    */

    if (cameraMessage) {

        cameraMessage.innerText =
            'Click "Start Camera"';

        cameraMessage.style.display =
            "flex";

    }


    status.innerText =
        "Camera Off";

    status.className =
        "badge bg-secondary";


    startBtn.disabled = false;
    stopBtn.disabled = true;

}


/*
============================================================
ATTENDANCE PRESENT
IMPORTANT:
CAMERA MUST CONTINUE FOR NEXT STUDENT
============================================================
*/

function attendanceSuccess(data) {

    /*
    DO NOT STOP CAMERA
    DO NOT STOP SCANNING
    */

    stopped = false;
    processing = false;


    lastPresentStudentId =
        String(data.student_id || "");

    lastPresentTime =
        Date.now();


    studentName.innerText =
        data.name || "Student";


    studentId.innerText =
        data.student_id || "-";


    confidence.innerText =
        (data.confidence || 0) + "%";


    status.innerText =
        "Present";

    status.className =
        "badge bg-success";


    if (cameraMessage) {
        cameraMessage.style.display = "none";
    }


    /*
    Keep camera buttons active.
    */

    startBtn.disabled = true;
    stopBtn.disabled = false;

}


/*
============================================================
CAPTURE FRAME
============================================================
*/

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


    if (!currentSessionId) {

        status.innerText =
            "Session ID missing";

        status.className =
            "badge bg-danger";

        return;
    }


    processing = true;


    /*
    --------------------------------------------------------
    CANVAS
    --------------------------------------------------------
    */

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


    /*
    --------------------------------------------------------
    JPEG
    --------------------------------------------------------
    */

    canvas.toBlob(
        sendFrame,
        "image/jpeg",
        0.85
    );

}


/*
============================================================
SEND FRAME TO FLASK
============================================================
*/

function sendFrame(blob) {

    if (
        !blob ||
        stopped ||
        !stream
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
        currentSessionId
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


    .then(async response => {

        let data = null;


        try {

            data =
                await response.json();

        } catch (e) {

            throw new Error(
                "Invalid server response."
            );

        }


        if (!response.ok) {

            throw new Error(
                data.status ||
                "Server error: " +
                response.status
            );

        }


        return data;

    })


    .then(data => {

        if (stopped) {
            return;
        }


        /*
        ----------------------------------------------------
        STUDENT NAME
        ----------------------------------------------------
        */

        studentName.innerText =
            data.name ||
            "Waiting...";


        /*
        ----------------------------------------------------
        STUDENT ID
        ----------------------------------------------------
        */

        studentId.innerText =
            data.student_id ||
            "-";


        /*
        ----------------------------------------------------
        CONFIDENCE
        ----------------------------------------------------
        */

        confidence.innerText =
            (
                data.confidence || 0
            ) + "%";


        /*
        ----------------------------------------------------
        STATUS
        ----------------------------------------------------
        */

        status.innerText =
            data.status ||
            "Processing";


        const currentStatus =
            (
                data.status || ""
            ).toLowerCase();


        /*
        ====================================================
        PRESENT
        ====================================================
        */

        if (data.success) {

            attendanceSuccess(data);

            return;

        }


        /*
        ====================================================
        CONFIRMING
        ====================================================
        */

        if (
            currentStatus.includes(
                "confirming"
            )
        ) {

            status.className =
                "badge bg-warning text-dark";

            return;

        }


        /*
        ====================================================
        ALREADY MARKED
        ====================================================
        */

        if (
            currentStatus.includes(
                "already marked"
            )
        ) {

            /*
            Same student just marked?
            Keep Present visible briefly.
            */

            if (
                lastPresentStudentId &&
                String(data.student_id || "") ===
                    lastPresentStudentId &&
                (
                    Date.now() -
                    lastPresentTime
                ) < 6000
            ) {

                status.innerText =
                    "Present";

                status.className =
                    "badge bg-success";

            } else {

                status.innerText =
                    "Already Marked";

                status.className =
                    "badge bg-info text-dark";

            }


            /*
            VERY IMPORTANT:
            Camera keeps scanning.
            */

            stopped = false;

            return;

        }


        /*
        ====================================================
        NO FACE
        ====================================================
        */

        if (
            currentStatus.includes(
                "no face"
            )
        ) {

            status.className =
                "badge bg-secondary";

            return;

        }


        /*
        ====================================================
        FACE TOO SMALL
        ====================================================
        */

        if (
            currentStatus.includes(
                "too small"
            )
        ) {

            status.className =
                "badge bg-warning text-dark";

            return;

        }


        /*
        ====================================================
        UNKNOWN FACE
        ====================================================
        */

        if (
            currentStatus.includes(
                "unknown"
            )
        ) {

            status.className =
                "badge bg-danger";

            return;

        }


        /*
        ====================================================
        OTHER
        ====================================================
        */

        status.className =
            "badge bg-danger";

    })


    .catch(error => {

        console.error(
            "Face request error:",
            error
        );


        if (!stopped) {

            status.innerText =
                error.message ||
                "Connection error";

            status.className =
                "badge bg-danger";

        }

    })


    .finally(() => {

        processing = false;

    });

}


/*
============================================================
BUTTON EVENTS
============================================================
*/

if (startBtn) {

    startBtn.addEventListener(
        "click",
        startCamera
    );

}


if (stopBtn) {

    stopBtn.addEventListener(
        "click",
        stopCamera
    );

}


/*
============================================================
INITIAL STATE
============================================================
*/

if (stopBtn) {
    stopBtn.disabled = true;
}


/*
============================================================
PAGE LEAVE
============================================================
*/

window.addEventListener(
    "beforeunload",
    () => {

        if (stream) {

            stream
                .getTracks()
                .forEach(
                    track => track.stop()
                );

        }


        if (interval) {

            clearInterval(interval);

        }

    }
);