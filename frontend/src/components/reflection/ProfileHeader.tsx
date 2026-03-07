import { motion } from "framer-motion";
import { SlidersHorizontal } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { cn } from "~/utils/cn";

interface ProfileHeaderProps {
  name: string;
  avatarUrl?: string;
  className?: string;
}

export function ProfileHeader({ name, avatarUrl, className }: ProfileHeaderProps) {
  return (
    <motion.div
      className={cn("flex items-center gap-3 px-5 pt-8 pb-4", className)}
      initial={{ opacity: 0, y: -16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      {/* Avatar */}
      <div
        className="w-12 h-12 shrink-0 overflow-hidden"
        style={{
          borderRadius: "30% 70% 70% 30% / 30% 30% 70% 70%",
          background: avatarUrl
            ? undefined
            : "linear-gradient(135deg, #5C7C66 0%, #C27D66 100%)",
        }}
      >
        {avatarUrl ? (
          <img src={avatarUrl} alt={name} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-white text-lg font-bold">
            {name.charAt(0).toUpperCase()}
          </div>
        )}
      </div>

      {/* Name */}
      <div className="flex-1 min-w-0">
        <h1 className="text-display text-xl italic text-charcoal truncate">{name}</h1>
      </div>

      {/* Preferences shortcut */}
      <Link
        to="/profile"
        className="shrink-0 w-10 h-10 glass-card rounded-2xl flex items-center justify-center hover:bg-white/30 active:scale-95 transition-all duration-200"
      >
        <SlidersHorizontal className="w-4 h-4 text-river" />
      </Link>
    </motion.div>
  );
}
