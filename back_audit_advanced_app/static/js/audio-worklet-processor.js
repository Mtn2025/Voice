class PCMProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this.bufferSize = 4096;
        this.buffer = new Int16Array(this.bufferSize);
        this.index = 0;
    }

    process(inputs, outputs, parameters) {
        const input = inputs[0];
        if (!input || !input.length) return true;

        const channelData = input[0];

        // Loop through the input data (usually 128 samples)
        for (let i = 0; i < channelData.length; i++) {
            // Float32 to Int16 conversion
            let s = Math.max(-1, Math.min(1, channelData[i]));
            // s < 0 ? s * 0x8000 : s * 0x7FFF
            this.buffer[this.index++] = s < 0 ? s * 0x8000 : s * 0x7FFF;

            // If buffer full, flush to main thread
            if (this.index >= this.bufferSize) {
                this.port.postMessage(this.buffer);
                this.index = 0;
            }
        }

        return true;
    }
}

registerProcessor('pcm-processor', PCMProcessor);
