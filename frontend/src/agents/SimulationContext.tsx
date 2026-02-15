import type React from "react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  type AgentResponse,
  LocationReminderAgent,
} from "./LocationReminderAgent";

interface SimulationContextType {
  locationAgent: LocationReminderAgent;
  notifications: AgentResponse[];
  addNotification: (notification: AgentResponse) => void;
  removeNotification: (index: number) => void;
  escalationSpeed: number;
  setEscalationSpeed: (speed: number) => void;
  startEscalation: () => void;
  stopEscalation: () => void;
  handleNotificationAction: (action: "done" | "snooze") => void;
}

const SimulationContext = createContext<SimulationContextType | undefined>(
  undefined,
);

export const SimulationProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [locationAgent] = useState(() => new LocationReminderAgent());
  const [notifications, setNotifications] = useState<AgentResponse[]>([]);
  const [escalationSpeed, setEscalationSpeed] = useState(1);
  const escalationTimerRef = useRef<NodeJS.Timeout | null>(null);

  const addNotification = useCallback((notification: AgentResponse) => {
    setNotifications((prev) => [...prev, notification]);
  }, []);

  const removeNotification = useCallback((index: number) => {
    setNotifications((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const stopEscalation = useCallback(() => {
    if (escalationTimerRef.current) {
      clearTimeout(escalationTimerRef.current);
      escalationTimerRef.current = null;
    }
  }, []);

  const handleNotificationAction = useCallback(
    (action: "done" | "snooze") => {
      // Both actions stop further escalation
      stopEscalation();
      // In a real app, this would also update the agent state, but for now stopping the cascade is the key visual requirement.
      console.log(`Action taken: ${action}`);
    },
    [stopEscalation],
  );

  const startEscalation = useCallback(() => {
    stopEscalation();

    // Step 2: WhatsApp after 30 "simulated" seconds
    const whatsAppDelay = (30 * 1000) / escalationSpeed;
    // Step 3: Call after another 45 "simulated" seconds (relative to WhatsApp)
    const callDelay = (45 * 1000) / escalationSpeed;

    escalationTimerRef.current = setTimeout(() => {
      const response = locationAgent.simulateEscalation("whatsapp");
      addNotification(response);

      escalationTimerRef.current = setTimeout(() => {
        const response = locationAgent.simulateEscalation("call");
        addNotification(response);
      }, callDelay);
    }, whatsAppDelay);
  }, [escalationSpeed, locationAgent, addNotification, stopEscalation]);

  useEffect(() => {
    return () => stopEscalation();
  }, [stopEscalation]);

  return (
    <SimulationContext.Provider
      value={{
        locationAgent,
        notifications,
        addNotification,
        removeNotification,
        escalationSpeed,
        setEscalationSpeed,
        startEscalation,
        stopEscalation,
        handleNotificationAction,
      }}
    >
      {children}
    </SimulationContext.Provider>
  );
};

export const useSimulation = () => {
  const context = useContext(SimulationContext);
  if (!context) {
    throw new Error("useSimulation must be used within a SimulationProvider");
  }
  return context;
};
