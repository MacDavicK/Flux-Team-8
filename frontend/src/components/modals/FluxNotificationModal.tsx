import { AnimatePresence, motion } from "framer-motion";
import { Clock, AlertCircle, ChevronRight, X, Calendar, Check } from "lucide-react";
import { useState } from "react";
import { cn } from "~/utils/cn";

interface FluxNotificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  eventDetails?: {
    title: string;
    time: string;
    type: "sage" | "terra" | "stone";
  };
}

const mockEvent = {
  title: "Deep Work: Strategy",
  time: "10:00 AM",
  type: "sage" as const,
};

const timeOptions = ["07:30 PM", "08:00 PM", "08:30 PM"];

export function FluxNotificationModal({
  isOpen,
  onClose,
  eventDetails = mockEvent,
}: FluxNotificationModalProps) {
  const [showTimeOptions, setShowTimeOptions] = useState(false);

  const handleReschedule = (time: string) => {
    console.log(`Rescheduled ${eventDetails.title} to ${time}`);
    onClose();
    setShowTimeOptions(false);
  };

  const handleMarkAsMissed = () => {
    console.log(`Marked ${eventDetails.title} as missed`);
    onClose();
  };

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
            className="fixed inset-0 bg-charcoal/20 z-[60]"
            style={{ backdropFilter: "blur(8px)" }}
          />

          {/* Bottom Sheet */}
          <motion.div
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", stiffness: 300, damping: 32 }}
            className="fixed bottom-0 left-0 right-0 z-[70] max-w-md mx-auto"
          >
            <div className="glass-card rounded-b-none p-6 pt-8 pb-safe shadow-2xl border-t border-white/40">
              {/* Handle */}
              <div className="absolute top-3 left-1/2 -translate-x-1/2 w-12 h-1.5 bg-charcoal/10 rounded-full" />

              {/* Close Button */}
              <button
                type="button"
                onClick={onClose}
                className="absolute top-4 right-4 p-2 rounded-full hover:bg-charcoal/5 transition-colors"
              >
                <X className="w-5 h-5 text-charcoal/40" />
              </button>

              <div className="flex flex-col pb-6 gap-6">
                {/* Header */}
                <div className="space-y-1">
                  <div className="flex items-center gap-2 text-terracotta font-medium">
                    <AlertCircle className="w-4 h-4" />
                    <span className="text-sm tracking-wide uppercase font-bold text-[10px]">
                      Missed Event
                    </span>
                  </div>
                  <h2 className="text-display text-2xl text-charcoal leading-tight">
                    You missed your <br />
                    <span className="italic">{eventDetails.title}</span>
                  </h2>
                </div>

                {/* Event Details Card */}
                <div className="glass-bubble p-4 flex items-center justify-between border-l-4 border-l-sage">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-full bg-sage/10 flex items-center justify-center text-sage">
                      <Calendar className="w-6 h-6" />
                    </div>
                    <div>
                      <h3 className="font-bold text-charcoal">
                        {eventDetails.title}
                      </h3>
                      <p className="text-river text-xs font-medium">
                        Today at {eventDetails.time}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="space-y-3">
                  {!showTimeOptions ? (
                    <>
                      <button
                        type="button"
                        onClick={() => {
                          console.log(`Marked ${eventDetails.title} as already done`);
                          onClose();
                        }}
                        className="w-full glass-bubble p-4 flex items-center justify-between group hover:bg-sage/10 transition-all border-none"
                      >
                        <div className="flex items-center gap-3">
                          <div className="p-2 rounded-full bg-sage text-white shadow-sm shadow-sage/20">
                            <Check className="w-4 h-4" />
                          </div>
                          <span className="font-bold text-charcoal">
                            I already did this
                          </span>
                        </div>
                        <ChevronRight className="w-5 h-5 text-charcoal/20 group-hover:translate-x-1 transition-transform" />
                      </button>

                      <button
                        type="button"
                        onClick={() => setShowTimeOptions(true)}
                        className="w-full glass-bubble p-4 flex items-center justify-between group hover:bg-stone/20 transition-all border-none"
                      >
                        <div className="flex items-center gap-3">
                          <div className="p-2 rounded-full bg-river/20 text-river">
                            <Clock className="w-4 h-4" />
                          </div>
                          <span className="font-bold text-charcoal">
                            Move it to another time
                          </span>
                        </div>
                        <ChevronRight className="w-5 h-5 text-charcoal/20 group-hover:translate-x-1 transition-transform" />
                      </button>

                      <button
                        type="button"
                        onClick={handleMarkAsMissed}
                        className="w-full p-4 text-center text-river text-sm font-bold hover:text-charcoal transition-colors decoration-river/30 underline-offset-4 hover:underline"
                      >
                        Do not Reschedule (Mark as Missed)
                      </button>
                    </>
                  ) : (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="space-y-2"
                    >
                      <div className="flex justify-between items-center px-1 mb-2">
                        <span className="text-[10px] font-bold text-charcoal/40 uppercase tracking-widest">
                          Select new time
                        </span>
                        <button
                          type="button"
                          onClick={() => setShowTimeOptions(false)}
                          className="text-[10px] font-bold text-sage"
                        >
                          Go Back
                        </button>
                      </div>
                      <div className="grid grid-cols-3 gap-2">
                        {timeOptions.map((time) => (
                          <button
                            key={time}
                            type="button"
                            onClick={() => handleReschedule(time)}
                            className="p-3 glass-bubble flex flex-col items-center gap-1 hover:bg-sage hover:text-white group transition-all"
                          >
                            <span className="text-xs font-bold">{time}</span>
                            <span className="text-[8px] opacity-60 font-medium">
                                Free Slot
                            </span>
                          </button>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
