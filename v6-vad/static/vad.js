"use strict";

const button = document.getElementById("listen");
const status = document.getElementById("status");
let stream;
let audioContext;
let processor;
let silence;
let chunks = [];

function stopAudio() {
    if (processor) {
        processor.disconnect();
        processor.onaudioprocess = null;
        processor = null;
    }
    if (silence) {
        silence.disconnect();
        silence = null;
    }
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
    }
    if (audioContext) {
        audioContext.close();
        audioContext = null;
    }
}

async function startListening() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: 1,
                echoCancellation: false,
                noiseSuppression: false,
                autoGainControl: false,
            },
        });
        audioContext = new AudioContext({sampleRate: 16000});
        if (audioContext.sampleRate !== 16000) {
            throw new Error(
                "This browser cannot capture audio at 16 kHz.",
            );
        }
        await audioContext.resume();

        const source = audioContext.createMediaStreamSource(stream);
        processor = audioContext.createScriptProcessor(4096, 1, 1);
        silence = audioContext.createGain();
        silence.gain.value = 0;
        chunks = [];
        processor.onaudioprocess = event => {
            const input = event.inputBuffer.getChannelData(0);
            const pcm = new Int16Array(input.length);
            for (let index = 0; index < input.length; index += 1) {
                const sample = Math.max(-1, Math.min(1, input[index]));
                pcm[index] = sample < 0
                    ? sample * 32768
                    : sample * 32767;
            }
            chunks.push(pcm);
        };
        source.connect(processor);
        processor.connect(silence);
        silence.connect(audioContext.destination);
        button.textContent = "Stop and detect";
        status.textContent = "Listening...";
    } catch (error) {
        stopAudio();
        button.textContent = "Listen";
        status.textContent = error.message;
    }
}

async function stopListening() {
    button.disabled = true;
    button.textContent = "Detecting...";
    status.textContent = "Processing captured audio...";
    stopAudio();

    const length = chunks.reduce(
        (total, chunk) => total + chunk.length,
        0,
    );
    const audio = new Int16Array(length);
    let offset = 0;
    for (const chunk of chunks) {
        audio.set(chunk, offset);
        offset += chunk.length;
    }
    chunks = [];
    if (!audio.length) {
        status.textContent = "No audio was captured.";
        button.disabled = false;
        button.textContent = "Listen";
        return;
    }

    try {
        const response = await fetch("/vad", {
            method: "POST",
            headers: {
                "Content-Type": "application/octet-stream",
                "X-Sample-Rate": "16000",
            },
            body: audio.buffer,
        });
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || "VAD request failed.");
        }
        status.textContent = result.segments.length
            ? `Detected ${result.segments.length} speech segment(s).`
            : "No speech detected.";
    } catch (error) {
        status.textContent = error.message;
    } finally {
        button.disabled = false;
        button.textContent = "Listen";
    }
}

button.addEventListener("click", () => {
    if (stream) {
        stopListening();
    } else {
        startListening();
    }
});
