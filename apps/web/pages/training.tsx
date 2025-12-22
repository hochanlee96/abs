import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/router";
import styles from "../styles/Training.module.css";
import { apiGetMyCharacter, apiPerformTraining, apiGetTrainingStatus, TrainingStatus } from "../lib/api";

type StatType = "contact" | "power" | "speed";

interface CharacterWithXP {
    character_id: number;
    nickname: string;
    contact: number;
    contact_xp: number;
    power: number;
    power_xp: number;
    speed: number;
    speed_xp: number;
}

interface Training {
    training_id: number;
    name: string;
    description: string;
    stat_type: StatType;
    xp_gain: number;
    icon: string;
}

interface TrainingLog {
    id: number;
    training_name: string;
    stat_type: StatType;
    xp_gained: number;
    timestamp: Date;
    isCritical?: boolean;
}

export default function TrainingPage() {
    const { data: session, status } = useSession();
    const router = useRouter();

    const [loading, setLoading] = useState(false);
    const [character, setCharacter] = useState<CharacterWithXP | null>(null);
    const [trainingStatus, setTrainingStatus] = useState<TrainingStatus | null>(null);
    const [trainingLogs, setTrainingLogs] = useState<TrainingLog[]>([]);
    const [showLevelUp, setShowLevelUp] = useState<{ stat: StatType; newLevel: number } | null>(null);
    const [showBonus, setShowBonus] = useState<{ message: string; xp: number } | null>(null);
    const [error, setError] = useState<string | null>(null);

    // Dummy trainings data
    const trainings: Training[] = [
        {
            training_id: 1,
            name: "Batting Practice",
            description: "Improve your contact hitting",
            stat_type: "contact",
            xp_gain: 25, // Base XP (will be randomized)
            icon: "🏏"
        },
        {
            training_id: 2,
            name: "Weightlifting",
            description: "Build raw power",
            stat_type: "power",
            xp_gain: 25, // Base XP (will be randomized)
            icon: "💪"
        },
        {
            training_id: 3,
            name: "Sprint Drills",
            description: "Increase your speed",
            stat_type: "speed",
            xp_gain: 25, // Base XP (will be randomized)
            icon: "⚡"
        }
    ];

    useEffect(() => {
        if (status === "unauthenticated") {
            router.push("/");
        } else if (status === "authenticated") {
            loadCharacter();
        }
    }, [status, router]);

    const loadCharacter = async () => {
        try {
            const token = (session as any)?.id_token;
            if (!token) return;

            const char = await apiGetMyCharacter(token);
            if (char) {
                setCharacter({
                    character_id: char.character_id,
                    nickname: char.nickname,
                    contact: char.contact,
                    contact_xp: char.contact_xp,
                    power: char.power,
                    power_xp: char.power_xp,
                    speed: char.speed,
                    speed_xp: char.speed_xp,
                });

                // Fetch training status
                const status = await apiGetTrainingStatus(token, char.character_id);
                setTrainingStatus(status);
            } else {
                router.push("/character");
            }
        } catch (e) {
            console.error("Failed to load character or training status", e);
        }
    };

    const handleTrain = async (training: Training) => {
        if (!character || !session) return;
        setLoading(true);
        setError(null);

        try {
            const token = (session as any)?.id_token;
            const result = await apiPerformTraining(character.character_id, training.training_id, token);

            if (result.success) {
                // Update character local state
                const char = result.character;
                setCharacter({
                    character_id: char.character_id,
                    nickname: char.nickname,
                    contact: char.contact,
                    contact_xp: char.contact_xp,
                    power: char.power,
                    power_xp: char.power_xp,
                    speed: char.speed,
                    speed_xp: char.speed_xp,
                });

                // Update lock status
                setTrainingStatus(prev => prev ? { ...prev, is_locked: true } : null);

                // UI Notifications
                if (result.is_critical) {
                    setShowBonus({ message: "🌟 Critical Training!", xp: result.xp_gained });
                    setTimeout(() => setShowBonus(null), 2000);
                }

                if (result.leveled_up) {
                    setShowLevelUp({ stat: training.stat_type, newLevel: result.new_level || 0 });
                    setTimeout(() => setShowLevelUp(null), 3000);
                }

                // Log
                const newLog: TrainingLog = {
                    id: Date.now(),
                    training_name: training.name,
                    stat_type: training.stat_type,
                    xp_gained: result.xp_gained,
                    timestamp: new Date(),
                    isCritical: result.is_critical
                };
                setTrainingLogs(prev => [newLog, ...prev].slice(0, 5));
            }
        } catch (e: any) {
            setError(e.message || "Training failed");
        } finally {
            setLoading(false);
        }
    };

    const getStatColor = (stat: StatType) => {
        switch (stat) {
            case "contact": return "#3b82f6"; // blue
            case "power": return "#ef4444"; // red
            case "speed": return "#10b981"; // green
        }
    };

    const formatTimeAgo = (date: Date) => {
        const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);
        if (seconds < 60) return `${seconds} sec ago`;
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes} min ago`;
        const hours = Math.floor(minutes / 60);
        return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    };

    if (status === "loading" || !character) {
        return (
            <div className={styles.container}>
                <div className={styles.loader}>Loading...</div>
            </div>
        );
    }

    return (
        <div className={styles.container}>
            {/* Level Up Celebration */}
            {showLevelUp && (
                <div className={styles.levelUpOverlay}>
                    <div className={styles.levelUpCard}>
                        <div className={styles.levelUpIcon}>🎉</div>
                        <h2>Level Up!</h2>
                        <p>
                            {showLevelUp.stat.toUpperCase()} increased to{" "}
                            <strong>{showLevelUp.newLevel}</strong>!
                        </p>
                    </div>
                </div>
            )}

            {/* Bonus XP Notification */}
            {showBonus && (
                <div className={styles.bonusNotification}>
                    <div className={styles.bonusMessage}>
                        {showBonus.message}
                    </div>
                    <div className={styles.bonusXp}>+{showBonus.xp} XP!</div>
                </div>
            )}

            <div className={styles.header}>
                <button className={styles.backButton} onClick={() => router.push("/dashboard")}>
                    ← Back
                </button>
                <h1>Training Center 🏋️</h1>
                <p className={styles.subtitle}>Train your character to improve their stats</p>
            </div>

            {/* Character Overview */}
            <div className={styles.characterCard}>
                <h2 className={styles.characterName}>{character.nickname}</h2>

                <div className={styles.statsContainer}>
                    {/* Contact Stat */}
                    <div className={styles.statRow}>
                        <div className={styles.statHeader}>
                            <span className={styles.statName}>
                                <span className={styles.statIcon}>🏏</span>
                                Contact
                            </span>
                            <span className={styles.statLevel}>Level {character.contact}</span>
                        </div>
                        <div className={styles.progressBar}>
                            <div
                                className={styles.progressFill}
                                style={{
                                    width: `${(character.contact_xp / (character.contact * 50)) * 100}%`,
                                    backgroundColor: getStatColor("contact")
                                }}
                            />
                        </div>
                        <div className={styles.xpText}>
                            {character.contact_xp} / {character.contact * 50} XP
                        </div>
                    </div>

                    {/* Power Stat */}
                    <div className={styles.statRow}>
                        <div className={styles.statHeader}>
                            <span className={styles.statName}>
                                <span className={styles.statIcon}>💪</span>
                                Power
                            </span>
                            <span className={styles.statLevel}>Level {character.power}</span>
                        </div>
                        <div className={styles.progressBar}>
                            <div
                                className={styles.progressFill}
                                style={{
                                    width: `${(character.power_xp / (character.power * 50)) * 100}%`,
                                    backgroundColor: getStatColor("power")
                                }}
                            />
                        </div>
                        <div className={styles.xpText}>
                            {character.power_xp} / {character.power * 50} XP
                        </div>
                    </div>

                    {/* Speed Stat */}
                    <div className={styles.statRow}>
                        <div className={styles.statHeader}>
                            <span className={styles.statName}>
                                <span className={styles.statIcon}>⚡</span>
                                Speed
                            </span>
                            <span className={styles.statLevel}>Level {character.speed}</span>
                        </div>
                        <div className={styles.progressBar}>
                            <div
                                className={styles.progressFill}
                                style={{
                                    width: `${(character.speed_xp / (character.speed * 50)) * 100}%`,
                                    backgroundColor: getStatColor("speed")
                                }}
                            />
                        </div>
                        <div className={styles.xpText}>
                            {character.speed_xp} / {character.speed * 50} XP
                        </div>
                    </div>
                </div>
            </div>

            {/* Training Options */}
            <div className={styles.trainingsSection}>
                {trainingStatus?.is_locked && (
                    <div className={styles.lockBanner}>
                        <span className={styles.lockIcon}>🔒</span>
                        {trainingStatus.reason || "Run a game before continuing training"}
                    </div>
                )}

                {error && (
                    <div className={styles.errorBanner}>
                        {error}
                    </div>
                )}

                <div className={styles.trainingsGrid}>
                    {trainings.map(training => (
                        <div key={training.training_id} className={styles.trainingCard} style={trainingStatus?.is_locked ? { opacity: 0.6 } : {}}>
                            <div className={styles.trainingIcon}>{training.icon}</div>
                            <h4 className={styles.trainingName}>{training.name}</h4>
                            <p className={styles.trainingDescription}>{training.description}</p>
                            <div className={styles.xpBadge} style={{ backgroundColor: getStatColor(training.stat_type) }}>
                                +10-35 {training.stat_type.toUpperCase()} XP
                            </div>
                            <button
                                className={styles.trainButton}
                                onClick={() => handleTrain(training)}
                                disabled={loading || trainingStatus?.is_locked}
                            >
                                {loading ? "Training..." : trainingStatus?.is_locked ? "Locked" : "Train"}
                            </button>
                        </div>
                    ))}
                </div>
            </div>

            {/* Training Log */}
            {trainingLogs.length > 0 && (
                <div className={styles.logSection}>
                    <h3>Recent Training</h3>
                    <div className={styles.logContainer}>
                        {trainingLogs.map(log => (
                            <div key={log.id} className={styles.logItem}>
                                <div className={styles.logIcon} style={{ backgroundColor: getStatColor(log.stat_type) }}>
                                    {trainings.find(t => t.stat_type === log.stat_type)?.icon}
                                </div>
                                <div className={styles.logContent}>
                                    <div className={styles.logTitle}>
                                        {log.training_name}
                                        {log.isCritical && <span className={styles.criticalBadge}>⚡ CRITICAL</span>}
                                    </div>
                                    <div className={styles.logDetails}>
                                        +{log.xp_gained} {log.stat_type.toUpperCase()} XP
                                    </div>
                                </div>
                                <div className={styles.logTime}>{formatTimeAgo(log.timestamp)}</div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
