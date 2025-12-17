import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/router";
import styles from "../styles/Training.module.css";

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

    const loadCharacter = () => {
        // Dummy character data with XP system
        const dummyCharacter: CharacterWithXP = {
            character_id: 1,
            nickname: "Test Player",
            contact: 3,
            contact_xp: 75,
            contact_xp_needed: 150, // 50 * level (50 * 3)
            power: 4,
            power_xp: 50,
            power_xp_needed: 200, // 50 * level (50 * 4)
            speed: 3,
            speed_xp: 30,
            speed_xp_needed: 150, // 50 * level (50 * 3)
        };
        setCharacter(dummyCharacter);
    };

    const handleTrain = (training: Training) => {
        if (!character) return;

        setLoading(true);

        // Simulate API call delay
        setTimeout(() => {
            const updatedCharacter = { ...character };
            const statXpKey = `${training.stat_type}_xp` as keyof CharacterWithXP;
            const statXpNeededKey = `${training.stat_type}_xp_needed` as keyof CharacterWithXP;
            const statLevelKey = training.stat_type as keyof CharacterWithXP;

            let currentXp = updatedCharacter[statXpKey] as number;
            let xpNeeded = updatedCharacter[statXpNeededKey] as number;
            let currentLevel = updatedCharacter[statLevelKey] as number;

            // Random XP gain (10-35 range)
            const baseXp = Math.floor(Math.random() * 26) + 10; // Random 10-35

            // Random critical training (20% chance for 2x XP)
            const isCritical = Math.random() < 0.2;
            let xpGained = baseXp;
            if (isCritical) {
                xpGained *= 2;
                setShowBonus({ message: "🌟 Critical Training!", xp: xpGained });
                setTimeout(() => setShowBonus(null), 2000);
            }

            // Add XP
            currentXp += xpGained;

            // Check for level up
            let leveledUp = false;
            while (currentXp >= xpNeeded) {
                currentXp -= xpNeeded;
                currentLevel += 1;
                xpNeeded = currentLevel * 50; // Scaling: 50 XP per level (level 1 = 50, level 2 = 100, level 3 = 150, etc.)
                leveledUp = true;
            }

            // Update character
            (updatedCharacter[statXpKey] as number) = currentXp;
            (updatedCharacter[statXpNeededKey] as number) = xpNeeded;
            (updatedCharacter[statLevelKey] as number) = currentLevel;

            setCharacter(updatedCharacter);

            // Add to training log
            const newLog: TrainingLog = {
                id: Date.now(),
                training_name: training.name,
                stat_type: training.stat_type,
                xp_gained: xpGained,
                timestamp: new Date(),
                isCritical
            };
            setTrainingLogs(prev => [newLog, ...prev].slice(0, 10)); // Keep last 10

            // Show level up animation if leveled up
            if (leveledUp) {
                setShowLevelUp({ stat: training.stat_type, newLevel: currentLevel });
                setTimeout(() => setShowLevelUp(null), 3000);
            }

            setLoading(false);
        }, 500);
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
