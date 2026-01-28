/**
 * Simulator Mixin
 * Handles logic for the Browser Simulator (Microphone, WebSocket, Audio Visualization).
 */
export const SimulatorMixin = {
    simState: 'ready',
    ws: null,
    audioContext: null,
    mediaStream: null,
    processor: null,
    analyser: null,
    visualizerMode: 'wave',
    animationId: null,
    transcripts: [],
    debugLogs: [],
    metrics: { llm_latency: null, tts_latency: null },
    vadLevel: 0,
    isAgentSpeaking: false,

    nextStartTime: 0,
    bgAudio: null,

    // Helper for formatting time in debug log
    formatTime(ts) {
        if (!ts) return '';
        const date = new Date(ts * 1000);
        return date.toLocaleTimeString('en-US', { hour12: false, fractionalSecondDigits: 3 });
    },

    async startTest() {
        if (this.simState === 'connected' || this.simState === 'connecting') {
            this.stopTest();
            return;
        }

        this.transcripts = [];

        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            this.audioContext = new AudioContext({ sampleRate: 16000 });

            if (this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }

            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 2048;

            this.drawVisualizer();

            console.log("AudioContext Initialized");
        } catch (e) {
            console.error("Audio Context Init Failed", e);
            alert("Audio Error: " + e.message);
            return;
        }

        this.simState = 'connecting';

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/media-stream?client=browser`;

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log("WS Connected");
                this.simState = 'connected';
                this.initMicrophone();

                this.ws.send(JSON.stringify({
                    event: 'start',
                    start: {
                        streamSid: 'browser-' + Date.now(),
                        callSid: 'sim-' + Date.now(),
                        media_format: { encoding: 'audio/pcm', sample_rate: 16000, channels: 1 }
                    }
                }));
            };

            this.ws.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);

                    if (msg.event === 'media' || msg.type === 'audio') {
                        const payload = msg.media ? msg.media.payload : msg.data;
                        this.playAudio(payload);
                    } else if (msg.type === 'config') {
                        if (msg.config.background_sound && msg.config.background_sound !== 'none') {
                            this.playBackgroundSound(msg.config.background_sound);
                        }
                    } else if (msg.type === 'debug') {
                        // Simulator 2.0 Debug Event
                        this.debugLogs.unshift(msg);
                        if (this.debugLogs.length > 50) this.debugLogs.pop(); // Keep last 50

                        // Update Metrics
                        if (msg.event === 'vad_level') {
                            this.vadLevel = msg.data.rms;
                        } else if (msg.event === 'llm_latency') {
                            this.metrics.llm_latency = msg.data.duration_ms + ' ms';
                        } else if (msg.event === 'tts_latency') {
                            this.metrics.tts_latency = msg.data.duration_ms + ' ms';
                        } else if (msg.event === 'speech_state') {
                            this.isAgentSpeaking = msg.data.speaking;
                        }
                    } else if (msg.type === 'transcript') {
                        this.transcripts.push({
                            role: msg.role,
                            text: msg.text,
                            timestamp: new Date().toLocaleTimeString()
                        });

                        this.$nextTick(() => {
                            const container = document.getElementById('transcript-container');
                            if (container) container.scrollTop = container.scrollHeight;
                        });
                    }
                } catch (err) {
                    console.error("Error processing WS message:", err);
                }
            };

            this.ws.onclose = () => { this.stopTest(); };
            this.ws.onerror = (e) => { console.error("WS Error", e); this.stopTest(); };

        } catch (e) {
            console.error("Connection failed", e);
            this.stopTest();
        }
    },

    async initMicrophone() {
        try {
            // Re-check context
            if (!this.audioContext) {
                const AudioContext = window.AudioContext || window.webkitAudioContext;
                this.audioContext = new AudioContext({ sampleRate: 16000 });
            }
            if (this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }

            // Connect Analyser if missing
            if (!this.analyser) {
                this.analyser = this.audioContext.createAnalyser();
                this.analyser.fftSize = 256;
            }

            const constraints = {
                audio: {
                    echoCancellation: this.c.denoise,
                    noiseSuppression: this.c.denoise,
                    autoGainControl: true
                }
            };

            this.mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
            const source = this.audioContext.createMediaStreamSource(this.mediaStream);

            source.connect(this.analyser);

            // ----------------------------------------------------------------
            // AUDIO WORKLET MIGRATION (Modern Audio API)
            // ----------------------------------------------------------------
            try {
                // Load the Worklet Module
                await this.audioContext.audioWorklet.addModule('/static/js/audio-worklet-processor.js');

                // Create the Worklet Node
                this.processor = new AudioWorkletNode(this.audioContext, 'pcm-processor');

                // Handle Data from Worklet (Int16 Buffer)
                this.processor.port.onmessage = (event) => {
                    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

                    const pcm16 = event.data;

                    // Convert Int16Array to Base64 (Main Thread)
                    // Note: Base64 encoding is still on main thread, but math/sampling is offloaded.
                    const bytes = new Uint8Array(pcm16.buffer);
                    let binary = '';
                    const len = bytes.byteLength;

                    // Chunked String.fromCharCode to avoid stack overflow on large buffers
                    // 4096 samples = 8192 bytes. Safe for spread or loop.
                    for (let i = 0; i < len; i++) {
                        binary += String.fromCharCode(bytes[i]);
                    }
                    const base64Audio = window.btoa(binary);

                    this.ws.send(JSON.stringify({ event: 'media', media: { payload: base64Audio, track: 'inbound' } }));
                };

                source.connect(this.processor);

                // CRITICAL FIX: Route through Mute Gain to prevent Echo (Direct Monitor)
                const muteGain = this.audioContext.createGain();
                muteGain.gain.value = 0;
                this.processor.connect(muteGain);
                muteGain.connect(this.audioContext.destination);

                console.log("✅ AudioWorklet 'pcm-processor' active");

            } catch (workletErr) {
                console.error("❌ AudioWorklet Failed, falling back to ScriptProcessor", workletErr);

                // FALLBACK: Deprecated ScriptProcessor //
                this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);
                source.connect(this.processor);
                const muteGain = this.audioContext.createGain();
                muteGain.gain.value = 0;
                this.processor.connect(muteGain);
                muteGain.connect(this.audioContext.destination);

                this.processor.onaudioprocess = (e) => {
                    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
                    const inputData = e.inputBuffer.getChannelData(0);
                    const pcm16 = new Int16Array(inputData.length);
                    for (let i = 0; i < inputData.length; i++) {
                        let s = Math.max(-1, Math.min(1, inputData[i]));
                        pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                    }
                    // Base64 logic duplicated here for fallback
                    const bytes = new Uint8Array(pcm16.buffer);
                    let binary = '';
                    for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i]);
                    this.ws.send(JSON.stringify({ event: 'media', media: { payload: window.btoa(binary), track: 'inbound' } }));
                };
            }
        } catch (e) {
            console.error("Mic Access Failed", e);
            alert("Microphone Error: " + e.message);
            this.stopTest();
        }
    },

    stopTest() {
        this.simState = 'ready';

        if (this.ws) {
            this.ws.onclose = null;
            this.ws.close();
            this.ws = null;
        }

        if (this.processor) {
            this.processor.disconnect();
            this.processor.onaudioprocess = null;
            this.processor = null;
        }

        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(t => t.stop());
            this.mediaStream = null;
        }

        if (this.bgAudio) {
            this.bgAudio.pause();
            this.bgAudio = null;
        }

        if (this.audioContext) {
            this.audioContext.close().catch(e => console.error("Ctx close err", e));
            this.audioContext = null;
        }

        if (this.animationId) cancelAnimationFrame(this.animationId);

        const canvas = document.getElementById('visualizer');
        if (canvas) {
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
    },

    playAudio(base64Data) {
        if (!base64Data || !this.audioContext) return;
        try {
            const binaryString = window.atob(base64Data);
            const len = binaryString.length;
            const bytes = new Uint8Array(len);
            for (let i = 0; i < len; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }
            const pcm16 = new Int16Array(bytes.buffer);
            const float32 = new Float32Array(pcm16.length);
            for (let i = 0; i < pcm16.length; i++) {
                float32[i] = pcm16[i] / 32768.0;
            }
            const buffer = this.audioContext.createBuffer(1, float32.length, 16000);
            buffer.copyToChannel(float32, 0);

            // 1. Create Output Analyser if missing
            if (!this.outputAnalyser) {
                this.outputAnalyser = this.audioContext.createAnalyser();
                this.outputAnalyser.fftSize = 256;
                this.outputAnalyser.connect(this.audioContext.destination);
            }

            const source = this.audioContext.createBufferSource();
            source.buffer = buffer;

            // 2. Connect Source -> Analyser -> Destination (Implicit via Analyser connection)
            source.connect(this.outputAnalyser);
            // source.connect(this.audioContext.destination); // Removed direct connect

            const currentTime = this.audioContext.currentTime;
            if (this.nextStartTime < currentTime) {
                this.nextStartTime = currentTime;
            }
            source.start(this.nextStartTime);
            this.nextStartTime += buffer.duration;
        } catch (e) {
            console.error("Playback Error", e);
        }
    },

    playBackgroundSound(soundName) {
        if (this.bgAudio) {
            this.bgAudio.pause();
            this.bgAudio = null;
        }
        const volume = 0.1;
        const soundFilePath = `/static/sounds/${soundName}.wav`;
        console.log(`Playing loop: ${soundFilePath}`);
        this.bgAudio = new Audio(soundFilePath);
        this.bgAudio.loop = true;
        this.bgAudio.volume = volume;
        this.bgAudio.play().catch(e => console.warn("Background Audio Play failed", e));
    },

    setVisualizer(mode) {
        this.visualizerMode = mode;
        if (window.localStorage) localStorage.setItem('sim_visualizerMode', mode);
    },

    drawVisualizer() {
        const canvas = document.getElementById('visualizer');
        if (!canvas || !this.analyser) return;

        const ctx = canvas.getContext('2d');

        const draw = () => {
            if (!this.analyser) return;
            this.animationId = requestAnimationFrame(draw);

            if (canvas.width !== canvas.offsetWidth) canvas.width = canvas.offsetWidth;
            if (canvas.height !== canvas.offsetHeight) canvas.height = canvas.offsetHeight;

            const WIDTH = canvas.width;
            const HEIGHT = canvas.height;
            const bufferLength = this.analyser.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLength);

            ctx.clearRect(0, 0, WIDTH, HEIGHT);

            if (this.visualizerMode === 'wave') {
                // Select Source: Prioritize TTS if talking, else Mic
                const activeAnalyser = (this.isAgentSpeaking && this.outputAnalyser) ? this.outputAnalyser : this.analyser;
                if (activeAnalyser) activeAnalyser.getByteTimeDomainData(dataArray);

                ctx.lineWidth = 2;
                ctx.strokeStyle = this.isAgentSpeaking ? '#3b82f6' : '#34d399'; // Blue for Agent, Green for User
                ctx.beginPath();
                const sliceWidth = WIDTH * 1.0 / bufferLength;
                let x = 0;
                for (let i = 0; i < bufferLength; i++) {
                    const v = dataArray[i] / 128.0;
                    const y = v * HEIGHT / 2;
                    if (i === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);
                    x += sliceWidth;
                }
                ctx.lineTo(WIDTH, HEIGHT / 2);
                ctx.stroke();
            } else if (this.visualizerMode === 'bars') {
                const activeAnalyser = (this.isAgentSpeaking && this.outputAnalyser) ? this.outputAnalyser : this.analyser;
                if (activeAnalyser) activeAnalyser.getByteFrequencyData(dataArray);

                // Change color 
                const hue = this.isAgentSpeaking ? 210 : 150; // Blue vs Green

                const barWidth = (WIDTH / bufferLength) * 2.5;
                let barHeight;
                let x = 0;
                for (let i = 0; i < bufferLength; i++) {
                    barHeight = dataArray[i] / 2;
                    ctx.fillStyle = `hsl(${hue}, 100%, 50%)`;
                    // ... existing loop continues
                    const r = barHeight + 25 * (i / bufferLength);
                    const g = 250 * (i / bufferLength);
                    const b = 50;
                    ctx.fillStyle = `rgb(${r},${g},${b})`;
                    ctx.fillRect(x, HEIGHT - barHeight, barWidth, barHeight);
                    x += barWidth + 1;
                }
            } else {
                this.analyser.getByteFrequencyData(dataArray);
                let sum = 0;
                for (let i = 0; i < bufferLength; i++) sum += dataArray[i];
                let avg = sum / bufferLength;
                const centerX = WIDTH / 2;
                const centerY = HEIGHT / 2;
                const radius = 50 + avg;
                const gradient = ctx.createRadialGradient(centerX, centerY, radius * 0.2, centerX, centerY, radius);
                gradient.addColorStop(0, "rgba(52, 211, 153, 0.8)");
                gradient.addColorStop(1, "rgba(5, 150, 105, 0)");
                ctx.beginPath();
                ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
                ctx.fillStyle = gradient;
                ctx.fill();
            }
        };
        draw();
    }
};
