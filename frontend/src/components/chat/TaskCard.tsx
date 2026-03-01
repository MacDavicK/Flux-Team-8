import type { Task } from "~/types/task";

export interface TaskCardProps {
  title: string;
  duration?: string;
  onAdd?: () => void;
  className?: string;
}

export type { Task };
export { Priority, TaskCategory, TaskStatus } from "~/types/task";
