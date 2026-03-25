import { Link, useLocation } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { Home, MessageCircle, Sparkles, UserRound } from "lucide-react";
import { useState } from "react";
import { useAuth } from "~/contexts/AuthContext";
import { cn } from "~/utils/cn";

const HIDDEN_ROUTES = ["/login"];

export function BottomNav() {
  const location = useLocation();
  const { user, isAuthenticated, hasTasks } = useAuth();
  const [showTooltip, setShowTooltip] = useState(false);

  const isNotOnboarded = isAuthenticated && user && !user.onboarded;

  if (HIDDEN_ROUTES.includes(location.pathname) || isNotOnboarded) {
    return null;
  }

  const flowDisabled = isAuthenticated && user && user.onboarded && !hasTasks;

  const notifPrefs = user?.notification_preferences as
    | { phone_number?: string }
    | null
    | undefined;
  const showPhoneAlert =
    isAuthenticated &&
    user?.onboarded &&
    !user?.phone_verified &&
    !notifPrefs?.phone_number;

  // Right nav item: Profile when tasks not yet created, Reflect otherwise
  const rightItem = flowDisabled
    ? {
        to: "/profile",
        icon: <UserRound className="w-5 h-5" />,
        label: "Profile",
      }
    : {
        to: "/reflection",
        icon: <Sparkles className="w-5 h-5" />,
        label: "Reflect",
      };

  const sideItems = [
    {
      to: "/",
      icon: <Home className="w-5 h-5" />,
      label: "Flow",
      position: "left" as const,
    },
    rightItem,
  ];

  return (
    <nav className="fixed bottom-8 left-1/2 transform -translate-x-1/2 w-auto z-50">
      <div className="glass-card px-4 py-3 rounded-full flex items-center gap-4 shadow-ambient">
        {/* Flow (left) */}
        {(() => {
          const item = sideItems[0];
          const isActive = location.pathname === item.to && !flowDisabled;

          if (flowDisabled) {
            return (
              <div className="relative">
                <button
                  type="button"
                  className="relative flex flex-col items-center justify-center w-14 h-10 rounded-2xl opacity-35 cursor-not-allowed touch-manipulation"
                  onClick={() => {
                    setShowTooltip(true);
                    setTimeout(() => setShowTooltip(false), 2000);
                  }}
                >
                  <div className="relative z-10 flex flex-col items-center gap-1">
                    <span className="text-river transition-colors duration-300">
                      {item.icon}
                    </span>
                    <span className="text-[9px] font-black leading-none uppercase tracking-[0.12em] text-river/60">
                      {item.label}
                    </span>
                  </div>
                </button>
                {showTooltip && (
                  <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 whitespace-nowrap bg-black/80 text-white text-[10px] font-medium px-2 py-1 rounded-md pointer-events-none">
                    Create a goal first
                  </div>
                )}
              </div>
            );
          }

          return (
            <Link
              to={item.to}
              className={cn(
                "relative flex flex-col items-center justify-center w-14 h-10 rounded-2xl transition-all duration-300 outline-none hover:bg-white/10 active:scale-95 touch-manipulation",
              )}
            >
              <div className="relative z-10 flex flex-col items-center gap-1">
                <motion.span
                  animate={{ y: isActive ? -1 : 0, scale: isActive ? 1.1 : 1 }}
                  className={cn(
                    "transition-colors duration-300",
                    isActive ? "text-sage" : "text-river hover:text-sage-dark",
                  )}
                >
                  {item.icon}
                </motion.span>
                <span
                  className={cn(
                    "text-[9px] font-black leading-none uppercase tracking-[0.12em] transition-colors duration-300",
                    isActive ? "text-sage" : "text-river/60",
                  )}
                >
                  {item.label}
                </span>
                {isActive && (
                  <motion.div
                    layoutId="activeIndicator"
                    className="w-4 h-[1.5px] bg-sage rounded-full absolute -bottom-1.5"
                    transition={{ type: "spring", stiffness: 500, damping: 30 }}
                  />
                )}
              </div>
            </Link>
          );
        })()}

        {/* Chat (center FAB) */}
        {(() => {
          const isActive = location.pathname === "/chat";
          return (
            <Link
              to="/chat"
              className={cn(
                "relative flex flex-col items-center justify-center w-14 h-14 fab-gradient text-white rounded-full shadow-glow transform group -my-4 translate-y-[-6px] transition-all duration-300 outline-none active:scale-95 touch-manipulation",
                isActive && "animate-pulse-glow scale-105",
              )}
            >
              <motion.span
                animate={{ scale: isActive ? 1.1 : 1 }}
                className="text-white"
              >
                <MessageCircle className="w-6 h-6" />
              </motion.span>
              <div className="absolute inset-0 rounded-full bg-white opacity-0 group-hover:opacity-10 transition-opacity duration-300" />
            </Link>
          );
        })()}

        {/* Right item: Reflect or Profile */}
        {(() => {
          const item = sideItems[1];
          const isActive = location.pathname === item.to;
          return (
            <Link
              to={item.to}
              className={cn(
                "relative flex flex-col items-center justify-center w-14 h-10 rounded-2xl transition-all duration-300 outline-none hover:bg-white/10 active:scale-95 touch-manipulation",
              )}
            >
              <div className="relative z-10 flex flex-col items-center gap-1">
                <motion.span
                  animate={{ y: isActive ? -1 : 0, scale: isActive ? 1.1 : 1 }}
                  className={cn(
                    "relative transition-colors duration-300",
                    isActive ? "text-sage" : "text-river hover:text-sage-dark",
                  )}
                >
                  {item.icon}
                  {showPhoneAlert && (
                    <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-amber-400" />
                  )}
                </motion.span>
                <span
                  className={cn(
                    "text-[9px] font-black leading-none uppercase tracking-[0.12em] transition-colors duration-300",
                    isActive ? "text-sage" : "text-river/60",
                  )}
                >
                  {item.label}
                </span>
                {isActive && (
                  <motion.div
                    layoutId="activeIndicator"
                    className="w-4 h-[1.5px] bg-sage rounded-full absolute -bottom-1.5"
                    transition={{ type: "spring", stiffness: 500, damping: 30 }}
                  />
                )}
              </div>
            </Link>
          );
        })()}
      </div>
    </nav>
  );
}
