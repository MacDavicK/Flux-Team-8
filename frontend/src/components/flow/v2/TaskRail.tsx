import { cn } from "~/utils/cn";

interface Task {
  id: string;
  title: string;
  completed: boolean;
}

interface TaskRailProps {
  tasks: Task[];
}

export function TaskRail({ tasks }: TaskRailProps) {
  const uncompletedCount = tasks.filter((t) => !t.completed).length;

  return (
    <div className="px-6 mb-8">
      <div className="flex items-center justify-between mb-1">
        <h2 className="text-xs font-bold text-river uppercase tracking-widest">
          Tasks
        </h2>
        <div className="flex items-center space-x-2">
          <span className="text-xs text-sage font-semibold bg-sage/10 px-2 py-0.5 rounded-full">
            {uncompletedCount} left
          </span>
        </div>
      </div>
      <div className="flex overflow-x-auto scrollbar-hide pb-2 snap-x space-x-2 pt-1">
        {tasks.map((task) => (
          <div key={task.id} className="snap-start shrink-0">
            <div className="glass-pebble-stone py-3 px-4 rounded-2xl w-[11rem] flex flex-col justify-center relative h-20 hover:shadow-lg transition-shadow cursor-pointer group mt-2 mr-1.5">
              <div className="absolute -top-3 -right-3 z-10">
                <div className="w-8 h-8 bg-stone border border-white/50 shadow-sm rounded-full flex items-center justify-center group-hover:border-sage transition-colors">
                  <div
                    className={cn(
                      "w-4 h-4 rounded-full border-2 transition-colors",
                      task.completed
                        ? "bg-sage border-sage"
                        : "border-river group-hover:border-sage",
                    )}
                  />
                </div>
              </div>
              <span className="text-sm font-medium text-charcoal leading-tight text-ellipsis-2-lines">
                {task.title}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
