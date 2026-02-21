import { authHandlers } from "./authHandlers";
import { goalPlannerHandlers } from "./goalPlannerHandlers";
import { onboardingHandlers } from "./onboardingHandlers";
import { tasksHandlers } from "./tasksHandlers";
import { userHandlers } from "./userHandlers";

export const handlers = [
  ...authHandlers,
  ...goalPlannerHandlers,
  ...onboardingHandlers,
  ...tasksHandlers,
  ...userHandlers,
];
