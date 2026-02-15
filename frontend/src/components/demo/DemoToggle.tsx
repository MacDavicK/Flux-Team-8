import { motion } from "framer-motion";
import { Settings2 } from "lucide-react";
import { cn } from "~/utils/cn";

interface DemoToggleProps {
  onClick: () => void;
  isOpen: boolean;
}

export function DemoToggle({ onClick, isOpen }: DemoToggleProps) {
  return (
    <motion.button
      onClick={onClick}
      className={cn(
        "fixed right-0 top-1/2 -translate-y-1/2 z-40",
        "glass-bubble p-3 rounded-l-bubble rounded-r-none",
        "flex items-center justify-center",
        "active:scale-95 transition-transform",
        "touch-manipulation",
      )}
      whileTap={{ scale: 0.95 }}
      animate={{ x: isOpen ? -140 : 0 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
    >
      <Settings2
        className={cn(
          "w-5 h-5 text-charcoal transition-transform duration-300",
          isOpen && "rotate-180",
        )}
      />
    </motion.button>
  );
}
