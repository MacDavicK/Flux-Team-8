import { motion } from "framer-motion";
import { cn } from "~/utils/cn";

interface ChatBubbleProps {
  children: React.ReactNode;
  variant: "user" | "ai";
  className?: string;
  animate?: boolean;
}

export function ChatBubble({
  children,
  variant,
  className,
  animate = true,
}: ChatBubbleProps) {
  const isUser = variant === "user";

  return (
    <motion.div
      className={cn(
        "max-w-[80%] px-4 py-3",
        isUser
          ? "ml-auto rounded-[24px_24px_4px_24px] bg-terracotta text-white"
          : "mr-auto rounded-[4px_24px_24px_24px] bg-white/90 text-charcoal",
        "shadow-md",
        className,
      )}
      initial={animate ? { opacity: 0, y: 20, scale: 0.95 } : false}
      animate={animate ? { opacity: 1, y: 0, scale: 1 } : false}
      transition={{
        duration: 0.4,
        ease: [0.34, 1.56, 0.64, 1],
      }}
    >
      <div className="text-body text-[15px] leading-relaxed">{children}</div>
    </motion.div>
  );
}
