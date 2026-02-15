import { useState } from 'react';
import styles from './DemoControls.module.css';

function DemoControls() {
  const [isOpen, setIsOpen] = useState(false);
  const [timeWarpHours, setTimeWarpHours] = useState(0);

  const handleForceMiss = () => {
    console.log('Demo: Force miss task triggered');
  };

  const handleSimulateLeaving = () => {
    console.log('Demo: Simulate leaving home triggered');
  };

  const handleReset = () => {
    console.log('Demo: Reset demo triggered');
    setTimeWarpHours(0);
  };

  return (
    <div className={styles.container}>
      {!isOpen && (
        <button
          className={styles.toggleButton}
          onClick={() => setIsOpen(true)}
          aria-label="Open demo controls"
        >
          Demo
        </button>
      )}

      {isOpen && (
        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <h3 className={styles.panelTitle}>Demo Controls</h3>
            <button
              className={styles.closeButton}
              onClick={() => setIsOpen(false)}
              aria-label="Close demo controls"
            >
              &times;
            </button>
          </div>

          <div className={styles.control}>
            <label className={styles.label} htmlFor="time-warp">
              Time Warp: <strong>{timeWarpHours}h</strong>
            </label>
            <input
              id="time-warp"
              type="range"
              min={0}
              max={24}
              value={timeWarpHours}
              onChange={(e) => setTimeWarpHours(Number(e.target.value))}
              className={styles.slider}
              aria-label="Time warp hours"
            />
          </div>

          <div className={styles.actions}>
            <button
              className={styles.actionButton}
              onClick={handleForceMiss}
              aria-label="Force miss task"
            >
              Force Miss Task
            </button>
            <button
              className={styles.actionButton}
              onClick={handleSimulateLeaving}
              aria-label="Simulate leaving home"
            >
              Simulate Leaving Home
            </button>
            <button
              className={`${styles.actionButton} ${styles.resetButton}`}
              onClick={handleReset}
              aria-label="Reset demo"
            >
              Reset Demo
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default DemoControls;
