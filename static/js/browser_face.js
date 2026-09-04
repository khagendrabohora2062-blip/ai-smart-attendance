
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


// =====================================================
// START CAMERA
// =====================================================

async function startCamera() {

    try {

        cameraError.classList.add("d-none");
        cameraError.innerText = "";

        if (!navigator.mediaDevices ||
            !navigator.mediaDevices.getUserMedia) {

            throw new Error(
                "Your browser does not support camera access."
            );

        }


        // Stop previous stream

        if (stream) {

            stream.getTracks().forEach(
                track => track.stop()
            );

        }


        // Browser camera

        stream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: "user",
                width: {
                    ideal: 1280
                },
                height: {
                    ideal: 720
                }
            },
            audio: false
        });


        video.srcObject = stream;

        await video.play();


        cameraMessage.style.display = "none";

        status.innerText = "Camera Started";
        status.className = "badge bg-success";

        startBtn.disabled = true;
        stopBtn.disabled = false;


        // Capture every 1 second

        if (interval) {
            clearInterval(interval);
        }

        interval = setInterval(
            captureFrame,
            1000
        );

    }

    catch (error) {

        console.error(
            "Camera Error:",
            error
        );

        cameraMessage.style.display = "flex";

        status.innerText = "Camera Error";
        status.className = "badge bg-danger";

        cameraError.innerText =
            "Camera access failed: " +
            error.message +
            ". Please allow camera permission and try again.";

        cameraError.classList.remove("d-none");

    }

}


// =====================================================
// STOP CAMERA
// =====================================================

function stopCamera() {

    if (interval) {

        clearInterval(interval);
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
        "Click \"Start Camera\"";

    cameraMessage.style.display = "flex";

    status.innerText = "Camera Off";
    status.className = "badge bg-secondary";

    startBtn.disabled = false;
    stopBtn.disabled = true;

    processing = false;

}


// =====================================================
// CAPTURE FRAME
// =====================================================

function captureFrame() {

    if (!stream ||
        video.readyState < 2 ||
        processing) {

        return;

    }

    if (
        video.videoWidth <= 0 ||
        video.videoHeight <= 0
    ) {

        return;

    }

    processing = true;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext("2d");

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


// =====================================================
// SEND IMAGE TO FLASK
// =====================================================

function sendFrame(blob) {

    if (!blob) {

        processing = false;
        return;

    }

    const formData = new FormData();

    formData.append(
        "image",
        blob,
        "camera.jpg"
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
            credentials: "same-origin"
        }
    )

    .then(response => {

        if (!response.ok) {
            throw new Error(
                "Server error: " +
                response.status
            );
        }

        return response.json();

    })

    .then(data => {

        studentName.innerText =
            data.name || "Waiting...";

        studentId.innerText =
            data.student_id || "-";

        confidence.innerText =
            (data.confidence || 0) + "%";

        status.innerText =
            data.status || "Processing";


        if (data.success) {

            status.className =
                "badge bg-success";

        }

        else if (
            (data.status || "")
                .toLowerCase()
                .includes("confirm")
        ) {

            status.className =
                "badge bg-warning text-dark";

        }

        else if (
            (data.status || "")
                .toLowerCase()
                .includes("already")
        ) {

            status.className =
                "badge bg-info text-dark";

        }

        else {

            status.className =
                "badge bg-danger";

        }

    })

    .catch(error => {

        console.error(
            "Face request error:",
            error
        );

    })

    .finally(() => {

        processing = false;

    });

}


// =====================================================
// BUTTON EVENTS
// =====================================================

startBtn.addEventListener(
    "click",
    startCamera
);

stopBtn.addEventListener(
    "click",
    stopCamera
);


// =====================================================
// INITIAL STATE
// =====================================================

stopBtn.disabled = true;


// =====================================================
// STOP WHEN LEAVING PAGE
// =====================================================

window.addEventListener(
    "beforeunload",
    stopCamera
);
