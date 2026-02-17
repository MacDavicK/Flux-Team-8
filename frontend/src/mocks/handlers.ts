import { goalPlannerHandlers } from "./goalPlannerHandlers";
import { tasksHandlers } from "./tasksHandlers";

export const handlers = [...goalPlannerHandlers, ...tasksHandlers];
