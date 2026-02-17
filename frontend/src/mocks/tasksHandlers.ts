import { delay, HttpResponse, http } from "msw";
import { EventType, type TaskRailItem, type TimelineEvent } from "~/types";

const sampleEvents: TimelineEvent[] = [
  {
    id: "1",
    title: "Deep Work: Strategy",
    description: "Focus block for Q4 roadmap planning.",
    time: "10:00",
    period: "AM",
    type: EventType.SAGE,
  },
  {
    id: "2",
    title: "Coffee w/ Team",
    description: "Discussion about the offsite.",
    time: "11:30",
    period: "AM",
    type: EventType.TERRA,
  },
  {
    id: "3",
    title: "Client Review",
    description: "Reviewing final mockups for Flux.",
    time: "01:00",
    period: "PM",
    type: EventType.STONE,
  },
  {
    id: "4",
    title: "Pick up dry cleaning",
    description: "",
    time: "03:30",
    period: "PM",
    type: EventType.STONE,
    isPast: true,
  },
  {
    id: "5",
    title: "Gym Session",
    description: "",
    time: "04:30",
    period: "PM",
    type: EventType.STONE,
    isPast: true,
  },
];

const sampleTasks: TaskRailItem[] = [
  { id: "1", title: "Email Sarah regarding brand", completed: false },
  { id: "2", title: "Sketch logo concepts", completed: false },
  { id: "3", title: "Update documentation", completed: true },
];

export interface TasksResponse {
  events: TimelineEvent[];
  tasks: TaskRailItem[];
  date: string;
}

export const tasksHandlers = [
  http.get("/api/tasks", async () => {
    await delay(300);

    const response: TasksResponse = {
      events: sampleEvents,
      tasks: sampleTasks,
      date: new Date().toISOString().split("T")[0],
    };

    return HttpResponse.json(response);
  }),
];
