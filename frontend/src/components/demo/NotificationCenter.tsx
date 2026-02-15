import { useNavigate } from "@tanstack/react-router";
import { AnimatePresence, motion } from "framer-motion";
import { Bell, MessageSquare, Phone, X } from "lucide-react";
import { useSimulation } from "~/agents/SimulationContext";
import { cn } from "~/utils/cn";

export function NotificationCenter() {
  const { notifications, removeNotification, handleNotificationAction } =
    useSimulation();
  const navigate = useNavigate();

  const handleNotificationClick = (index: number) => {
    removeNotification(index);
    navigate({ to: "/chat" });
  };

  return (
    <div className="fixed top-4 left-1/2 -translate-x-1/2 z-[100] w-full max-w-sm px-4 flex flex-col gap-2">
      <AnimatePresence>
        {notifications.map((notification, index) => (
          <motion.div
            key={`${notification.type}-${index}-${notification.message.substring(0, 10)}`}
            initial={{ opacity: 0, y: -20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            onClick={() => handleNotificationClick(index)}
            className={cn(
              "glass-card p-4 shadow-2xl cursor-pointer hover:bg-white/90 transition-all",
              "border-l-4",
              notification.type === "notification" && "border-l-river",
              notification.type === "whatsapp" && "border-l-sage",
              notification.type === "call" && "border-l-terracotta",
            )}
          >
            <div className="flex items-start gap-4">
              <div
                className={cn(
                  "p-2 rounded-full",
                  notification.type === "notification" &&
                    "bg-river/10 text-river",
                  notification.type === "whatsapp" && "bg-sage/10 text-sage",
                  notification.type === "call" &&
                    "bg-terracotta/10 text-terracotta",
                )}
              >
                {notification.type === "notification" && (
                  <Bell className="w-4 h-4" />
                )}
                {notification.type === "whatsapp" && (
                  <MessageSquare className="w-4 h-4" />
                )}
                {notification.type === "call" && <Phone className="w-4 h-4" />}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex justify-between items-start">
                  <span className="text-[10px] font-bold text-charcoal/40 uppercase tracking-widest">
                    {notification.type === "notification"
                      ? "System Notification"
                      : notification.type === "whatsapp"
                        ? "WhatsApp"
                        : "Incoming Call"}
                  </span>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      removeNotification(index);
                    }}
                    className="text-charcoal/20 hover:text-charcoal/40 transition-colors"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
                <p className="text-sm font-medium text-charcoal mt-1 line-clamp-2">
                  {notification.message}
                </p>
                <div className="flex flex-col gap-2 mt-2">
                  {notification.distance && (
                    <div className="flex items-center gap-1.5 text-[10px] font-bold text-river bg-river/5 px-2 py-0.5 rounded-full w-fit">
                      <Bell className="w-2.5 h-2.5" />
                      {notification.distance} away
                    </div>
                  )}
                  {notification.type !== "text" && (
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleNotificationAction("done");
                          removeNotification(index);
                        }}
                        className="px-3 py-1 text-[10px] font-bold text-white bg-sage rounded-full hover:bg-sage/90 transition-colors shadow-sm"
                      >
                        Done
                      </button>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleNotificationAction("snooze");
                          removeNotification(index);
                        }}
                        className="px-3 py-1 text-[10px] font-bold text-charcoal/60 bg-charcoal/5 rounded-full hover:bg-charcoal/10 transition-colors"
                      >
                        Snooze
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
