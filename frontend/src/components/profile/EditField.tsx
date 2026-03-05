import { motion, AnimatePresence } from "framer-motion";
import { Check, Pencil, X } from "lucide-react";
import { useState } from "react";
import { cn } from "~/utils/cn";

interface EditFieldProps {
  label: string;
  value: string;
  onSave: (value: string) => Promise<void>;
  placeholder?: string;
  hint?: string;
  disabled?: boolean;
}

export function EditField({
  label,
  value,
  onSave,
  placeholder,
  hint,
  disabled,
}: EditFieldProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleEdit = () => {
    setDraft(value);
    setError(null);
    setEditing(true);
  };

  const handleCancel = () => {
    setEditing(false);
    setError(null);
  };

  const handleSave = async () => {
    if (draft.trim() === value.trim()) {
      setEditing(false);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSave(draft.trim());
      setEditing(false);
    } catch {
      setError("Couldn't save. Try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-1">
      <span className="text-[10px] font-semibold uppercase tracking-widest text-river/70">
        {label}
      </span>

      <AnimatePresence mode="wait" initial={false}>
        {editing ? (
          <motion.div
            key="editing"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.15 }}
            className="flex items-center gap-2"
          >
            <input
              autoFocus
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSave();
                if (e.key === "Escape") handleCancel();
              }}
              placeholder={placeholder}
              className={cn(
                "flex-1 bg-white/20 backdrop-blur-sm border border-white/40",
                "rounded-2xl px-4 py-2.5 text-sm text-charcoal",
                "placeholder:text-river/50 outline-none",
                "focus:border-sage/50 focus:bg-white/30 transition-all duration-200",
              )}
            />
            <motion.button
              onClick={handleSave}
              disabled={saving}
              whileTap={{ scale: 0.9 }}
              className={cn(
                "w-9 h-9 rounded-full fab-gradient flex items-center justify-center",
                "text-white shadow-glow shrink-0 transition-opacity",
                saving && "opacity-60",
              )}
            >
              <Check className="w-4 h-4" />
            </motion.button>
            <motion.button
              onClick={handleCancel}
              whileTap={{ scale: 0.9 }}
              className="w-9 h-9 rounded-full glass-bubble flex items-center justify-center text-river shrink-0"
            >
              <X className="w-4 h-4" />
            </motion.button>
          </motion.div>
        ) : (
          <motion.button
            key="display"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.15 }}
            onClick={disabled ? undefined : handleEdit}
            className={cn(
              "w-full flex items-center justify-between",
              "glass-bubble px-4 py-2.5 text-left",
              "transition-all duration-200",
              !disabled && "hover:bg-white/30 active:scale-[0.98] cursor-pointer",
              disabled && "opacity-60 cursor-default",
            )}
          >
            <span className="text-sm text-charcoal">
              {value || <span className="text-river/50">{placeholder}</span>}
            </span>
            {!disabled && (
              <Pencil className="w-3.5 h-3.5 text-river/50 shrink-0 ml-2" />
            )}
          </motion.button>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {error && (
          <motion.p
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="text-terracotta text-xs px-1"
          >
            {error}
          </motion.p>
        )}
        {hint && !editing && (
          <p className="text-river/50 text-xs px-1">{hint}</p>
        )}
      </AnimatePresence>
    </div>
  );
}
