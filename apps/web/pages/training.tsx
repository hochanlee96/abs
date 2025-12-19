import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/router";
import styles from "../styles/Training.module.css";
import { apiGetMyCharacter, apiListTrainings, apiPerformTraining } from "../lib/api";

type StatType = "contact" | "power" | "speed";

interface CharacterWithXP {
    character_id: number;
    nickname: string;
    contact: number;
    contact_xp: number;
    contact_xp_needed: number;
    power: number;
    power_xp: number;
    power_xp_needed: number;
    speed: number;
    speed_xp: number;
    speed_xp_needed: number;
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
    const [trainingLogs, setTrainingLogs] = useState<TrainingLog[]>([]);
    const [showLevelUp, setShowLevelUp] = useState<{ stat: StatType; newLevel: number } | null>(null);
    const [showBonus, setShowBonus] = useState<{ message: string; xp: number } | null>(null);

    const [trainings, setTrainings] = useState<Training[]>([]);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (status === "unauthenticated") {
            router.push("/");
        } else if (status === "authenticated") {
            loadCharacter();
            loadTrainings();
        }
    }, [status, router]);

    const loadTrainings = async () => {
        try {
            const token = (session as any)?.id_token;
            const data = await apiListTrainings(token);
            // Map to local interface
            const mapped: Training[] = data.map((t: any) => ({
                training_id: t.training_id,
                name: t.train_name,
                description: `Improve your performance in ${t.contact_delta > 0 ? 'contact' : t.power_delta > 0 ? 'power' : 'speed'}`,
                stat_type: t.contact_delta > 0 ? 'contact' : t.power_delta > 0 ? 'power' : 'speed' as StatType,
                xp_gain: 25, // Visual hint
                icon: t.contact_delta > 0 ? '🏏' : t.power_delta > 0 ? '💪' : '⚡'
            }));
            setTrainings(mapped);
        } catch (e) {
            console.error("Failed to load trainings", e);
        }
    };

    const loadCharacter = async () => {
        try {
            const token = (session as any)?.id_token;
            if (!token) return;

            const char = await apiGetMyCharacter(token);
            if (char) {
                const charWithXP: CharacterWithXP = {
                    character_id: char.character_id,
                    nickname: char.nickname,
                    contact: char.contact,
                    contact_xp: (char as any).contact_xp || 0,
                    contact_xp_needed: (char as any).contact_xp_needed || 100,
                    power: char.power,
                    power_xp: (char as any).power_xp || 0,
                    power_xp_needed: (char as any).power_xp_needed || 100,
                    speed: char.speed,
                    speed_xp: (char as any).speed_xp || 0,
                    speed_xp_needed: (char as any).speed_xp_needed || 100,
                };
                setCharacter(charWithXP);
            } else {
                router.push("/character");
            }
        } catch (e) {
            console.error("Failed to load character", e);
        }
    };

    const handleTrain = async (training: Training) => {
        if (!character) return;

        setLoading(true);
        setError(null);

        try {
            const token = (session as any)?.id_token;
            const updated = await apiPerformTraining(character.character_id, training.training_id, token) as any;

            // Check for level up by comparing old level to new level
            const oldStat = character[training.stat_type];
            const newStat = updated[training.stat_type];

            if (newStat > oldStat) {
                setShowLevelUp({ stat: training.stat_type, newLevel: newStat });
                setTimeout(() => setShowLevelUp(null), 3000);
            }

            // XP Gained visual (roughly calculate difference or just show "Done")
            // Since we don't return "XP Gained" directly from backend (it's derived), 
            // we can just refresh the character.

            const charWithXP: CharacterWithXP = {
                character_id: updated.character_id,
                nickname: updated.nickname,
                contact: updated.contact,
                contact_xp: updated.contact_xp || 0,
                contact_xp_needed: updated.contact_xp_needed || 100,
                power: updated.power,
                power_xp: updated.power_xp || 0,
                power_xp_needed: updated.power_xp_needed || 100,
                speed: updated.speed,
                speed_xp: updated.speed_xp || 0,
                speed_xp_needed: updated.speed_xp_needed || 100,
            };
            setCharacter(charWithXP);

            // Add to training log (client side history)
            const newLog: TrainingLog = {
                id: Date.now(),
                training_name: training.name,
                stat_type: training.stat_type,
                xp_gained: charWithXP[`${training.stat_type}_xp`] - character[`${training.stat_type}_xp`], // Approximated
                timestamp: new Date()
            };
            // Note: If leveled up, xp_gained might look negative in this simple diff.
            // Let's just fix the log to show something nice.
            if (newLog.xp_gained < 0) newLog.xp_gained = 0; // Or better logic

            setTrainingLogs(prev => [newLog, ...prev].slice(0, 10));

        } catch (e: any) {
            console.error("Training failed", e);
            setError(e.message);
            // Auto hide error after 3s
            setTimeout(() => setError(null), 3000);
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
            {/* Error Banner */}
            {error && (
                <div className={styles.errorBanner}>
                    <span className={styles.errorIcon}>⚠️</span>
                    {error}
                </div>
            )}

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
                                    width: `${(character.contact_xp / character.contact_xp_needed) * 100}%`,
                                    backgroundColor: getStatColor("contact")
                                }}
                            />
                        </div>
                        <div className={styles.xpText}>
                            {character.contact_xp} / {character.contact_xp_needed} XP
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
                                    width: `${(character.power_xp / character.power_xp_needed) * 100}%`,
                                    backgroundColor: getStatColor("power")
                                }}
                            />
                        </div>
                        <div className={styles.xpText}>
                            {character.power_xp} / {character.power_xp_needed} XP
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
                                    width: `${(character.speed_xp / character.speed_xp_needed) * 100}%`,
                                    backgroundColor: getStatColor("speed")
                                }}
                            />
                        </div>
                        <div className={styles.xpText}>
                            {character.speed_xp} / {character.speed_xp_needed} XP
                        </div>
                    </div>
                </div>
            </div>

            {/* Training Options */}
            <div className={styles.trainingsSection}>
                <h3>Available Training</h3>
                <div className={styles.trainingsGrid}>
                    {trainings.map(training => (
                        <div key={training.training_id} className={styles.trainingCard}>
                            <div className={styles.trainingIcon}>{training.icon}</div>
                            <h4 className={styles.trainingName}>{training.name}</h4>
                            <p className={styles.trainingDescription}>{training.description}</p>
                            <div className={styles.xpBadge} style={{ backgroundColor: getStatColor(training.stat_type) }}>
                                +10-35 {training.stat_type.toUpperCase()} XP
                            </div>
                            <button
                                className={styles.trainButton}
                                onClick={() => handleTrain(training)}
                                disabled={loading}
                            >
                                {loading ? "Training..." : "Train"}
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
