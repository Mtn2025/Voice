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

        // Pre-init Audio Context user interaction check
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        this.audioContext = new AudioContext({ sampleRate: 16000 });

        this.simState = 'connecting';

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/media-stream?client=browser`;

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = async () => {
                console.log("WS Connected");
                this.simState = 'connected';

                // CRITICAL FIX: Await Audio Engine (Worklet) BEFORE telling backend to start.
                // This prevents the "Greeting" from arriving before we are ready to play it.
                await this.initMicrophone();

                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(JSON.stringify({
                        event: 'start',
                        start: {
                            streamSid: 'browser-' + Date.now(),
                            callSid: 'sim-' + Date.now(),
                            media_format: { encoding: 'audio/pcm', sample_rate: 16000, channels: 1 }
                        }
                    }));
                }
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
                        if (this.debugLogs.length > 50) this.debugLogs.pop();

                        // Handle Metrics & Speaking State from Server
                        if (msg.event === 'speech_state') {
                            this.isAgentSpeaking = msg.data.speaking;
                        } else if (msg.event === 'vad_level') {
                            this.vadLevel = msg.data.rms;
                        } else if (msg.event === 'llm_latency') {
                            this.metrics.llm_latency = msg.data.duration_ms + ' ms';
                        } else if (msg.event === 'tts_latency') {
                            this.metrics.tts_latency = msg.data.duration_ms + ' ms';
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
                    } else if (msg.event === 'clear') {
                        // Clear buffers command?
                        // If we had a 'clear' message handling in Worklet, we would send it here.
                        // For now ignores.
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

            // Connect Analyser if missing (Input Analysis)
            if (!this.analyser) {
                this.analyser = this.audioContext.createAnalyser();
                this.analyser.fftSize = 256;
            }

            // Output Analyser (Assistant)
            if (!this.outputAnalyser) {
                this.outputAnalyser = this.audioContext.createAnalyser();
                this.outputAnalyser.fftSize = 256;
                this.outputAnalyser.connect(this.audioContext.destination);
            }

            const constraints = {
                audio: {
                    echoCancellation: this.c && this.c.denoise,
                    noiseSuppression: this.c && this.c.denoise,
                    autoGainControl: true
                }
            };

            this.mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
            const source = this.audioContext.createMediaStreamSource(this.mediaStream);

            // Connect Mic -> Analyser (Visualizer)
            source.connect(this.analyser);

            // Load Worklet
            try {
                await this.audioContext.audioWorklet.addModule('/static/js/audio-worklet-processor.js');

                // Create Worklet Node
                this.processor = new AudioWorkletNode(this.audioContext, 'pcm-processor');

                // Handle Messages from Worklet (Mic Data)
                this.processor.port.onmessage = (event) => {
                    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

                    const pcm16 = event.data; // Int16Array

                    // Convert to Base64 (Main Thread)
                    const bytes = new Uint8Array(pcm16.buffer);
                    let binary = '';
                    const len = bytes.byteLength;
                    // Chunked optimization for large strings
                    const CHUNK_SIZE = 8192;
                    for (let i = 0; i < len; i += CHUNK_SIZE) {
                        binary += String.fromCharCode.apply(null, bytes.subarray(i, i + CHUNK_SIZE));
                    }
                    const base64Audio = window.btoa(binary);

                    this.ws.send(JSON.stringify({ event: 'media', media: { payload: base64Audio, track: 'inbound' } }));
                };

                // AUDIO GRAPH:
                // Mic Source -> Analyser -> Worklet (Input 0)
                source.connect(this.processor);

                // Worklet (Output 0) -> Output Analyser -> Destination
                this.processor.connect(this.outputAnalyser);

                console.log("✅ AudioWorklet 'pcm-processor' active (Ring Buffer Implemented)");

            } catch (err) {
                console.error("❌ AudioWorklet Failed to Load:", err);
                alert("Audio Worklet Error: " + err.message + ". Update your browser.");
                this.stopTest();
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
            this.processor.port.onmessage = null;
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

        // Fix: Clear Analysers to prevent "Different AudioContext" error on restart
        this.analyser = null;
        this.outputAnalyser = null;

        if (this.animationId) cancelAnimationFrame(this.animationId);
        if (this.speakingTimer) clearTimeout(this.speakingTimer);

        const canvas = document.getElementById('visualizer');
        if (canvas) {
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
    },

    playAudio(base64Data) {
        if (!base64Data || !this.processor) return;
        try {
            // Decode Base64 -> String -> Uint8Array -> Int16Array
            const binaryString = window.atob(base64Data);
            const len = binaryString.length;
            const bytes = new Uint8Array(len);
            for (let i = 0; i < len; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }
            const pcm16 = new Int16Array(bytes.buffer);

            // Feed to Worklet (Ring Buffer)
            this.processor.port.postMessage(pcm16);

            // Visualizer State (Optimistic)
            this.isAgentSpeaking = true;
            if (this.speakingTimer) clearTimeout(this.speakingTimer);
            this.speakingTimer = setTimeout(() => {
                this.isAgentSpeaking = false;
            }, 300); // Debounce duration (since we are streaming chunks)

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
