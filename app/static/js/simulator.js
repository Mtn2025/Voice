let socket;
let audioContext;
let processor;
let inputSource;
let analyser;
let bgAudio;
let localStream; // New
let isCallActive = false;
let hangupPending = false;
let activeAudioSources = 0;
let lastAudioTime = 0;

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
        // Clear Transcript for new call
        transcriptBox.innerHTML = "";

        // Enforce single connection
        if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
            console.log("Closing existing socket before starting new one.");
            socket.close();
        }
        clearAudio(); // Stop any pending audio

        // 1. Initialize Audio Context (16kHz for consistency)
        audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });

        // ALWAYS generate a new ID for each call to ensure unique DB entries
        let clientId = crypto.randomUUID();

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
            } else if (msg.type === 'control' && msg.action === 'end_call') {
                console.log("☎️ Received server request to end call after audio.");
                hangupPending = true;
                checkHangup();
            }
        };

        socket.onclose = () => stopCall(false);

    } catch (err) {
        console.error("Error starting call:", err);
        alert("¡Se requiere acceso al micrófono!");
    }
}

function stopCall(immediate = true) {
    isCallActive = false;
    updateUI(false);

    // Stop Microphone IMMEDIATELY
    if (processor) {
        try { processor.disconnect(); } catch (e) { }
    }
    if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
        localStream = null;
    }

    // Close socket if open
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
    }

    if (bgAudio) { bgAudio.pause(); bgAudio = null; }

    if (immediate) {
        if (audioContext) try { audioContext.close(); } catch (e) { }
        statusDiv.innerText = "Llamada Finalizada";
        statusDiv.className = "text-slate-500 font-mono mb-4 text-lg";
    } else {
        // Graceful exit: allow audio buffer to drain
        statusDiv.innerText = "Cerrando...";
        setTimeout(() => {
            if (audioContext) try { audioContext.close(); } catch (e) { }
            statusDiv.innerText = "Llamada Finalizada";
            document.body.dispatchEvent(new Event('refreshHistory')); // Trigger Dashboard Update
        }, 3000);
    }

    // Immediate stop also triggers refresh
    if (immediate) {
        document.body.dispatchEvent(new Event('refreshHistory'));
    }
}

