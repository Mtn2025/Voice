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
    nextStartTime: 0,
    bgAudio: null,

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

            // Deprecated ScriptProcessor (standard Worklet replacement takes more boilerplate, sticking to this for migration parity)
            this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);
            source.connect(this.processor);

            // Mute output to avoid feedback loop
            const muteGain = this.audioContext.createGain();
            muteGain.gain.value = 0;
            this.processor.connect(muteGain);
            muteGain.connect(this.audioContext.destination);

            this.processor.onaudioprocess = (e) => {
                if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

                const inputData = e.inputBuffer.getChannelData(0);

                // Downsample/Convert Float32 to Int16
                const pcm16 = new Int16Array(inputData.length);
                for (let i = 0; i < inputData.length; i++) {
                    let s = Math.max(-1, Math.min(1, inputData[i]));
                    pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                }

                // Convert to Base64
                // Note: Performance heavy, but functional for this scale
                const bytes = new Uint8Array(pcm16.buffer);
                let binary = '';
                const len = bytes.byteLength;
                for (let i = 0; i < len; i++) {
                    binary += String.fromCharCode(bytes[i]);
                }
                const base64Audio = window.btoa(binary);

                this.ws.send(JSON.stringify({ event: 'media', media: { payload: base64Audio, track: 'inbound' } }));
            };
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

            const source = this.audioContext.createBufferSource();
            source.buffer = buffer;
            source.connect(this.audioContext.destination);

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
                this.analyser.getByteTimeDomainData(dataArray);
                ctx.lineWidth = 2;
                ctx.strokeStyle = '#34d399';
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
                this.analyser.getByteFrequencyData(dataArray);
                const barWidth = (WIDTH / bufferLength) * 2.5;
                let barHeight;
                let x = 0;
                for (let i = 0; i < bufferLength; i++) {
                    barHeight = dataArray[i] / 2;
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
