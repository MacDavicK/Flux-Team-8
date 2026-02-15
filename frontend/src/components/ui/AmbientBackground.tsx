import { cn } from "~/utils/cn";

interface AmbientBackgroundProps {
  className?: string;
  variant?: "light" | "dark";
}

export function AmbientBackground({
  className,
  variant = "light",
}: AmbientBackgroundProps) {
  return (
    <div
      className={cn(
        "fixed inset-0 -z-10 overflow-hidden",
        variant === "dark" ? "bg-sage-dark" : "bg-stone",
        className,
      )}
      style={{
        background:
          variant === "dark"
            ? "linear-gradient(135deg, #4A6352 0%, #3A5242 100%)"
            : "var(--gradient-base)",
      }}
    >
      {/* Organic blob 1 */}
      <div
        className="absolute animate-blob opacity-30"
        style={{
          width: "400px",
          height: "400px",
          background:
            "radial-gradient(circle, rgba(92, 124, 102, 0.4) 0%, transparent 70%)",
          top: "-100px",
          right: "-100px",
          filter: "blur(40px)",
        }}
      />

      {/* Organic blob 2 */}
      <div
        className="absolute animate-blob opacity-20"
        style={{
          width: "300px",
          height: "300px",
          background:
            "radial-gradient(circle, rgba(194, 125, 102, 0.3) 0%, transparent 70%)",
          bottom: "20%",
          left: "-50px",
          filter: "blur(50px)",
          animationDelay: "-2s",
        }}
      />

      {/* Organic blob 3 */}
      <div
        className="absolute animate-blob opacity-25"
        style={{
          width: "250px",
          height: "250px",
          background:
            "radial-gradient(circle, rgba(92, 124, 102, 0.35) 0%, transparent 70%)",
          top: "40%",
          right: "10%",
          filter: "blur(35px)",
          animationDelay: "-4s",
        }}
      />
    </div>
  );
}
