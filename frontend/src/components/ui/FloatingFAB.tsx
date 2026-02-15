import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";
import { cn } from "~/utils/cn";

interface FloatingFABProps {
  onClick?: () => void;
  className?: string;
  icon?: React.ReactNode;
  pulse?: boolean;
}

export function FloatingFAB({
  onClick,
  className,
  icon = <Sparkles className="w-6 h-6 text-white" />,
  pulse = true,
}: FloatingFABProps) {
  return (
    <motion.button
      onClick={onClick}
      className={cn(
        "fixed bottom-24 right-5 w-16 h-16 rounded-full fab-gradient",
        "flex items-center justify-center shadow-lg",
        "active:scale-95 transition-transform duration-200",
        "z-40 touch-manipulation",
        pulse && "animate-pulse-glow",
        className,
      )}
      whileTap={{ scale: 0.95 }}
      whileHover={{ scale: 1.05 }}
      transition={{ type: "spring", stiffness: 400, damping: 17 }}
    >
      {icon}
    </motion.button>
  );
}
