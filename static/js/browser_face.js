const video = document.getElementById("video");
const canvas = document.getElementById("canvas");

const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");

const studentName = document.getElementById("studentName");
const status = document.getElementById("status");
const confidence = document.getElementById("confidence");

let stream = null;
let interval = null;


// ======================================
// Start Camera
// ======================================

startBtn.onclick = async () => {

    try {

        stream = await navigator.mediaDevices.getUserMedia({
            video: true,
            audio: false
        });

        video.srcObject = stream;

        status.innerHTML = "Camera Started";
        status.className = "badge bg-success";

        interval = setInterval(captureFrame, 1000);

    }

    catch (err) {

        console.error(err);

        alert("Unable to access camera.");

    }

};


// ======================================
// Stop Camera
// ======================================

stopBtn.onclick = () => {

    if (interval) {

        clearInterval(interval);

    }

    if (stream) {

        stream.getTracks().forEach(track => track.stop());

    }

    status.innerHTML = "Stopped";
    status.className = "badge bg-danger";

};


// ======================================
// Capture Frame
// ======================================

function captureFrame() {

    const ctx = canvas.getContext("2d");

    ctx.drawImage(
        video,
        0,
        0,
        canvas.width,
        canvas.height
    );

    canvas.toBlob(sendFrame, "image/jpeg");

}


// ======================================
// Send Frame to Flask
// ======================================

function sendFrame(blob) {

    const formData = new FormData();

    formData.append("image", blob);

    formData.append("session_id", sessionId);

    fetch("/teacher/face/recognize", {

        method: "POST",

        body: formData

    })

    .then(response => response.json())

    .then(data => {

        studentName.innerHTML = data.name;

        confidence.innerHTML = data.confidence + "%";

        status.innerHTML = data.status;

        if (data.success) {

            status.className = "badge bg-success";

        }

        else {

            status.className = "badge bg-danger";

        }

    })

    .catch(error => {

        console.log(error);

    });

}