let socket;
let audioContext;
let processor;
let inputSource;
let isCallActive = false;

const startBtn = document.getElementById('start-btn');
const statusDiv = document.getElementById('status-indicator');
const transcriptBox = document.getElementById('transcript-box');
const canvas = document.getElementById('visualizer');
const canvasCtx = canvas.getContext('2d');

async function toggleCall() {
    if (!isCallActive) {
        await startCall();
    } else {
        stopCall();
    }
}

async function startCall() {
    try {
        // 1. Initialize Audio Context (16kHz for consistency)
        audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });

        // 2. Connect WebSocket
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        socket = new WebSocket(`${protocol}//${window.location.host}/api/v1/ws/media-stream?client=browser`);

        socket.onopen = () => {
            isCallActive = true;
            updateUI(true);
            statusDiv.innerText = "Conectado. Habla ahora.";
            statusDiv.className = "text-emerald-400 font-mono mb-4 text-lg animate-pulse";

            // Start Audio Capture
            setupAudioCapture();
        };

        socket.onmessage = async (event) => {
            const msg = JSON.parse(event.data);
            if (msg.type === 'audio') {
                // Play audio from server
                playAudioChunk(msg.data);
                statusDiv.innerText = "Andrea está hablando...";
                statusDiv.className = "text-blue-400 font-mono mb-4 text-lg";
            } else if (msg.type === 'transcript') {
                // Append transcript
                const p = document.createElement('p');
                p.className = msg.role === 'user' ? 'text-right text-emerald-400' : 'text-left text-blue-400';
                p.innerText = `${msg.role === 'user' ? 'Tú' : 'Andrea'}: ${msg.text}`;
                transcriptBox.appendChild(p);
                transcriptBox.scrollTop = transcriptBox.scrollHeight;

            } else if (msg.event === 'clear') {
                // Stop current audio (Barge-in)
                clearAudio();
                statusDiv.innerText = "Interrupción detectada.";
            }
        };

        socket.onclose = () => stopCall();

    } catch (err) {
        console.error("Error starting call:", err);
        alert("¡Se requiere acceso al micrófono!");
    }
}

function stopCall() {
    isCallActive = false;
    updateUI(false);
    if (socket) socket.close();
    if (audioContext) audioContext.close();
    if (processor) processor.disconnect();
    statusDiv.innerText = "Llamada Finalizada";
    statusDiv.className = "text-slate-500 font-mono mb-4 text-lg";
}

async function setupAudioCapture() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    inputSource = audioContext.createMediaStreamSource(stream);

    // Processor to capture raw PCM
    processor = audioContext.createScriptProcessor(4096, 1, 1);

    inputSource.connect(processor);
    processor.connect(audioContext.destination);

    processor.onaudioprocess = (e) => {
        if (!isCallActive || socket.readyState !== WebSocket.OPEN) return;

        const inputData = e.inputBuffer.getChannelData(0);
        // Convert Float32 to Int16
        const buffer = new ArrayBuffer(inputData.length * 2);
        const view = new DataView(buffer);
        for (let i = 0; i < inputData.length; i++) {
            let s = Math.max(-1, Math.min(1, inputData[i]));
            view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
        }

        // Send as base64
        const base64Audio = arrayBufferToBase64(buffer);
        socket.send(JSON.stringify({
            event: "media",
            media: { payload: base64Audio }
        }));

        // Visualizer
        drawVisualizer(inputData);
    };
}

const activeSources = [];

function playAudioChunk(base64Data) {
    if (!audioContext) return;

    // Decode base64 to buffer
    const binaryString = window.atob(base64Data);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }

    // Since it's raw PCM 16bit 16kHz
    const int16 = new Int16Array(bytes.buffer);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) {
        float32[i] = int16[i] / 32768.0;
    }

    const audioBuf = audioContext.createBuffer(1, float32.length, 16000);
    audioBuf.getChannelData(0).set(float32);

    const source = audioContext.createBufferSource();
    source.buffer = audioBuf;
    source.connect(audioContext.destination);

    source.onended = () => {
        const index = activeSources.indexOf(source);
        if (index > -1) activeSources.splice(index, 1);
    };

    activeSources.push(source);
    source.start();
}

function clearAudio() {
    activeSources.forEach(src => {
        try { src.stop(); } catch (e) { }
    });
    activeSources.length = 0;
}

function updateUI(active) {
    startBtn.innerText = active ? "Terminar Llamada" : "Iniciar Prueba";
    startBtn.className = active
        ? "px-6 py-2 bg-red-600 hover:bg-red-500 rounded font-bold shadow-lg transition-all"
        : "px-6 py-2 bg-emerald-600 hover:bg-emerald-500 rounded font-bold shadow-lg transition-all";
}

function arrayBufferToBase64(buffer) {
    let binary = '';
    const bytes = new Uint8Array(buffer);
    const len = bytes.byteLength;
    for (let i = 0; i < len; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return window.btoa(binary);
}

function drawVisualizer(dataArray) {
    canvasCtx.fillStyle = 'rgb(15, 23, 42)';
    canvasCtx.fillRect(0, 0, canvas.width, canvas.height);
    canvasCtx.lineWidth = 2;
    canvasCtx.strokeStyle = 'rgb(52, 211, 153)';
    canvasCtx.beginPath();

    const sliceWidth = canvas.width / dataArray.length;
    let x = 0;

    for (let i = 0; i < dataArray.length; i++) {
        const v = dataArray[i] * 50 + 50; // Scale center
        const y = v; // Simple wave

        if (i === 0) canvasCtx.moveTo(x, y);
        else canvasCtx.lineTo(x, y);
        x += sliceWidth;
    }
    canvasCtx.lineTo(canvas.width, canvas.height / 2);
    canvasCtx.stroke();
}
