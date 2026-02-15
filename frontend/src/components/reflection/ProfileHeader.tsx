import { motion } from "framer-motion";
import { cn } from "~/utils/cn";

interface ProfileHeaderProps {
  name: string;
  avatarUrl?: string;
  className?: string;
}

export function ProfileHeader({
  name,
  avatarUrl,
  className,
}: ProfileHeaderProps) {
  return (
    <motion.div
      className={cn("flex flex-col items-center gap-4 py-8", className)}
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      {/* Squircle Avatar */}
      <motion.div
        className="relative w-24 h-24"
        whileHover={{ scale: 1.05 }}
        transition={{ type: "spring", stiffness: 300 }}
      >
        {/* Squircle shape mask */}
        <div
          className="w-full h-full overflow-hidden"
          style={{
            borderRadius: "30% 70% 70% 30% / 30% 30% 70% 70%",
            background: avatarUrl
              ? undefined
              : "linear-gradient(135deg, #5C7C66 0%, #C27D66 100%)",
          }}
        >
          {avatarUrl ? (
            <img
              src={avatarUrl}
              alt={name}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-white text-3xl font-bold">
              {name.charAt(0).toUpperCase()}
            </div>
          )}
        </div>

        {/* Glow effect */}
        <div
          className="absolute inset-0 -z-10 blur-xl opacity-50"
          style={{
            borderRadius: "30% 70% 70% 30% / 30% 30% 70% 70%",
            background: "linear-gradient(135deg, #5C7C66 0%, #C27D66 100%)",
          }}
        />
      </motion.div>

      {/* Name */}
      <motion.h1
        className="text-display text-2xl italic text-charcoal"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
      >
        {name}
      </motion.h1>
    </motion.div>
  );
}
