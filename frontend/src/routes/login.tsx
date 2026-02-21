import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { AnimatePresence, motion } from "framer-motion";
import { Eye, EyeOff, Lock, Mail, User } from "lucide-react";
import { useState } from "react";
import { AmbientBackground } from "~/components/ui/AmbientBackground";
import { useAuth } from "~/contexts/AuthContext";
import { cn } from "~/utils/cn";

type AuthMode = "login" | "signup";

export const Route = createFileRoute("/login")({
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const { login, signup, isAuthenticated, user } = useAuth();
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | undefined>(undefined);
  const [success, setSuccess] = useState<string | undefined>(undefined);

  const postLogin = () => {
    if (user?.onboarded) {
      navigate({ to: "/" });
    } else {
      navigate({ to: "/chat" });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(undefined);
    setSuccess(undefined);
    setIsLoading(true);

    try {
      if (mode === "login") {
        await login(email, password);
        setSuccess("Welcome back!");
      } else {
        if (!name.trim()) {
          setError("Name is required");
          setIsLoading(false);
          return;
        }
        await signup(name.trim(), email, password);
        setSuccess("Account created successfully!");
      }

      postLogin();
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  const resetForm = () => {
    setEmail("");
    setPassword("");
    setName("");
    setError(undefined);
    setSuccess(undefined);
  };

  const switchMode = () => {
    setMode(mode === "login" ? "signup" : "login");
    resetForm();
  };

  const validateEmail = (email: string) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const isEmailValid = validateEmail(email);
  const isPasswordValid = password.length >= 6;
  const isNameValid = mode === "signup" ? name.trim().length >= 2 : true;
  const canSubmit =
    isEmailValid && isPasswordValid && isNameValid && !isLoading;

  if (isAuthenticated) {
    return null;
  }

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center p-4">
      <AmbientBackground />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-sm"
      >
        <div className="text-center mb-8">
          <h1 className="text-display text-3xl italic text-charcoal mb-2">
            Flux
          </h1>
          <p className="text-body text-river text-sm">
            {mode === "login"
              ? "Welcome back! Sign in to continue."
              : "Create your account to get started."}
          </p>
        </div>

        <div className="glass-card p-6">
          <div className="flex mb-6">
            <button
              type="button"
              onClick={() => {
                setMode("login");
                resetForm();
              }}
              className={cn(
                "flex-1 py-2 text-sm font-medium transition-all duration-200 rounded-l-bubble",
                mode === "login"
                  ? "bg-sage text-white"
                  : "bg-white/20 text-river hover:bg-white/30",
              )}
            >
              Login
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("signup");
                resetForm();
              }}
              className={cn(
                "flex-1 py-2 text-sm font-medium transition-all duration-200 rounded-r-bubble",
                mode === "signup"
                  ? "bg-sage text-white"
                  : "bg-white/20 text-river hover:bg-white/30",
              )}
            >
              Sign Up
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <AnimatePresence mode="wait">
              {mode === "signup" && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <div className="relative">
                    <motion.div
                      animate={{
                        color:
                          name.length > 1 && isNameValid
                            ? "#5C7C66"
                            : name.length > 0 && !isNameValid
                              ? "#C27D66"
                              : "#8A8F8B",
                      }}
                      transition={{ duration: 0.3 }}
                      className="absolute left-3 top-1/2 transform -translate-y-1/2"
                    >
                      <User className="w-4 h-4" />
                    </motion.div>
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Your name"
                      className={cn(
                        "w-full pl-10 pr-4 py-3 rounded-bubble bg-white/50",
                        "border border-glass-border focus:outline-none focus:ring-2",
                        "text-charcoal placeholder:text-river/60 text-body transition-shadow duration-300",
                        name.length > 1 && isNameValid
                          ? "ring-2 ring-sage/60 animate-[pulse-ring-sage_2s_ease-in-out_infinite]"
                          : name.length > 0 && !isNameValid
                            ? "ring-2 ring-terracotta/60 animate-[pulse-ring-error_2s_ease-in-out_infinite]"
                            : "focus:ring-sage/30",
                      )}
                    />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <div className="relative">
              <motion.div
                animate={{
                  color:
                    email.length > 0 && isEmailValid
                      ? "#5C7C66"
                      : email.length > 0 && !isEmailValid
                        ? "#C27D66"
                        : "#8A8F8B",
                }}
                transition={{ duration: 0.3 }}
                className="absolute left-3 top-1/2 transform -translate-y-1/2"
              >
                <Mail className="w-4 h-4" />
              </motion.div>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Email address"
                className={cn(
                  "w-full pl-10 pr-4 py-3 rounded-bubble bg-white/50",
                  "border border-glass-border focus:outline-none focus:ring-2",
                  "text-charcoal placeholder:text-river/60 text-body transition-shadow duration-300",
                  email.length > 0 && isEmailValid
                    ? "ring-2 ring-sage/60 animate-[pulse-ring-sage_2s_ease-in-out_infinite]"
                    : email.length > 0 && !isEmailValid
                      ? "ring-2 ring-terracotta/60 animate-[pulse-ring-error_2s_ease-in-out_infinite]"
                      : "focus:ring-sage/30",
                )}
              />
            </div>

            <div className="relative">
              <motion.div
                animate={{
                  color:
                    password.length > 0 && isPasswordValid
                      ? "#5C7C66"
                      : password.length > 0 && !isPasswordValid
                        ? "#C27D66"
                        : "#8A8F8B",
                }}
                transition={{ duration: 0.3 }}
                className="absolute left-3 top-1/2 transform -translate-y-1/2"
              >
                <Lock className="w-4 h-4" />
              </motion.div>
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                className={cn(
                  "w-full pl-10 pr-10 py-3 rounded-bubble bg-white/50",
                  "border border-glass-border focus:outline-none focus:ring-2",
                  "text-charcoal placeholder:text-river/60 text-body transition-shadow duration-300",
                  password.length > 0 && isPasswordValid
                    ? "ring-2 ring-sage/60 animate-[pulse-ring-sage_2s_ease-in-out_infinite]"
                    : password.length > 0 && !isPasswordValid
                      ? "ring-2 ring-terracotta/60 animate-[pulse-ring-error_2s_ease-in-out_infinite]"
                      : "focus:ring-sage/30",
                )}
              />
              <motion.button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2"
                aria-label={showPassword ? "Hide password" : "Show password"}
                animate={{
                  color:
                    password.length > 0 && isPasswordValid
                      ? "#5C7C66"
                      : "#8A8F8B",
                }}
                transition={{ duration: 0.3 }}
              >
                {showPassword ? (
                  <EyeOff className="w-4 h-4" />
                ) : (
                  <Eye className="w-4 h-4" />
                )}
              </motion.button>
            </div>

            <AnimatePresence mode="wait">
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="bg-terracotta/10 border border-terracotta/30 rounded-bubble p-3"
                >
                  <p className="text-terracotta text-sm text-center">{error}</p>
                </motion.div>
              )}

              {success && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="bg-sage/10 border border-sage/30 rounded-bubble p-3"
                >
                  <p className="text-sage text-sm text-center">{success}</p>
                </motion.div>
              )}
            </AnimatePresence>

            <button
              type="submit"
              disabled={!canSubmit}
              className={cn(
                "w-full py-3 rounded-bubble font-medium text-body",
                "transition-all duration-200",
                canSubmit
                  ? "bg-sage text-white hover:bg-sage-dark active:scale-[0.98]"
                  : "bg-river/30 text-white/50 cursor-not-allowed",
              )}
            >
              {isLoading ? (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full mx-auto"
                />
              ) : mode === "login" ? (
                "Sign In"
              ) : (
                "Create Account"
              )}
            </button>
          </form>

          <div className="mt-6 pt-4 border-t border-glass-border">
            <p className="text-center text-river text-xs mb-3">
              Or continue with
            </p>
            <button
              type="button"
              className={cn(
                "w-full py-3 rounded-bubble font-medium text-body",
                "bg-white/30 text-charcoal border border-glass-border",
                "hover:bg-white/40 transition-all duration-200",
                "flex items-center justify-center gap-2",
              )}
            >
              <svg
                className="w-5 h-5"
                viewBox="0 0 24 24"
                aria-label="Google logo"
              >
                <title>Google</title>
                <path
                  fill="currentColor"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="currentColor"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="currentColor"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="currentColor"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
              Continue with Google
            </button>
            <p className="text-center text-river/60 text-xs mt-3">
              Coming soon
            </p>
          </div>

          <div className="mt-4 text-center">
            <button
              type="button"
              onClick={switchMode}
              className="text-sage text-sm hover:underline"
            >
              {mode === "login"
                ? "Don't have an account? Sign up"
                : "Already have an account? Login"}
            </button>
          </div>

          {mode === "login" && (
            <p className="text-center text-river/50 text-xs mt-4">
              Demo: test@test.com / test@123
            </p>
          )}
        </div>
      </motion.div>
    </div>
  );
}
