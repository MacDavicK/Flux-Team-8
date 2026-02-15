import { motion } from "framer-motion";
import { cn } from "~/utils/cn";

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  variant?: "default" | "bubble" | "pebble";
  animate?: boolean;
  onClick?: () => void;
}

export function GlassCard({
  children,
  className,
  variant = "default",
  animate = false,
  onClick,
}: GlassCardProps) {
  const variantStyles = {
    default: "glass-card",
    bubble: "glass-bubble",
    pebble: "event-pebble",
  };

  const Component = animate ? motion.div : "div";

  return (
    <Component
      onClick={onClick}
      className={cn(variantStyles[variant], className)}
      {...(animate && {
        initial: { opacity: 0, y: 20 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: 0.4, ease: [0.34, 1.56, 0.64, 1] },
      })}
    >
      {children}
    </Component>
  );
}
