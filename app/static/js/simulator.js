let socket;
let audioContext;
let processor;
let inputSource;
let analyser;
let bgAudio;
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
        // Enforce single connection
        if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
            console.log("Closing existing socket before starting new one.");
            socket.close();
            // Wait a tiny bit for cleanup?
        }
        clearAudio(); // Stop any pending audio

        // 1. Initialize Audio Context (16kHz for consistency)
        audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });

        // Get persistent ID for this tab/session
        let clientId = sessionStorage.getItem("voice_client_id");
        if (!clientId) {
            clientId = crypto.randomUUID();
            sessionStorage.setItem("voice_client_id", clientId);
        }

        // 2. Connect WebSocket
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        socket = new WebSocket(`${protocol}//${window.location.host}/api/v1/ws/media-stream?client=browser&client_id=${clientId}`);

        socket.onopen = () => {
            isCallActive = true;
            updateUI(true);
            statusDiv.innerText = "Conectado. Habla ahora.";
            statusDiv.className = "text-emerald-400 font-mono mb-4 text-lg animate-pulse";

            // Send START event so backend initializes stream_id properly
            socket.send(JSON.stringify({
                event: "start",
                start: {
                    streamSid: clientId, // Use client ID as stream ID for browser
                    callSid: clientId
                }
            }));

            // Start Audio Capture (which also starts Visualizer/VAD)
            setupAudioCapture();
        };

        socket.onmessage = async (event) => {
            const msg = JSON.parse(event.data);
            if (msg.type === 'audio') {
                // Play audio from server
                console.log(`🔊 PLAYING AUDIO PACKET | Size: ${msg.data.length}`);
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
            } else if (msg.type === 'config') {
                // Handle Config (e.g. Background Sound)
                const bgSound = msg.config?.background_sound;
                const bgSoundUrl = msg.config?.background_sound_url;

                let sourceUrl = null;

                if (bgSoundUrl && bgSoundUrl.startsWith('http')) {
                    sourceUrl = bgSoundUrl;
                    console.log(`🎵 Starting External Background Sound: ${sourceUrl}`);
                } else if (bgSound && bgSound !== 'none') {
                    sourceUrl = `/static/sounds/${bgSound}.mp3`;
                    console.log(`🎵 Starting Local Background Sound: ${bgSound}`);
                }

                if (sourceUrl) {
                    if (bgAudio) { bgAudio.pause(); bgAudio = null; }

                    bgAudio = new Audio(sourceUrl);
                    bgAudio.loop = true; // Loop is ENABLED here
                    bgAudio.volume = 0.1; // 10% volume (Subtle)
                    bgAudio.play().catch(e => console.warn("Background Audio Auto-play blocked (Interact first)?", e));
                }
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
    if (bgAudio) { bgAudio.pause(); bgAudio = null; }
    statusDiv.innerText = "Llamada Finalizada";
    statusDiv.className = "text-slate-500 font-mono mb-4 text-lg";
}

async function setupAudioCapture() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    inputSource = audioContext.createMediaStreamSource(stream);

    // 1. Analyser for VAD (Direct Mic Connection)
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 2048;
    inputSource.connect(analyser);

    // 2. Processor for Streaming
    processor = audioContext.createScriptProcessor(4096, 1, 1);
    inputSource.connect(processor);

    // 3. Mute Output (Required for Chrome to fire processor)
    const mute = audioContext.createGain();
    mute.gain.value = 0;
    processor.connect(mute);
    mute.connect(audioContext.destination);

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
    };

    startVisualizer();
}

const activeSources = [];
let nextStartTime = 0;

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

    // Scheduling Magic
    const currentTime = audioContext.currentTime;
    if (nextStartTime < currentTime) {
        nextStartTime = currentTime;
    }

    source.start(nextStartTime);
    nextStartTime += audioBuf.duration;
}

function clearAudio() {
    activeSources.forEach(src => {
        try { src.stop(); } catch (e) { }
    });
    activeSources.length = 0;
    nextStartTime = 0;
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

function startVisualizer() {
    if (!analyser) return;

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    let speechFrames = 0; // VAD State

    const draw = () => {
        if (!isCallActive) return;
        requestAnimationFrame(draw);

        analyser.getByteFrequencyData(dataArray);

        canvasCtx.fillStyle = '#0f172a';
        canvasCtx.fillRect(0, 0, canvas.width, canvas.height);

        const barWidth = (canvas.width / bufferLength) * 2.5;
        let barHeight;
        let x = 0;

        // --- Local VAD (Barge-In) ---
        let sum = 0;
        // --- Local VAD (Barge-In) 2.0: Band-Pass & Debounce ---
        let speechSum = 0;
        let speechBins = 0;

        // FFT Size 2048 @ 16kHz = ~7.8Hz per bin
        // Human Voice Fundamental: ~85Hz to ~255Hz
        // Harmonics up to 3000Hz typically dominant.
        // Range: 80Hz (Bin 10) to 1000Hz (Bin 128) for robust detection
        // Focusing on lower partials avoids high-pitch hiss (fans) and low rumble (<80Hz)

        const startBin = 10;  // ~80Hz
        const endBin = 200;   // ~1500Hz (Strong voice detection range)

        for (let i = startBin; i < endBin; i++) {
            speechSum += dataArray[i];
            speechBins++;
        }
        const average = speechSum / speechBins;

        // Tuning: 
        // Threshold: 35 (Higher than floor noise, sensitive to voice)
        // Persistence: 10 consecutive frames (~160ms) to trigger
        // This validates "Sustained" speech vs "Transient" noise (coughs, clicks).

        if (average > 35 && activeSources.length > 0) {
            speechFrames++;
        } else {
            speechFrames = 0; // Strict reset: sound must be continuous
        }

        if (speechFrames > 10) {
            console.log(`🎤 VAD Triggered (Sustained): Level ${average.toFixed(1)} for ${speechFrames} frames`);
            clearAudio();
            speechFrames = 0; // Reset after trigger to prevent spam
        }
        // -----------------------------
        // -----------------------------

        for (let i = 0; i < bufferLength; i++) {
            barHeight = dataArray[i] / 2;
            canvasCtx.fillStyle = `rgb(${barHeight + 100}, 50, 50)`;
            canvasCtx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
            x += barWidth + 1;
        }
    };
    draw();
}
