import { useSession } from "next-auth/react";
import { useRouter } from "next/router";
import { useEffect, useState, useRef } from "react";
import styles from "../styles/Dashboard.module.css";
import { apiGetMyCharacter, apiGetWorldTeams, apiGetWorldMatches, apiPlayMatch, apiGetMatch } from "../lib/api";

export default function Dashboard() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [logs, setLogs] = useState<string[]>([]);
  const [character, setCharacter] = useState<any>(null);
  const [playingMatchId, setPlayingMatchId] = useState<number | null>(null);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/");
    } else if (status === "authenticated") {
      fetchWorldData();
    }
    return () => stopPolling();
  }, [status, router]);

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  const fetchWorldData = async () => {
    try {
      const idToken = (session as any)?.id_token;
      if (!idToken) return;

      const char = await apiGetMyCharacter(idToken);
      if (!char) return;
      setCharacter(char);
      
      const teams = await apiGetWorldTeams(idToken, char.world_id);
      const matches = await apiGetWorldMatches(idToken, char.world_id);

      setLogs([
        `Found Character: ${char.nickname}`,
        `Fetched ${teams.length} Teams`,
        `Fetched ${matches.length} Matches`,
        `Ready to play.`
      ]);

    } catch (e) {
      console.error("Dashboard Data Fetch Error:", e);
    }
  };

  const handlePlayGame = async () => {
    if (!character) return;
    try {
      const idToken = (session as any)?.id_token;
      setLogs(prev => [...prev, "Starting Simulation..."]);
      
      const res = await apiPlayMatch(idToken, character.world_id);
      setPlayingMatchId(res.match_id);
      setLogs(prev => [...prev, `Simulation Started for Match #${res.match_id}`]);
      
      // Start Polling
      stopPolling();
      pollingRef.current = setInterval(async () => {
        try {
           const match = await apiGetMatch(idToken, res.match_id);
           // Show Logs
           if (match.game_state && match.game_state.logs) {
             // For simplicity, just show last few logs or all
             // Replacing logs with simulation logs
             const simLogs = match.game_state.logs;
             setLogs(simLogs.length > 20 ? simLogs.slice(-20) : simLogs);
           }
           
           if (match.status === "FINISHED") {
             setLogs(prev => [...prev, `Match Finished! Winner: Team ${match.winner_team_id}`]);
             stopPolling();
             setPlayingMatchId(null);
           }
        } catch (po) {
           console.error("Polling error", po);
        }
      }, 1000);

    } catch (e) {
      console.error(e);
      alert("Failed to play game");
    }
  };

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
          <button 
            className={styles.button}
            onClick={handlePlayGame}
            disabled={!!playingMatchId}
            style={{ opacity: playingMatchId ? 0.5 : 1 }}
          >
            {playingMatchId ? "Playing..." : "Play Match"}
          </button>
        </div>

        <div className={styles.card}>
          <h2>📊 Statistics</h2>
          <p>View your performance stats</p>
          <button className={styles.button}>Coming Soon</button>
        </div>

        <div className={styles.card}>
          <h2>🏆 Leaderboard</h2>
          <p>See top players</p>
          <button className={styles.button}>Coming Soon</button>
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

      {/* Debug Section */}
      <div style={{ marginTop: 40, borderTop: '1px solid #333', paddingTop: 20 }}>
        <h3 style={{ color: '#666', marginBottom: 10 }}>Debug Info</h3>
        <div style={{ 
          background: '#1a1a1a', 
          padding: 15, 
          borderRadius: 8, 
          fontFamily: 'monospace',
          fontSize: '0.8rem',
          color: '#4ade80'
        }}>
           {logs.length === 0 ? "Loading world data..." : logs.map((l, i) => <div key={i}>{l}</div>)}
        </div>
      </div>
    </div>
  );
}
