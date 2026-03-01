import { Link, useLocation } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { Home, MessageCircle, User } from "lucide-react";
import { useAuth } from "~/contexts/AuthContext";
import { cn } from "~/utils/cn";

interface NavItem {
  to: string;
  icon: React.ReactNode;
  label: string;
  position: "left" | "center" | "right";
}

const navItems: NavItem[] = [
  {
    to: "/",
    icon: <Home className="w-5 h-5" />,
    label: "Flow",
    position: "left",
  },
  {
    to: "/chat",
    icon: <MessageCircle className="w-6 h-6" />,
    label: "Chat",
    position: "center",
  },
  {
    to: "/reflection",
    icon: <User className="w-5 h-5" />,
    label: "Profile",
    position: "right",
  },
];

const HIDDEN_ROUTES = ["/login"];

export function BottomNav() {
  const location = useLocation();
  const { user, isAuthenticated } = useAuth();

  const isNotOnboarded = isAuthenticated && user && !user.onboarded;

  if (HIDDEN_ROUTES.includes(location.pathname) || isNotOnboarded) {
    return null;
  }

  return (
    <nav className="fixed bottom-8 left-1/2 transform -translate-x-1/2 w-auto z-50">
      <div className="glass-card px-4 py-3 rounded-full flex items-center gap-4 shadow-ambient">
        {navItems.map((item) => {
          const isActive = location.pathname === item.to;
          const isCenter = item.position === "center";

          return (
            <Link
              key={item.to}
              to={item.to}
              className={cn(
                "relative flex flex-col items-center justify-center transition-all duration-300 outline-none",
                isCenter
                  ? "w-14 h-14 fab-gradient text-white rounded-full shadow-glow flex items-center justify-center transform group -my-4 translate-y-[-6px]"
                  : "w-14 h-10 rounded-2xl",
                isCenter && isActive && "animate-pulse-glow scale-105",
                !isCenter && "hover:bg-white/10",
                "active:scale-95 touch-manipulation",
              )}
            >
              {/* Side Items Content */}
              <div className="relative z-10 flex flex-col items-center gap-1">
                <motion.span
                  animate={{
                    y: isCenter ? 0 : isActive ? -1 : 0,
                    scale: isActive ? 1.1 : 1,
                  }}
                  className={cn(
                    "transition-colors duration-300",
                    isCenter
                      ? "text-white"
                      : isActive
                        ? "text-sage"
                        : "text-river hover:text-sage-dark",
                  )}
                >
                  {item.icon}
                </motion.span>

                {!isCenter && (
                  <span
                    className={cn(
                      "text-[9px] font-black leading-none uppercase tracking-[0.12em] transition-colors duration-300",
                      isActive ? "text-sage" : "text-river/60",
                    )}
                  >
                    {item.label}
                  </span>
                )}

                {/* Active Indicator Underline */}
                {!isCenter && isActive && (
                  <motion.div
                    layoutId="activeIndicator"
                    className="w-4 h-[1.5px] bg-sage rounded-full absolute -bottom-1.5"
                    transition={{ type: "spring", stiffness: 500, damping: 30 }}
                  />
                )}
              </div>

              {/* Center Button Glow for Hover/Active */}
              {isCenter && (
                <div className="absolute inset-0 rounded-full bg-white opacity-0 group-hover:opacity-10 transition-opacity duration-300" />
              )}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
