/**
 * Maps LangGraph node names to human-readable progress labels.
 * Shown in ThinkingIndicator while the backend processes a chat message.
 *
 * Keys must match the names passed to graph.add_node() in graph.py —
 * WITHOUT the _node suffix (e.g. "orchestrator" not "orchestrator_node").
 * astream_events emits metadata.langgraph_node using the add_node() name.
 */
export const NODE_LABELS: Record<string, string> = {
  orchestrator: "Understanding your request...",
  goal_clarifier: "Analyzing your goal...",
  goal_planner: "Building your 6-week plan...",
  classifier: "Categorizing your goal...",
  scheduler: "Scheduling your tasks...",
  pattern_observer: "Identifying habit patterns...",
  save_tasks: "Saving your plan...",
  ask_start_date: "Almost there...",
  onboarding: "Getting to know you...",
  chitchat: "Thinking...",
  task_handler: "Processing your task...",
  goal_modifier: "Updating your goal...",
  reschedule: "Rescheduling your tasks...",
};

export function getNodeLabel(node: string): string {
  return NODE_LABELS[node] ?? "Working on it...";
}
