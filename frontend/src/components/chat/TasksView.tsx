import { motion } from "framer-motion";
import { CalendarDays, CheckCircle2, Clock } from "lucide-react";

export interface ProposedTask {
  title: string;
  description: string;
  scheduled_days: string[];
  suggested_time: string;
  duration_minutes: number;
  recurrence_rule: string;
  week_range: number[];
}

interface TasksViewProps {
  tasks: ProposedTask[];
  onConfirm?: () => void;
}

export function TasksView({ tasks, onConfirm }: TasksViewProps) {
  return (
    <div className="space-y-4 my-2">
      <div className="flex items-center gap-2 mb-1">
        <CheckCircle2 className="w-5 h-5 text-sage" />
        <h3 className="text-river font-semibold">Milestone Tasks</h3>
      </div>

      <div className="space-y-2.5">
        {tasks.map((task, index) => (
          <motion.div
            key={task.title}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.07 }}
            className="bg-white/60 backdrop-blur-sm rounded-xl p-3.5 border border-sage/15 shadow-sm"
          >
            <p className="text-sm font-semibold text-charcoal">{task.title}</p>
            {task.description && (
              <p className="text-xs text-river/65 mt-0.5 leading-relaxed">
                {task.description}
              </p>
            )}
            <div className="flex flex-wrap gap-2 mt-2">
              {task.scheduled_days.length > 0 && (
                <span className="inline-flex items-center gap-1 text-xs text-river/70 bg-sage/10 rounded-full px-2 py-0.5">
                  <CalendarDays className="w-3 h-3" />
                  {task.scheduled_days.join(", ")}
                </span>
              )}
              {task.suggested_time && (
                <span className="inline-flex items-center gap-1 text-xs text-river/70 bg-sage/10 rounded-full px-2 py-0.5">
                  <Clock className="w-3 h-3" />
                  {task.suggested_time} · {task.duration_minutes} min
                </span>
              )}
            </div>
          </motion.div>
        ))}
      </div>

      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={onConfirm}
        className="w-full py-3 bg-sage text-white rounded-2xl font-semibold shadow-lg shadow-sage/20 transition-all hover:bg-sage-dark"
      >
        Activate This Plan
      </motion.button>
    </div>
  );
}
