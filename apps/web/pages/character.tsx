import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/router";
import styles from "../styles/Character.module.css";
import { apiGetMyCharacter, apiCreateCharacter, apiDeleteCharacter, Character } from "../lib/api";
import Modal from "../components/Modal";

type StatType = "contact" | "power" | "speed";

export default function CharacterPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  
  const [loading, setLoading] = useState(true);
  const [character, setCharacter] = useState<Character | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  
  // Creation Form State
  const [nickname, setNickname] = useState("");
  const [stats, setStats] = useState({ contact: 0, power: 0, speed: 0 });
  const MAX_POINTS = 10;
  
  const totalPointsUsed = stats.contact + stats.power + stats.speed;
  const pointsRemaining = MAX_POINTS - totalPointsUsed;

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/");
    } else if (status === "authenticated") {
      checkCharacter();
    }
  }, [status, router]);

  const checkCharacter = async () => {
    try {
      const idToken = (session as any)?.id_token;
      if (idToken) {
        const char = await apiGetMyCharacter(idToken);
        setCharacter(char);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const updateStat = (type: StatType, delta: number) => {
    setStats(prev => {
      const current = prev[type];
      const next = current + delta;
      
      // Validation: cannot go below 0
      if (next < 0) return prev;
      
      // Validation: cannot exceed total points constraint
      // But we can decrease even if max points used
      if (delta > 0 && totalPointsUsed >= MAX_POINTS) return prev;
      
      return { ...prev, [type]: next };
    });
  };

  const handleCreate = async () => {
    if (!nickname.trim() || totalPointsUsed !== MAX_POINTS) return; // Enforce strict 10 points usage? Or just update validation visual
    
    try {
      setLoading(true);
      const idToken = (session as any)?.id_token;
      const newChar = await apiCreateCharacter(idToken, {
        nickname,
        ...stats
      });
      setCharacter(newChar);
      setIsCreating(false);
    } catch (e) {
      alert("Failed to create character");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    try {
      setLoading(true);
      const idToken = (session as any)?.id_token;
      await apiDeleteCharacter(idToken);
      setCharacter(null);
      setShowDeleteModal(false);
    } catch (e) {
      console.error("Failed to delete character:", e);
      alert("Failed to delete character");
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

  return (
    <>
    <div className={styles.container}>
      {character ? (
        // Existing Character Viewer
        <div className={styles.card}>
          <div className={styles.characterDisplay}>
            <h2 style={{ marginBottom: 10, color: 'var(--secondary)' }}>Your Character</h2>
            <h1 className={styles.charNickname}>{character.nickname}</h1>
            
            <div className={styles.statsGrid}>
              <div className={styles.statDisplay}>
                <span>Contact</span>
                <strong>{character.contact}</strong>
              </div>
              <div className={styles.statDisplay}>
                <span>Power</span>
                <strong>{character.power}</strong>
              </div>
              <div className={styles.statDisplay}>
                <span>Speed</span>
                <strong>{character.speed}</strong>
              </div>
            </div>
            
            <div style={{ marginTop: 20, color: 'var(--secondary)', fontSize: '0.9rem' }}>
              Created: {new Date(character.created_at).toLocaleDateString()}
            </div>

            <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
              <button 
                className={styles.startButton}
                onClick={() => router.push('/dashboard')}
                style={{ 
                  flex: 1,
                  padding: '12px 24px', 
                  backgroundColor: 'var(--primary)', 
                  color: 'white', 
                  border: 'none',
                  borderRadius: 8,
                  fontSize: '1rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                Start Game
              </button>
              <button 
                className={styles.deleteButton}
                onClick={() => setShowDeleteModal(true)}
                style={{ 
                  padding: '12px 24px', 
                  backgroundColor: 'rgba(239, 68, 68, 0.1)', 
                  color: '#ef4444', 
                  border: '1px solid rgba(239, 68, 68, 0.2)',
                  borderRadius: 8
                }}
              >
                Delete
              </button>
            </div>

          </div>
        </div>
      ) : isCreating ? (
        // Creation Form
        <div className={styles.card}>
          <h2 style={{ marginBottom: '1rem' }}>Create New Character</h2>
          
          <div className={styles.inputGroup}>
            <label className={styles.label}>Nickname</label>
            <input 
              className={styles.input}
              value={nickname}
              onChange={e => setNickname(e.target.value)}
              placeholder="Enter nickname..."
            />
          </div>
          
          <div className={styles.statsGrid}>
            <div className={styles.statRow}>
              <span className={styles.statName}>Contact</span>
              <div className={styles.statControl}>
                <button 
                  className={styles.statButton} 
                  onClick={() => updateStat("contact", -1)}
                  disabled={stats.contact <= 0}
                >-</button>
                <span className={styles.statValue}>{stats.contact}</span>
                <button 
                  className={styles.statButton} 
                  onClick={() => updateStat("contact", 1)}
                  disabled={pointsRemaining <= 0}
                >+</button>
              </div>
            </div>
            
            <div className={styles.statRow}>
              <span className={styles.statName}>Power</span>
              <div className={styles.statControl}>
                <button 
                  className={styles.statButton} 
                  onClick={() => updateStat("power", -1)}
                  disabled={stats.power <= 0}
                >-</button>
                <span className={styles.statValue}>{stats.power}</span>
                <button 
                  className={styles.statButton} 
                  onClick={() => updateStat("power", 1)}
                  disabled={pointsRemaining <= 0}
                >+</button>
              </div>
            </div>
            
            <div className={styles.statRow}>
              <span className={styles.statName}>Speed</span>
              <div className={styles.statControl}>
                <button 
                  className={styles.statButton} 
                  onClick={() => updateStat("speed", -1)}
                  disabled={stats.speed <= 0}
                >-</button>
                <span className={styles.statValue}>{stats.speed}</span>
                <button 
                  className={styles.statButton} 
                  onClick={() => updateStat("speed", 1)}
                  disabled={pointsRemaining <= 0}
                >+</button>
              </div>
            </div>
          </div>
          
          <div className={styles.pointsRemaining}>
            Points Remaining: {pointsRemaining}
          </div>
          
          <button 
            className={styles.submitButton}
            onClick={handleCreate}
            disabled={!nickname || pointsRemaining !== 0}
          >
            캐릭터 생성하기
          </button>
        </div>
      ) : (
        // Empty State
        <div className={`${styles.card} ${styles.emptyCard}`}>
          <h2>No Character Found</h2>
          <p style={{ color: 'var(--secondary)', marginBottom: '1rem' }}>
            You haven't created a character yet.
          </p>
          <div style={{ 
            width: 100, height: 100, background: 'rgba(255,255,255,0.05)', 
            borderRadius: '50%', margin: '0 auto', display: 'flex', 
            alignItems: 'center', justifyContent: 'center', fontSize: '2rem',
            color: 'var(--secondary)', border: '2px dashed var(--secondary)'
          }}>
            ?
          </div>
          <button className={styles.createButton} onClick={() => setIsCreating(true)}>
            + 캐릭터 생성
          </button>
        </div>
      )}
    </div>

      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="Delete Character?"
        footer={
          <>
            <button 
              className={styles.cancelButton}
              onClick={() => setShowDeleteModal(false)}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: 'transparent',
                color: 'var(--secondary)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: 6,
                marginRight: 10
              }}
            >
              Cancel
            </button>
            <button 
              className={styles.confirmButton}
              onClick={handleDelete}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#ef4444',
                color: 'white',
                border: 'none',
                borderRadius: 6
              }}
            >
              Delete
            </button>
          </>
        }
      >
        <p>Are you sure you want to delete your character? This action cannot be undone.</p>
      </Modal>
    </>
  );
}
