import { motion } from "framer-motion";

interface FlowHeaderProps {
  date: string;
  greeting?: string;
  weather?: "sunny" | "cloudy" | "rainy" | "partly-cloudy";
}

export function FlowHeader({
  date,
  greeting = "Good morning",
  weather = "sunny",
}: FlowHeaderProps) {
  const weatherIcons = {
    sunny: "☀️",
    cloudy: "☁️",
    rainy: "🌧️",
    "partly-cloudy": "⛅",
  };

  return (
    <motion.header
      className="relative px-5 pt-12 pb-6"
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
    >
      {/* Background gradient overlay */}
      <div
        className="absolute inset-0 -z-10"
        style={{
          background:
            "linear-gradient(180deg, rgba(92, 124, 102, 0.15) 0%, transparent 100%)",
        }}
      />

      <div className="flex items-start justify-between">
        <div className="flex flex-col gap-1">
          <motion.p
            className="text-river text-sm font-medium"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            {greeting}
          </motion.p>
          <motion.h1
            className="text-display text-3xl italic text-charcoal"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
          >
            {date}
          </motion.h1>
        </div>

        <motion.div
          className="text-3xl"
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.4, type: "spring" }}
        >
          {weatherIcons[weather]}
        </motion.div>
      </div>
    </motion.header>
  );
}
