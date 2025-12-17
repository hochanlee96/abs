import { useRouter } from "next/router";
import { useSession } from "next-auth/react";
import { useEffect, useState, useRef } from "react";
import styles from "../../styles/LiveMatch.module.css";
import { MatchEventType, BroadcastData, MatchEventMessage, SimulationResult, PlayerInfo } from "../../types/match";

import BaseballField from "../../components/BaseballField";
import PlayerCard from "../../components/PlayerCard";

export default function LiveMatchPage() {
    const router = useRouter();
    const { matchId } = router.query;
    const { data: session, status } = useSession();
    const idToken = (session as any)?.id_token as string | undefined;

    const [logs, setLogs] = useState<BroadcastData[]>([]);
    const [score, setScore] = useState<{ home: number; away: number }>({ home: 0, away: 0 });
    const [gameState, setGameState] = useState<"CONNECTING" | "READY" | "PLAYING" | "FINISHED">("CONNECTING");
    const [homeLineup, setHomeLineup] = useState<PlayerInfo[]>([]);
    const [awayLineup, setAwayLineup] = useState<PlayerInfo[]>([]);
    const wsRef = useRef<WebSocket | null>(null);

    // Auto-connect removed to allow manual start via button
    // useEffect(() => {
    //   if (status === "authenticated" && idToken && matchId && !wsRef.current) {
    //     connectWs();
    //   }
    //   return () => {
    //     if (wsRef.current) {
    //       wsRef.current.close();
    //       wsRef.current = null;
    //     }
    //   };
    // }, [status, idToken, matchId]);

    // Cleanup on unmount only
    useEffect(() => {
        return () => {
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
        };
    }, []);

    const connectWs = () => {
        const protocol = window.location.protocol === "https:" ? "wss" : "ws";
        const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
        // Use the new replay endpoint
        const wsUrl = apiBase.replace("http", "ws") + `/ws/simulation/replay/${matchId}?token=${idToken}`;

        console.log("Connecting to WS:", wsUrl);
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log("WS Connected");
        };

        ws.onmessage = (event) => {
            try {
                const msg: MatchEventMessage = JSON.parse(event.data);
                console.log("WS Message:", msg);

                switch (msg.type) {
                    case "CONNECTED":
                        setGameState("READY");
                        break;
                    case "ROSTERS":
                        if (msg.home) setHomeLineup(msg.home);
                        if (msg.away) setAwayLineup(msg.away);
                        break;
                    case "PA":
                        setGameState("PLAYING");
                        if (msg.data) {
                            setLogs((prev) => [msg.data!, ...prev]);
                            setScore({ home: msg.data.home_score, away: msg.data.away_score });
                        }
                        break;
                    case "FINAL":
                        setGameState("FINISHED");
                        if (msg.scores) {
                            setScore(msg.scores);
                        }
                        break;
                    case "ERROR":
                        alert("Error: " + msg.message);
                        break;
                }
            } catch (e) {
                console.error("Failed to parse WS message", e);
            }
        };

        ws.onclose = () => {
            console.log("WS Closed");
        };
    };

    const handleStart = () => {
        // For replay, connecting IS starting
        if (!wsRef.current) {
            connectWs();
        }
    };

    // Removed client-side mock simulation in favor of backend replay
    const handleReplaySimulation = () => {
        connectWs();
    };

    const getResultClass = (code: string) => {
        if (["HR", "3B", "2B", "1B"].includes(code)) return styles.resultHit;
        if (["BB", "HBP"].includes(code)) return styles.resultRun; // On base
        return styles.resultOut;
    };

    if (status === "loading") return <div className={styles.container}>Loading...</div>;
    if (status === "unauthenticated") {
        // Redirect or show message
        return <div className={styles.container}>Please sign in to view matches.</div>;
    }

    const currentBatterName = logs.length > 0 ? logs[0].current_batter.name : "";
    const currentPitcherName = logs.length > 0 ? logs[0].current_pitcher.name : "";
    const isTop = logs.length > 0 ? logs[0].half === "TOP" : true;

    return (
        <div className={styles.container}>
            {/* Header */}
            <div className={styles.header}>
                <button className={styles.backButton} onClick={() => router.push("/dashboard")}>
                    &larr; Dashboard
                </button>
                <div style={{ fontWeight: 600 }}>Match #{matchId}</div>
                <div className={`${styles.statusBadge} ${gameState === "CONNECTING" ? styles.statusConnecting :
                    gameState === "READY" ? styles.statusReady :
                        gameState === "PLAYING" ? styles.statusPlaying :
                            styles.statusFinished
                    }`}>
                    {gameState}
                </div>
            </div>

            {/* Scoreboard */}
            <div className={styles.scoreboard}>
                <div className={styles.teamScore}>
                    <div className={styles.teamName}>HOME</div>
                    <div className={styles.score}>{score.home}</div>
                </div>

                <div className={styles.matchInfo}>
                    {gameState === "READY" && (
                        <div style={{ display: 'flex', gap: '10px' }}>
                            <button className={styles.startButton} onClick={handleStart}>
                                START GAME
                            </button>
                            <button
                                className={styles.startButton}
                                onClick={handleReplaySimulation}
                                style={{ backgroundColor: '#8b5cf6', boxShadow: '0 4px 0 #7c3aed' }}
                            >
                                REPLAY SIM
                            </button>
                        </div>
                    )}
                    {(gameState === "CONNECTING") && (
                        <button
                            className={styles.startButton}
                            onClick={handleReplaySimulation}
                            style={{ backgroundColor: '#8b5cf6', boxShadow: '0 4px 0 #7c3aed' }}
                        >
                            REPLAY SIM
                        </button>
                    )}
                    {gameState === "PLAYING" && logs.length > 0 && (
                        <>
                            <div className={styles.inning}>
                                {logs[0].half === "TOP" ? "▲" : "▼"} {logs[0].inning}
                            </div>
                            <div style={{ color: '#888' }}>In Progress</div>
                        </>
                    )}
                    {gameState === "FINISHED" && (
                        <div className={styles.inning} style={{ color: '#ef4444' }}>FINAL</div>
                    )}
                </div>

                <div className={styles.teamScore}>
                    <div className={styles.teamName}>AWAY</div>
                    <div className={styles.score}>{score.away}</div>
                </div>
            </div>

            {/* Main Content */}
            <div className={styles.mainContent} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

                {/* Broadcast View: Lineup | Batter | Field | Pitcher | Lineup */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 2fr 1fr 1fr', gap: '10px', alignItems: 'start' }}>

                    {/* Away Lineup (Left) */}
                    <div style={{ background: '#222', padding: '10px', borderRadius: '8px', fontSize: '0.8rem' }}>
                        <div style={{ fontWeight: 'bold', marginBottom: '8px', color: '#aaa' }}>AWAY ROSTER</div>
                        {awayLineup.map((p, i) => (
                            <div key={i} style={{
                                padding: '4px',
                                borderBottom: '1px solid #333',
                                backgroundColor: (isTop && p.name === currentBatterName) || (!isTop && p.name === currentPitcherName) ? '#374151' : 'transparent',
                                color: (isTop && p.name === currentBatterName) ? '#fbbf24' : (!isTop && p.name === currentPitcherName) ? '#60a5fa' : '#ccc',
                                fontWeight: (p.name === currentBatterName || p.name === currentPitcherName) ? 'bold' : 'normal'
                            }}>
                                {p.name} <span style={{ fontSize: '0.7em', color: '#666' }}>{p.role}</span>
                            </div>
                        ))}
                    </div>

                    {/* Current Batter Info */}
                    <div>
                        {logs.length > 0 ? (
                            <>
                                <PlayerCard player={logs[0].current_batter} label="At Bat" />
                                <div style={{ marginTop: '20px' }}>
                                    <PlayerCard player={logs[0].next_batter} label="On Deck" />
                                </div>
                            </>
                        ) : (
                            <div style={{ color: '#666', textAlign: 'center', padding: '20px', background: '#2a2a2a', borderRadius: '8px' }}>
                                Waiting for lineup...
                            </div>
                        )}
                    </div>

                    {/* Center: Field */}
                    <div className={styles.fieldView} style={{ minHeight: 'auto', aspectRatio: '1/1', background: 'transparent', border: 'none' }}>
                        <BaseballField
                            runners={logs.length > 0 ? logs[0].runners : [null, null, null]}
                            pitcherName={currentPitcherName}
                        />
                    </div>

                    {/* Current Pitcher Info */}
                    <div>
                        {logs.length > 0 ? (
                            <PlayerCard player={logs[0].current_pitcher} isPitcher label="Pitching" />
                        ) : (
                            <div style={{ color: '#666', textAlign: 'center', padding: '20px', background: '#2a2a2a', borderRadius: '8px' }}>
                                Waiting for pitcher...
                            </div>
                        )}
                    </div>

                    {/* Home Lineup (Right) */}
                    <div style={{ background: '#222', padding: '10px', borderRadius: '8px', fontSize: '0.8rem' }}>
                        <div style={{ fontWeight: 'bold', marginBottom: '8px', color: '#aaa' }}>HOME ROSTER</div>
                        {homeLineup.map((p, i) => (
                            <div key={i} style={{
                                padding: '4px',
                                borderBottom: '1px solid #333',
                                backgroundColor: (!isTop && p.name === currentBatterName) || (isTop && p.name === currentPitcherName) ? '#374151' : 'transparent',
                                color: (!isTop && p.name === currentBatterName) ? '#fbbf24' : (isTop && p.name === currentPitcherName) ? '#60a5fa' : '#ccc',
                                fontWeight: (p.name === currentBatterName || p.name === currentPitcherName) ? 'bold' : 'normal'
                            }}>
                                {p.name} <span style={{ fontSize: '0.7em', color: '#666' }}>{p.role}</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Game Log */}
                <div className={styles.logContainer} style={{ height: '300px' }}>
                    <div className={styles.logHeader}>
                        <span>📜 Play-by-Play</span>
                    </div>
                    <div className={styles.logList}>
                        {logs.length === 0 && (
                            <div style={{ padding: 20, textAlign: "center", color: "#666" }}>
                                Waiting for first pitch...
                            </div>
                        )}
                        {logs.map((log, idx) => (
                            <div key={idx} className={styles.logItem}>
                                <div className={styles.logMeta}>
                                    <span>{log.half === "TOP" ? "Top" : "Bot"} {log.inning}</span>
                                    {/* BroadcastData doesn't have seq, so we use index or omit */}
                                    <span>#{logs.length - idx}</span>
                                </div>
                                <div className={styles.logResult}>
                                    <span className={`${styles.resultBadge} ${getResultClass(log.result.result_code)}`}>
                                        {log.result.result_code}
                                    </span>
                                    <span className={styles.logDesc}>{log.result.description}</span>
                                </div>
                                <div className={styles.logStats}>
                                    <span>Runs: +{log.result.runs_scored}</span>
                                    <span>Outs: {log.outs}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
