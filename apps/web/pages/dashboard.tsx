import { useSession } from "next-auth/react";
import { useRouter } from "next/router";
import { useEffect } from "react";
import styles from "../styles/Dashboard.module.css";

export default function Dashboard() {
  const { data: session, status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/");
    }
  }, [status, router]);

  if (status === "loading") {
    return (
      <div className={styles.container}>
        <div className={styles.loader}>Loading...</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>Game Dashboard</h1>
        <p className={styles.subtitle}>Welcome to Agentic Baseball Simulator</p>
      </div>

      <div className={styles.grid}>
        <div className={styles.card}>
          <h2>🎮 Play Game</h2>
          <p>Start a new baseball game</p>
          <button className={styles.button}>Coming Soon</button>
        </div>

        <div className={styles.card}>
          <h2>📊 Statistics</h2>
          <p>View your performance stats</p>
          <button className={styles.button}>Coming Soon</button>
        </div>

        <div className={styles.card}>
          <h2>🏋️ Training</h2>
          <p>Improve your stats</p>
          <button
            className={styles.button}
            onClick={() => router.push("/training")}
          >
            Start Training
          </button>
        </div>

        <div className={styles.card}>
          <h2>⚙️ Character</h2>
          <p>Manage your character</p>
          <button
            className={styles.button}
            onClick={() => router.push("/character")}
          >
            View Character
          </button>
        </div>
      </div>
    </div>
  );
}