async function setupAudioCapture() {
    localStream = await navigator.mediaDevices.getUserMedia({
        audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
            channelCount: 1,
            sampleRate: 16000
        }
    });
    inputSource = audioContext.createMediaStreamSource(localStream);

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

        // 1. Calculate RMS (Volume Level)
        let sum = 0;
        for (let i = 0; i < inputData.length; i++) {
            sum += inputData[i] * inputData[i];
        }
        const rms = Math.sqrt(sum / inputData.length);

        // 2. Frequency Analysis (Voice vs Noise)
        // Get FFT Data from Analyser
        const bufferLength = analyser.frequencyBinCount; // 1024 for fftSize 2048
        const dataArray = new Uint8Array(bufferLength);
        analyser.getByteFrequencyData(dataArray);

        // Calculate Voice Score (Avg intensity in 80Hz - 1500Hz range)
        // Bin Size = 16000 / 2048 = ~7.8Hz
        // 80Hz ~= Bin 10
        // 1500Hz ~= Bin 192
        let voiceSum = 0;
        let voiceBins = 0;
        for (let i = 10; i < 195; i++) {
            voiceSum += dataArray[i];
            voiceBins++;
        }
        const voiceScore = voiceSum / voiceBins; // 0 - 255

        // 3. UI Updates (Throttle)
        if (Math.random() < 0.1) { // Update ~10% of frames to save DOM
            document.getElementById('cur-rms').innerText = rms.toFixed(3);
            document.getElementById('cur-voice').innerText = voiceScore.toFixed(0);
        }

        // 4. Dynamic Gate Logic
        // Read Sliders (Live)
        const micSens = parseFloat(document.getElementById('vad-sensitivity').value);
        const voiceThresh = parseFloat(document.getElementById('vad-voice-threshold').value);

        // Update Slider Labels
        document.getElementById('vad-sens-val').innerText = micSens.toFixed(3);
        document.getElementById('vad-voice-val').innerText = voiceThresh;

        // Condition: Must be Loud Enough (RMS) AND Sound like Voice (Freq)
        // Exception: If RMS is extremely high (> 0.5), pass anyway (Screaming/Close mic exception)
        const isVoice = (rms > micSens && voiceScore > voiceThresh) || (rms > 0.5);

        // Convert Float32 to Int16
        const buffer = new ArrayBuffer(inputData.length * 2);
        const view = new DataView(buffer);

        if (!isVoice) {
            // SILENCE / NOISE SUPPRESSION: Send Zeros
            for (let i = 0; i < inputData.length; i++) {
                view.setInt16(i * 2, 0, true);
            }
        } else {
            // VALID SPEECH: Convert normally
            for (let i = 0; i < inputData.length; i++) {
                let s = Math.max(-1, Math.min(1, inputData[i]));
                view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
            }
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

function checkHangup() {
    if (hangupPending && activeSources.length === 0) {
        console.log("📞 Audio finished. Executing pending hangup.");
        stopCall(false);
    }
}

// --- Global Flag for Suppression ---
let suppressEndMark = false;

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

        // Check if we need to hang up
        if (hangupPending && activeSources.length === 0) {
            console.log("📞 Audio finished. Executing pending hangup.");
            stopCall(false);
        }

        // If queue is empty, notify backend that playback finished
        if (activeSources.length === 0) {
            console.log("🔊 Playback Finished. Resetting UI.");

            // UI UPDATE: Confirm listening state
            statusDiv.innerText = "Escuchando...";
            statusDiv.className = "text-emerald-400 font-mono mb-4 text-lg animate-pulse";

            // LOGIC UPDATE: Only send 'speech_ended' if NOT suppressed (i.e. Natural End)
            if (!suppressEndMark) {
                console.log("✅ Sending 'speech_ended' mark to Server.");
                if (socket && socket.readyState === WebSocket.OPEN) {
                    socket.send(JSON.stringify({ event: "mark", mark: "speech_ended" }));
                }
            } else {
                console.log("🤫 'speech_ended' suppressed (Local VAD / Echo Recovery).");
            }
        }
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

function clearAudio(isVAD = false) {
    if (isVAD) {
        suppressEndMark = true; // Prevent telling server we stopped
    }

    activeSources.forEach(src => {
        try { src.stop(); } catch (e) { }
    });
    activeSources.length = 0;
    nextStartTime = 0;

    // Reset flag after a short delay to ensure onended handlers fired
    setTimeout(() => {
        suppressEndMark = false;
    }, 100);
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

// --- Persistence & Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    // Load Saved Values
    const savedSens = localStorage.getItem('vad-sensitivity');
    const savedVoice = localStorage.getItem('vad-voice-threshold');

    if (savedSens) {
        const el = document.getElementById('vad-sensitivity');
        if (el) {
            el.value = savedSens;
            document.getElementById('vad-sens-val').innerText = savedSens;
        }
    }
    if (savedVoice) {
        const el = document.getElementById('vad-voice-threshold');
        if (el) {
            el.value = savedVoice;
            document.getElementById('vad-voice-val').innerText = savedVoice;
        }
    }

    // Attach Save Listeners
    document.getElementById('vad-sensitivity')?.addEventListener('input', (e) => {
        localStorage.setItem('vad-sensitivity', e.target.value);
    });
    document.getElementById('vad-voice-threshold')?.addEventListener('input', (e) => {
        localStorage.setItem('vad-voice-threshold', e.target.value);
    });
});

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
        // Calculate Voice Score (Same logic as onaudioprocess)
        // Range: 80Hz (Bin 10) to 1500Hz (Bin 195)
        let voiceSum = 0;
        let voiceBins = 0;
        for (let i = 10; i < 195; i++) {
            voiceSum += dataArray[i];
            voiceBins++;
        }
        const currentVoiceScore = voiceSum / voiceBins;

        // Approximate RMS from Freq Data (Not perfect but fast)
        // Actually, let's use the Voice Score as the main trigger for barge-in
        // It's safer than raw volume.

        // Read Current Thresholds
        const micSens = parseFloat(document.getElementById('vad-sensitivity').value) * 255 * 2; // Rough mapping to 0-255 scale? No, keep separate.
        // Actually we don't have RMS here easily without re-calculating from time domain or passing it.
        // But we can trust VoiceScore for "Speech" detection.

        const voiceThresh = parseFloat(document.getElementById('vad-voice-threshold').value);

        // Logic: ONLY interrupt if VoiceScore is high enough.
        // We use a slightly higher threshold for **Interruption** than for **Transmission** 
        // to avoid "Clipping" the bot for minor noises.
        const interruptionThreshold = voiceThresh;

        if (currentVoiceScore > interruptionThreshold && activeSources.length > 0) {
            speechFrames++;
        } else {
            speechFrames = 0;
        }

        if (speechFrames > 8) { // ~130ms of sustained voice
            // console.log(`🎤 VAD Triggered (Voice Score: ${currentVoiceScore.toFixed(0)})...`);
            clearAudio(true);
            speechFrames = 0;
        }
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
