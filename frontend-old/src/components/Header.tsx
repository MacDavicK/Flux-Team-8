import styles from './Header.module.css';

function Header() {
  return (
    <header className={styles.header} role="banner">
      <h1 className={styles.title}>Flux</h1>
      <div className={styles.avatar} aria-label="User profile" role="img">
        <span className={styles.avatarInitial}>U</span>
      </div>
    </header>
  );
}

export default Header;
