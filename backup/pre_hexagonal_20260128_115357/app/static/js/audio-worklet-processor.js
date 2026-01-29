class PCMProcessor extends AudioWorkletProcessor {
    constructor() {
        super();

        // --- 1. Ring Buffer for Output (TTS) ---
        // Tuned to 10 seconds (16kHz) to handle "Burst Mode" from backend without wrapping.
        this.bufferSize = 160000;
        this.outBuffer = new Float32Array(this.bufferSize);
        this.writePtr = 0;
        this.readPtr = 0;
        this.available = 0;

        // --- 2. Input Buffer for Mic (Capture) ---
        this.inBufferSize = 4096;
        this.inBuffer = new Int16Array(this.inBufferSize);
        this.inPtr = 0;

        // Messaging Handlers
        this.port.onmessage = (e) => {
            const data = e.data;
            // Handle raw Int16Array as TTS Data (Legacy/Simple) or Object?
            // Let's support both or just raw array for speed.
            // If it's a typed array, treat as TTS feed.
            if (data && data.length && (data instanceof Int16Array || data instanceof ArrayBuffer)) {
                this.writeOutput(new Int16Array(data.buffer || data));
            } else if (data && data.type === 'feed') {
                this.writeOutput(data.buffer);
            }
        };
    }

    writeOutput(int16Data) {
        // Write incoming TTS Int16 chunks to Ring Buffer (Float32)
        for (let i = 0; i < int16Data.length; i++) {
            const s = int16Data[i];
            const floatSample = s < 0 ? s / 32768 : s / 32767;

            this.outBuffer[this.writePtr] = floatSample;
            this.writePtr = (this.writePtr + 1) % this.bufferSize;
            this.available = Math.min(this.available + 1, this.bufferSize);
        }
    }

    process(inputs, outputs, parameters) {
        // --- 1. CAPTURE (Mic Input) ---
        // Input[0] is the Mic stream
        const input = inputs[0];
        if (input && input.length) {
            const channelData = input[0];
            for (let i = 0; i < channelData.length; i++) {
                // Float32 -> Int16
                let s = Math.max(-1, Math.min(1, channelData[i]));
                s = s < 0 ? s * 0x8000 : s * 0x7FFF;

                this.inBuffer[this.inPtr++] = s;

                // Flush Input Buffer
                if (this.inPtr >= this.inBufferSize) {
                    this.port.postMessage(this.inBuffer); // Post Int16Array
                    this.inPtr = 0;
                }
            }
        }

        // --- 2. RENDER (TTS Output) ---
        // Output[0] is the Speaker
        const output = outputs[0];
        if (output && output.length) {
            const channel = output[0];
            for (let i = 0; i < channel.length; i++) {
                if (this.available > 0) {
                    channel[i] = this.outBuffer[this.readPtr];
                    this.readPtr = (this.readPtr + 1) % this.bufferSize;
                    this.available--;
                } else {
                    channel[i] = 0; // Silence
                }
            }
        }

        return true; // Keep processor alive
    }
}

registerProcessor('pcm-processor', PCMProcessor);
