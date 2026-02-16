import { motion } from "framer-motion";
import { useEffect, useRef } from "react";
import type { EnergyPoint } from "~/types/analytics";

interface EnergyAuraProps {
  data: EnergyPoint[];
  className?: string;
}

export function EnergyAura({ data, className }: EnergyAuraProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Set canvas size
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    // Clear canvas
    ctx.clearRect(0, 0, rect.width, rect.height);

    // Draw energy orbs
    const orbSize = 20;
    const spacing = 35;
    const cols = Math.floor(rect.width / spacing);
    const rows = Math.floor(rect.height / spacing);

    for (let row = 0; row < rows; row++) {
      for (let col = 0; col < cols; col++) {
        const x = col * spacing + spacing / 2;
        const y = row * spacing + spacing / 2;

        // Get intensity for this position
        const dataIndex = (row * cols + col) % data.length;
        const intensity = data[dataIndex]?.intensity || 0.5;

        // Create gradient
        const gradient = ctx.createRadialGradient(x, y, 0, x, y, orbSize);
        const alpha = 0.3 + intensity * 0.5;

        // Color based on intensity (cool to warm)
        if (intensity < 0.3) {
          gradient.addColorStop(0, `rgba(138, 143, 139, ${alpha})`);
          gradient.addColorStop(1, "rgba(138, 143, 139, 0)");
        } else if (intensity < 0.7) {
          gradient.addColorStop(0, `rgba(92, 124, 102, ${alpha})`);
          gradient.addColorStop(1, "rgba(92, 124, 102, 0)");
        } else {
          gradient.addColorStop(0, `rgba(194, 125, 102, ${alpha})`);
          gradient.addColorStop(1, "rgba(194, 125, 102, 0)");
        }

        ctx.beginPath();
        ctx.arc(x, y, orbSize * (0.5 + intensity * 0.5), 0, Math.PI * 2);
        ctx.fillStyle = gradient;
        ctx.fill();
      }
    }
  }, [data]);

  return (
    <motion.div
      className={className}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      <h3 className="text-river text-xs font-semibold uppercase tracking-wider mb-3">
        Energy Aura
      </h3>
      <div className="glass-card p-4 overflow-hidden">
        <canvas
          ref={canvasRef}
          className="w-full h-32 cursor-crosshair"
          style={{ touchAction: "none" }}
        />
      </div>
    </motion.div>
  );
}

export type { EnergyPoint };
export { EnergyLevel } from "~/types/analytics";
