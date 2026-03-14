/**
 * VoiceWaveform — real-time mic amplitude visualizer
 *
 * Reads frequency data from an AnalyserNode driven by the active MediaStream
 * and animates 5 bars with Framer Motion. Falls back to a static pulse if
 * Web Audio API is unavailable.
 */

import { motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";

interface VoiceWaveformProps {
  stream: MediaStream | null;
}

const NUM_BARS = 5;
// Which frequency bins to sample (0–255 range, 256 total bins)
const BIN_INDICES = [8, 24, 48, 24, 8];

export function VoiceWaveform({ stream }: VoiceWaveformProps) {
  const [heights, setHeights] = useState<number[]>(Array(NUM_BARS).fill(0.15));
  const animFrameRef = useRef<number | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const ctxRef = useRef<AudioContext | null>(null);

  useEffect(() => {
    if (!stream) return;

    let ctx: AudioContext;
    try {
      ctx = new AudioContext();
      ctxRef.current = ctx;
    } catch {
      // Web Audio API unavailable — static pulse fallback handled by initial state
      return;
    }

    const source = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 512;
    analyser.smoothingTimeConstant = 0.6;
    source.connect(analyser);
    analyserRef.current = analyser;

    const dataArray = new Uint8Array(analyser.frequencyBinCount);

    const tick = () => {
      analyser.getByteFrequencyData(dataArray);

      const newHeights = BIN_INDICES.map((bin) => {
        const raw = dataArray[bin] ?? 0;
        // Normalize 0–255 to 0.1–1.0, with a floor so bars are always visible
        return Math.max(0.1, raw / 255);
      });

      setHeights(newHeights);
      animFrameRef.current = requestAnimationFrame(tick);
    };

    animFrameRef.current = requestAnimationFrame(tick);

    return () => {
      if (animFrameRef.current !== null) {
        cancelAnimationFrame(animFrameRef.current);
      }
      source.disconnect();
      ctx.close().catch(() => {});
    };
  }, [stream]);

  return (
    <output
      className="flex items-center gap-1 h-6"
      aria-label="Listening"
      aria-live="polite"
    >
      {heights.map((h, i) => (
        <motion.div
          // biome-ignore lint/suspicious/noArrayIndexKey: bar order is stable; no reorder occurs
          key={i}
          className="w-1 rounded-full bg-red-400 origin-center"
          animate={{ scaleY: h }}
          transition={{ duration: 0.05, ease: "linear" }}
          style={{ height: "100%" }}
        />
      ))}
    </output>
  );
}
