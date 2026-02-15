import { motion } from "framer-motion";
import { CheckCircle2, Circle } from "lucide-react";
import { useState } from "react";
import { cn } from "~/utils/cn";

interface Todo {
  id: string;
  title: string;
  completed: boolean;
}

interface TodoSectionProps {
  todos: Todo[];
  onToggle?: (id: string) => void;
}

export function TodoSection({ todos, onToggle }: TodoSectionProps) {
  if (todos.length === 0) return null;

  return (
    <motion.div
      className="px-5 py-4"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
    >
      <h2 className="text-river text-xs font-semibold uppercase tracking-wider mb-3">
        To Do
      </h2>

      <div className="space-y-2">
        {todos.map((todo, index) => (
          <TodoItem
            key={todo.id}
            todo={todo}
            onToggle={() => onToggle?.(todo.id)}
            index={index}
          />
        ))}
      </div>
    </motion.div>
  );
}

interface TodoItemProps {
  todo: Todo;
  onToggle: () => void;
  index: number;
}

function TodoItem({ todo, onToggle, index }: TodoItemProps) {
  const [isChecked, setIsChecked] = useState(todo.completed);

  const handleToggle = () => {
    setIsChecked(!isChecked);
    onToggle();
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.4 + index * 0.1 }}
      className={cn(
        "flex items-center gap-3 p-3 rounded-bubble",
        "glass-bubble cursor-pointer touch-manipulation",
        "active:scale-[0.98] transition-transform",
      )}
      onClick={handleToggle}
    >
      <motion.div
        initial={false}
        animate={{ scale: isChecked ? 1 : 0.9 }}
        transition={{ type: "spring", stiffness: 500, damping: 30 }}
      >
        {isChecked ? (
          <CheckCircle2 className="w-5 h-5 text-sage" />
        ) : (
          <Circle className="w-5 h-5 text-river" />
        )}
      </motion.div>

      <span
        className={cn(
          "text-sm transition-all duration-200",
          isChecked ? "text-river line-through" : "text-charcoal",
        )}
      >
        {todo.title}
      </span>
    </motion.div>
  );
}
