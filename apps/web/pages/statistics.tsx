import { useSession } from "next-auth/react";
import { useRouter } from "next/router";
import { useEffect, useState } from "react";
import styles from "../styles/Dashboard.module.css"; // Reusing dashboard styles for consistency
import { apiGetMyCharacter, apiGetCharacterStats, CharacterStats, Character } from "../lib/api";

export default function StatisticsPage() {
    const { data: session, status } = useSession();
    const router = useRouter();
    const [character, setCharacter] = useState<Character | null>(null);
    const [stats, setStats] = useState<CharacterStats | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (status === "unauthenticated") {
            router.push("/");
        } else if (status === "authenticated") {
            loadData();
        }
    }, [status, router]);

    const loadData = async () => {
        try {
            const idToken = (session as any)?.id_token;
            if (!idToken) return;

            const char = await apiGetMyCharacter(idToken);
            setCharacter(char);

            if (char) {
                // Fetch stats using the character ID
                // Note: In a real app, we might want to handle multiple characters, but for now we assume one main character
                const charStats = await apiGetCharacterStats(char.character_id);
                setStats(charStats);
            }
        } catch (e) {
            console.error("Failed to load stats", e);
        } finally {
            setLoading(false);
        }
    };

    if (status === "loading" || loading) {
        return (
            <div className={styles.container}>
                <div className={styles.loader}>Loading...</div>
            </div>
        );
    }

    if (!character) {
        return (
            <div className={styles.container}>
                <div className={styles.header}>
                    <h1>Statistics</h1>
                    <p>No character found. Please create one first.</p>
                    <button className={styles.button} onClick={() => router.push("/character")}>
                        Create Character
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <button
                    onClick={() => router.push("/dashboard")}
                    style={{
                        background: 'none',
                        border: 'none',
                        color: '#aaa',
                        cursor: 'pointer',
                        fontSize: '1rem',
                        marginBottom: '10px'
                    }}
                >
                    &larr; Back to Dashboard
                </button>
                <h1>{character.nickname}'s Season Stats</h1>
                <p className={styles.subtitle}>Overall Performance Record</p>
            </div>

            <div className={styles.grid} style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))' }}>
                <StatCard label="Games Played" value={stats?.games_played ?? 0} icon="🏟️" />
                <StatCard label="At Bats" value={stats?.at_bats ?? 0} icon="⚾" />
                <StatCard label="Hits" value={stats?.hits ?? 0} icon="💥" />
                <StatCard label="Homeruns" value={stats?.homeruns ?? 0} icon="🎆" />
                <StatCard label="RBIs" value={stats?.rbis ?? 0} icon="🏃" />
                <StatCard label="Batting AVG" value={stats?.batting_average?.toFixed(3) ?? ".000"} icon="📊" />
            </div>
        </div>
    );
}

function StatCard({ label, value, icon }: { label: string, value: string | number, icon: string }) {
    return (
        <div style={{
            background: '#2a2a2a',
            padding: '20px',
            borderRadius: '12px',
            textAlign: 'center',
            boxShadow: '0 4px 6px rgba(0,0,0,0.2)',
            border: '1px solid #333'
        }}>
            <div style={{ fontSize: '2rem', marginBottom: '10px' }}>{icon}</div>
            <div style={{ fontSize: '0.9rem', color: '#888', textTransform: 'uppercase', letterSpacing: '1px' }}>{label}</div>
            <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#fff', marginTop: '5px' }}>{value}</div>
        </div>
    );
}
