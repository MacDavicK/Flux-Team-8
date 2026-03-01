/**
 * Flux Conv Agent -- Deepgram WebSocket Client
 *
 * Manages the direct browser-to-Deepgram WebSocket connection.
 * Handles authentication via subprotocol, Settings message,
 * incoming events (text + binary), and outgoing audio.
 *
 * No Deepgram SDK -- raw WebSocket only.
 */

import type {
  DeepgramEvent,
  DeepgramSettingsMessage,
  SessionConfig,
} from "./types";

/** Callback map for Deepgram events. */
export interface DeepgramCallbacks {
  onOpen: () => void;
  onClose: (code: number, reason: string) => void;
  onError: (error: Event) => void;
  onTextEvent: (event: DeepgramEvent) => void;
  onAudioData: (pcmData: ArrayBuffer) => void;
}

const DEEPGRAM_AGENT_URL = "wss://agent.deepgram.com/v1/agent/converse";

export class DeepgramClient {
  private ws: WebSocket | null = null;
  private callbacks: DeepgramCallbacks;
  private settingsSent = false;

  constructor(callbacks: DeepgramCallbacks) {
    this.callbacks = callbacks;
  }

  /**
   * Open a WebSocket connection to Deepgram Voice Agent.
   *
   * Authenticates via the "token" subprotocol with the short-lived JWT.
   * Once connected, sends the Settings message with agent configuration.
   */
  connect(token: string, config: SessionConfig): void {
    if (this.ws) {
      this.disconnect();
    }

    this.settingsSent = false;

    // Authenticate via WebSocket subprotocol.
    // JWT tokens from auth/grant require the "bearer" scheme;
    // the "token" scheme is only for raw API keys.
    this.ws = new WebSocket(DEEPGRAM_AGENT_URL, ["bearer", token]);
    this.ws.binaryType = "arraybuffer";

    this.ws.onopen = () => {
      this.callbacks.onOpen();
      this._sendSettings(config);
    };

    this.ws.onclose = (ev: CloseEvent) => {
      this.callbacks.onClose(ev.code, ev.reason);
      this.ws = null;
    };

    this.ws.onerror = (ev: Event) => {
      this.callbacks.onError(ev);
    };

    this.ws.onmessage = (ev: MessageEvent) => {
      if (ev.data instanceof ArrayBuffer) {
        // Binary frame -- TTS audio from the agent
        this.callbacks.onAudioData(ev.data);
      } else {
        // Text frame -- JSON event
        this._handleTextMessage(ev.data as string);
      }
    };
  }

  /** Close the WebSocket connection gracefully. */
  disconnect(): void {
    if (this.ws) {
      this.ws.close(1000, "Client disconnecting");
      this.ws = null;
    }
    this.settingsSent = false;
  }

  /**
   * Send raw PCM audio data to Deepgram.
   * The data should be linear16, 16kHz, mono (Int16Array buffer).
   */
  sendAudio(pcmBuffer: ArrayBuffer): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN && this.settingsSent) {
      this.ws.send(pcmBuffer);
    }
  }

  /**
   * Send a FunctionCallResponse back to Deepgram after processing
   * a function call on the backend.
   *
   * V1 format requires id, name, and content (not output).
   */
  sendFunctionResult(functionCallId: string, functionName: string, result: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          type: "FunctionCallResponse",
          id: functionCallId,
          name: functionName,
          content: result,
        }),
      );
    }
  }

  /** Whether the WebSocket is currently open. */
  get isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  // -- Private Methods ------------------------------------------------------

  /**
   * Build and send the Settings message that configures the
   * Deepgram voice agent (STT, LLM, TTS, functions, greeting).
   */
  private _sendSettings(config: SessionConfig): void {
    const settings: DeepgramSettingsMessage = {
      type: "Settings",
      audio: {
        input: { encoding: "linear16", sample_rate: 16000 },
        output: { encoding: "linear16", sample_rate: 16000, container: "none" },
      },
      agent: {
        language: "en",
        listen: {
          provider: { type: "deepgram", model: config.listen_model },
        },
        think: {
          provider: { type: "open_ai", model: config.llm_model },
          prompt: config.system_prompt,
          functions: config.functions,
        },
        speak: {
          provider: { type: "deepgram", model: config.voice_model },
        },
        greeting: config.greeting,
      },
    };

    this.ws?.send(JSON.stringify(settings));
    this.settingsSent = true;
  }

  /** Parse and dispatch an incoming text-frame event. */
  private _handleTextMessage(raw: string): void {
    try {
      const event = JSON.parse(raw) as DeepgramEvent;
      this.callbacks.onTextEvent(event);
    } catch (err) {
      console.warn("Failed to parse Deepgram event:", raw, err);
    }
  }
}
