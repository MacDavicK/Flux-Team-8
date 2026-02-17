import { goalPlannerHandlers } from "./goalPlannerHandlers";
import { tasksHandlers } from "./tasksHandlers";
import { userHandlers } from "./userHandlers";

export const handlers = [
  ...goalPlannerHandlers,
  ...tasksHandlers,
  ...userHandlers,
];
