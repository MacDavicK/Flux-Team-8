import { AnimatePresence, motion } from "framer-motion";
import { Calendar, Clock, Coffee, Sun, X } from "lucide-react";
import { useState } from "react";
import type { RescheduleOption } from "~/types/demo";
import { cn } from "~/utils/cn";

const rescheduleOptions: RescheduleOption[] = [
  { id: "later-today", label: "Later Today", icon: Clock, color: "sage" },
  { id: "tomorrow", label: "Tomorrow Morning", icon: Sun, color: "terracotta" },
  { id: "weekend", label: "This Weekend", icon: Coffee, color: "river" },
  { id: "custom", label: "Pick Date", icon: Calendar, color: "charcoal" },
];

interface RescheduleModalProps {
  isOpen: boolean;
  onClose: () => void;
  taskTitle: string;
  onReschedule: (option: string) => void;
}

export function RescheduleModal({
  isOpen,
  onClose,
  taskTitle,
  onReschedule,
}: RescheduleModalProps) {
  const [draggedOption, setDraggedOption] = useState<string | null>(null);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-charcoal/30 z-50"
            style={{ backdropFilter: "blur(8px)" }}
          />

          {/* Modal */}
          <motion.div
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="fixed bottom-0 left-0 right-0 z-50"
          >
            <div className="glass-card rounded-b-none p-6 pb-safe">
              {/* Close button */}
              <button
                type="button"
                onClick={onClose}
                className="absolute top-4 right-4 p-2 rounded-full hover:bg-charcoal/10 transition-colors"
              >
                <X className="w-5 h-5 text-charcoal" />
              </button>

              {/* Task Preview */}
              <motion.div
                className="mb-6"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                <p className="text-river text-sm mb-2">Reschedule</p>
                <div
                  className={cn(
                    "glass-bubble p-4 transform -rotate-1",
                    "border-l-4 border-l-terracotta",
                  )}
                >
                  <p className="text-charcoal font-medium">{taskTitle}</p>
                </div>
              </motion.div>

              {/* Options Grid */}
              <div className="grid grid-cols-2 gap-3">
                {rescheduleOptions.map((option, index) => {
                  const Icon = option.icon;
                  const isActive = draggedOption === option.id;

                  return (
                    <motion.button
                      key={option.id}
                      type="button"
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.2 + index * 0.1 }}
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => onReschedule(option.id)}
                      onMouseEnter={() => setDraggedOption(option.id)}
                      onMouseLeave={() => setDraggedOption(null)}
                      className={cn(
                        "glass-bubble p-4 flex flex-col items-center gap-2",
                        "transition-all duration-200",
                        isActive && "scale-105 shadow-lg",
                      )}
                      style={{
                        background: isActive
                          ? `linear-gradient(135deg, rgba(255,255,255,0.6) 0%, rgba(255,255,255,0.3) 100%)`
                          : undefined,
                      }}
                    >
                      <Icon
                        className={cn(
                          "w-6 h-6",
                          option.color === "sage" && "text-sage",
                          option.color === "terracotta" && "text-terracotta",
                          option.color === "river" && "text-river",
                          option.color === "charcoal" && "text-charcoal",
                        )}
                      />
                      <span className="text-charcoal text-sm font-medium text-center">
                        {option.label}
                      </span>
                    </motion.button>
                  );
                })}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

export type { RescheduleOption };
export { rescheduleOptions };
