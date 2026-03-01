/**
 * Flux Conv Agent -- Audio Engine
 *
 * Manages microphone capture and TTS playback using the Web Audio API.
 * Uses ScriptProcessorNode for capture (better mobile support than AudioWorklet).
 *
 * Audio format: linear16 PCM, 16kHz, mono. No WAV headers.
 */

/** Callback for outgoing PCM audio from the microphone. */
type OnAudioCapture = (pcmBuffer: ArrayBuffer) => void;

const TARGET_SAMPLE_RATE = 16000;
const BUFFER_SIZE = 4096;

export class AudioEngine {
  private audioCtx: AudioContext | null = null;
  private micStream: MediaStream | null = null;
  private sourceNode: MediaStreamAudioSourceNode | null = null;
  private processorNode: ScriptProcessorNode | null = null;
  private onCapture: OnAudioCapture | null = null;

  // Playback state
  private playbackQueue: Float32Array[] = [];
  private isPlaying = false;

  /**
   * Start capturing microphone audio.
   *
   * Requests mic permission, creates an AudioContext at 16kHz (or
   * resamples from the native rate), and begins sending PCM buffers
   * via the onCapture callback.
   */
  async startCapture(onCapture: OnAudioCapture): Promise<void> {
    this.onCapture = onCapture;

    // Request microphone access
    this.micStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: TARGET_SAMPLE_RATE,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });

    // Create audio context
    this.audioCtx = new AudioContext({ sampleRate: TARGET_SAMPLE_RATE });

    // If the browser ignores our requested sample rate, we resample below
    this.sourceNode = this.audioCtx.createMediaStreamSource(this.micStream);

    // ScriptProcessorNode for capture (deprecated but reliable on mobile)
    this.processorNode = this.audioCtx.createScriptProcessor(
      BUFFER_SIZE,
      1, // input channels
      1, // output channels
    );

    this.processorNode.onaudioprocess = (event: AudioProcessingEvent) => {
      const inputData = event.inputBuffer.getChannelData(0);

      // Resample if the AudioContext rate differs from target
      const sampleRate = this.audioCtx?.sampleRate ?? TARGET_SAMPLE_RATE;
      const resampled =
        sampleRate !== TARGET_SAMPLE_RATE
          ? this._resample(inputData, sampleRate)
          : inputData;

      // Convert Float32 [-1, 1] to Int16 for Deepgram
      const int16 = float32ToInt16(resampled);
      this.onCapture?.(int16.buffer as ArrayBuffer);
    };

    // Connect the pipeline: mic -> processor -> destination (required for node to work)
    this.sourceNode.connect(this.processorNode);
    this.processorNode.connect(this.audioCtx.destination);
  }

  /** Stop microphone capture and release resources. */
  stopCapture(): void {
    this.processorNode?.disconnect();
    this.sourceNode?.disconnect();
    // biome-ignore lint/suspicious/useIterableCallbackReturn: forEach pattern intentional
    this.micStream?.getTracks().forEach((t) => t.stop());

    this.processorNode = null;
    this.sourceNode = null;
    this.micStream = null;
    this.onCapture = null;
  }

  /**
   * Enqueue TTS audio for playback.
   *
   * Accepts raw linear16 PCM data from Deepgram (Int16, 16kHz, mono).
   * Converts to Float32 and schedules playback through the AudioContext.
   */
  playAudio(pcmData: ArrayBuffer): void {
    if (!this.audioCtx) return;

    const int16 = new Int16Array(pcmData);
    const float32 = int16ToFloat32(int16);
    this.playbackQueue.push(float32);

    if (!this.isPlaying) {
      this._playNext();
    }
  }

  /** Stop all queued and current TTS playback (e.g. on user interruption). */
  stopPlayback(): void {
    this.playbackQueue = [];
    this.isPlaying = false;
  }

  /** Fully tear down the audio engine (capture + playback). */
  destroy(): void {
    this.stopCapture();
    this.stopPlayback();
    if (this.audioCtx && this.audioCtx.state !== "closed") {
      this.audioCtx.close();
    }
    this.audioCtx = null;
  }

  // -- Private Methods ------------------------------------------------------

  /** Play the next chunk from the playback queue. */
  private _playNext(): void {
    if (!this.audioCtx || this.playbackQueue.length === 0) {
      this.isPlaying = false;
      return;
    }

    this.isPlaying = true;
    // biome-ignore lint/style/noNonNullAssertion: audio context guaranteed initialized
    const samples = this.playbackQueue.shift()!;

    // Create a buffer and fill it with the Float32 samples
    const buffer = this.audioCtx.createBuffer(
      1,
      samples.length,
      TARGET_SAMPLE_RATE,
    );
    buffer.getChannelData(0).set(samples);

    const source = this.audioCtx.createBufferSource();
    source.buffer = buffer;
    source.connect(this.audioCtx.destination);

    source.onended = () => {
      this._playNext();
    };

    source.start();
  }

  /**
   * Simple linear resampling from sourceRate to TARGET_SAMPLE_RATE.
   * Good enough for voice -- no anti-aliasing filter needed.
   */
  private _resample(input: Float32Array, sourceRate: number): Float32Array {
    const ratio = sourceRate / TARGET_SAMPLE_RATE;
    const outputLength = Math.round(input.length / ratio);
    const output = new Float32Array(outputLength);

    for (let i = 0; i < outputLength; i++) {
      const srcIndex = i * ratio;
      const low = Math.floor(srcIndex);
      const high = Math.min(low + 1, input.length - 1);
      const frac = srcIndex - low;
      output[i] = input[low] * (1 - frac) + input[high] * frac;
    }

    return output;
  }
}

// -- PCM Conversion Utilities -----------------------------------------------

/** Convert Float32 [-1, 1] audio samples to Int16 for Deepgram. */
function float32ToInt16(float32: Float32Array): Int16Array {
  const int16 = new Int16Array(float32.length);
  for (let i = 0; i < float32.length; i++) {
    const s = Math.max(-1, Math.min(1, float32[i]));
    int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return int16;
}

/** Convert Int16 PCM audio samples to Float32 for Web Audio playback. */
function int16ToFloat32(int16: Int16Array): Float32Array {
  const float32 = new Float32Array(int16.length);
  for (let i = 0; i < int16.length; i++) {
    float32[i] = int16[i] / 32768;
  }
  return float32;
}
