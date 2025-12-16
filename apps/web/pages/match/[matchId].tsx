import { useRouter } from "next/router";
import { useSession } from "next-auth/react";
import { useEffect, useState, useRef } from "react";

type MatchEventType = 'CONNECTED' | 'START' | 'PA' | 'FINAL' | 'ERROR';

interface PlateAppearanceData {
  inning: number;
  half: 'TOP' | 'BOTTOM';
  seq: number;
  pitcher_id: number;
  batter_id: number;
  result_code: string;
  description: string;
  runs: number;
  outs_added: number;
  current_score: {
    home: number;
    away: number;
  };
}

export default function MatchPage() {
  const router = useRouter();
  const { matchId } = router.query;
  const { data: session, status } = useSession();
  const idToken = (session as any)?.id_token as string | undefined;

  const [logs, setLogs] = useState<PlateAppearanceData[]>([]);
  const [score, setScore] = useState({ home: 0, away: 0 });
  const [gameState, setGameState] = useState<"CONNECTING" | "READY" | "PLAYING" | "FINISHED">("CONNECTING");
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (status === "authenticated" && idToken && matchId && !wsRef.current) {
      connectWs();
    }
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [status, idToken, matchId]);

  const connectWs = () => {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    // Assuming API is on localhost:8000 for local dev, need to handle this better in prod
    // But for now, let's use the env var or hardcode for local testing if env is HTTP
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
    const wsUrl = apiBase.replace("http", "ws") + `/ws/match/${matchId}?token=${idToken}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("WS Connected");
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      console.log("WS Message:", msg);

      switch (msg.type) {
        case "CONNECTED":
          setGameState("READY");
          break;
        case "PA":
          setGameState("PLAYING");
          setLogs((prev) => [msg.data, ...prev]);
          setScore(msg.data.current_score);
          break;
        case "FINAL":
          setGameState("FINISHED");
          setScore(msg.scores);
          break;
        case "ERROR":
          alert("Error: " + msg.message);
          break;
      }
    };

    ws.onclose = () => {
      console.log("WS Closed");
    };
  };

  const handleStart = () => {
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({ type: "START" }));
    }
  };

  if (status === "loading") return <div>Loading...</div>;
  if (status === "unauthenticated") return <div>Please sign in</div>;

  return (
    <div style={{ padding: 24, fontFamily: "system-ui", maxWidth: 800, margin: "0 auto" }}>
      <button onClick={() => router.push("/")} style={{ marginBottom: 16 }}>&larr; Back to Home</button>

      <h1>Match #{matchId} Simulation</h1>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "#333", color: "white", padding: 16, borderRadius: 8 }}>
        <div style={{ fontSize: 24, fontWeight: "bold" }}>HOME {score.home}</div>
        <div style={{ textAlign: "center" }}>
          <div>{gameState}</div>
          {gameState === "READY" && (
            <button onClick={handleStart} style={{ padding: "8px 16px", fontSize: 16, cursor: "pointer" }}>
              START GAME
            </button>
          )}
        </div>
        <div style={{ fontSize: 24, fontWeight: "bold" }}>AWAY {score.away}</div>
      </div>

      <div style={{ marginTop: 24 }}>
        <h3>Game Log</h3>
        <div style={{ border: "1px solid #ccc", borderRadius: 8, height: 400, overflowY: "auto", padding: 16, background: "#f9f9f9" }}>
          {logs.length === 0 && <div style={{ color: "#999", textAlign: "center" }}>Waiting for game start...</div>}
          {logs.map((log, idx) => (
            <div key={idx} style={{ marginBottom: 12, borderBottom: "1px solid #eee", paddingBottom: 8 }}>
              <div style={{ fontWeight: "bold", color: "#555" }}>
                {log.half} {log.inning} - Seq {log.seq}
              </div>
              <div style={{ fontSize: 18 }}>
                <span style={{
                  display: "inline-block",
                  padding: "2px 6px",
                  borderRadius: 4,
                  background: ["HR", "3B", "2B", "1B"].includes(log.result_code) ? "green" : "red",
                  color: "white",
                  marginRight: 8,
                  fontSize: 14
                }}>
                  {log.result_code}
                </span>
                {log.description}
              </div>
              <div style={{ fontSize: 14, color: "#666", marginTop: 4 }}>
                Runs: {log.runs} | Outs Added: {log.outs_added}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}