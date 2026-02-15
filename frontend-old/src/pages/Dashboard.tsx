import DemoControls from './DemoControls';
import styles from './Dashboard.module.css';

const DEMO_ENABLED = import.meta.env.VITE_ENABLE_DEMO_MODE === 'true';

/** Generate time slots from 6 AM to 10 PM */
function generateTimeSlots(): string[] {
  const slots: string[] = [];
  for (let h = 6; h <= 22; h++) {
    const period = h >= 12 ? 'PM' : 'AM';
    const display = h > 12 ? h - 12 : h;
    slots.push(`${display}:00 ${period}`);
  }
  return slots;
}

const timeSlots = generateTimeSlots();

function Dashboard() {
  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  const handleAddTask = () => {
    console.log('Add task clicked');
  };

  return (
    <section className={styles.container}>
      <header className={styles.pageHeader}>
        <h2 className={styles.heading}>Today&apos;s Schedule</h2>
        <p className={styles.date}>{today}</p>
      </header>

      <div className={styles.timeline}>
        {timeSlots.map((slot) => (
          <article key={slot} className={styles.slot}>
            <span className={styles.time}>{slot}</span>
            <div className={styles.slotContent} />
          </article>
        ))}
      </div>

      <button
        className={styles.fab}
        onClick={handleAddTask}
        aria-label="Add new task"
      >
        +
      </button>

      {DEMO_ENABLED && <DemoControls />}
    </section>
  );
}

export default Dashboard;
