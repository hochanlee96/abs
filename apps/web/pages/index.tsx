import { useState, useEffect } from "react";
import { signIn, signOut, useSession } from "next-auth/react";
import { apiGetMe, apiGetMyCharacters, User } from "../lib/api";
import Link from "next/link";

export default function Home() {
  const { data: session, status } = useSession();
  const [userProfile, setUserProfile] = useState<User | null>(null);
  const [characters, setCharacters] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  // Creation State
  const [newCharName, setNewCharName] = useState("");
  const [stats, setStats] = useState({ contact: 0, power: 0, speed: 0 });
  const pointsRemaining = 10 - (stats.contact + stats.power + stats.speed);

  const idToken = (session as any)?.id_token as string | undefined;

  useEffect(() => {
    if (status === "authenticated" && idToken) {
      loadData();
    }
  }, [status, idToken]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [me, myChars] = await Promise.all([
        apiGetMe(idToken!),
        apiGetMyCharacters(idToken!)
      ]);
      setUserProfile(me);
      setCharacters(myChars);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleStatChange = (stat: 'contact' | 'power' | 'speed', value: number) => {
    const newVal = Math.max(0, value);
    const otherStats = stats.contact + stats.power + stats.speed - stats[stat];

    // Prevent going over 10 total
    if (otherStats + newVal <= 10) {
      setStats(prev => ({ ...prev, [stat]: newVal }));
    }
  };

  const handleCreate = async () => {
    if (!idToken || !userProfile || !newCharName) return;
    if (pointsRemaining !== 0) {
      alert("You must distribute exactly 10 points.");
      return;
    }

    try {
      // 1. Create World (simplification)
      const worldRes = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/worlds`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ world_name: `World for ${newCharName}` })
      });
      const world = await worldRes.json();

      // 2. Create Character with Stats
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/characters`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          world_id: world.world_id,
          nickname: newCharName,
          owner_account_id: userProfile.account_id,
          is_user_created: true,
          contact: stats.contact,
          power: stats.power,
          speed: stats.speed
        })
      });

      if (res.ok) {
        alert("Character created!");
        setNewCharName("");
        setStats({ contact: 0, power: 0, speed: 0 });
        loadData(); // Reload to show dashboard
      } else {
        const err = await res.json();
        alert("Failed to create character: " + err.detail);
      }
    } catch (e) {
      console.error(e);
      alert("Error creating character");
    }
  };

  if (status === "loading" || loading) return <div style={{ padding: 24 }}>Loading...</div>;

  if (status !== "authenticated") {
    return (
      <div style={{ padding: 24, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', fontFamily: 'system-ui' }}>
        <h1>Baseball Sim MVP</h1>
        <button
          onClick={() => signIn("google")}
          style={{ padding: '12px 24px', fontSize: 18, cursor: 'pointer' }}
        >
          Sign in with Google
        </button>
      </div>
    );
  }

  // DASHBOARD VIEW (If user has a character)
  if (characters.length > 0) {
    const char = characters[0]; // Single character limit
    const ovr = Math.round((char.contact + char.power + char.speed) / 3);

    return (
      <div style={{ padding: 24, fontFamily: "system-ui", maxWidth: 800, margin: "0 auto" }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <h1>Dashboard</h1>
          <button onClick={() => signOut()}>Sign out</button>
        </div>

        <div style={{ border: "1px solid #ccc", borderRadius: 8, padding: 24, background: "#f9f9f9" }}>
          <h2 style={{ marginTop: 0 }}>{char.nickname}</h2>
          <div style={{ fontSize: 24, fontWeight: "bold", color: "#333", marginBottom: 16 }}>
            OVR: {ovr}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, marginBottom: 24 }}>
            <div style={{ background: 'white', padding: 16, borderRadius: 8, textAlign: 'center', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
              <div style={{ color: '#666', fontSize: 14 }}>CONTACT</div>
              <div style={{ fontSize: 24, fontWeight: 'bold' }}>{char.contact}</div>
            </div>
            <div style={{ background: 'white', padding: 16, borderRadius: 8, textAlign: 'center', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
              <div style={{ color: '#666', fontSize: 14 }}>POWER</div>
              <div style={{ fontSize: 24, fontWeight: 'bold' }}>{char.power}</div>
            </div>
            <div style={{ background: 'white', padding: 16, borderRadius: 8, textAlign: 'center', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
              <div style={{ color: '#666', fontSize: 14 }}>SPEED</div>
              <div style={{ fontSize: 24, fontWeight: 'bold' }}>{char.speed}</div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 16 }}>
            <Link href={`/character/${char.character_id}`} style={{ textDecoration: 'none' }}>
              <button style={{ padding: '12px 24px', fontSize: 16, cursor: 'pointer', background: '#0070f3', color: 'white', border: 'none', borderRadius: 4 }}>
                Train Character
              </button>
            </Link>
            <Link href="/match/1" style={{ textDecoration: 'none' }}>
              <button style={{ padding: '12px 24px', fontSize: 16, cursor: 'pointer', background: '#28a745', color: 'white', border: 'none', borderRadius: 4 }}>
                Play Match
              </button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // CREATE CHARACTER VIEW (If user has no characters)
  return (
    <div style={{ padding: 24, fontFamily: "system-ui", maxWidth: 600, margin: "0 auto" }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1>Create Your Player</h1>
        <button onClick={() => signOut()}>Sign out</button>
      </div>

      <div style={{ border: "1px solid #ccc", borderRadius: 8, padding: 24 }}>
        <div style={{ marginBottom: 24 }}>
          <label style={{ display: 'block', marginBottom: 8, fontWeight: 'bold' }}>Character Name</label>
          <input
            type="text"
            value={newCharName}
            onChange={(e) => setNewCharName(e.target.value)}
            style={{ width: '100%', padding: 8, fontSize: 16 }}
            placeholder="Enter name..."
          />
        </div>

        <div style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
            <h3 style={{ margin: 0 }}>Distribute Stats</h3>
            <div style={{ fontWeight: 'bold', color: pointsRemaining === 0 ? 'green' : 'red' }}>
              Points Remaining: {pointsRemaining}
            </div>
          </div>

          {['contact', 'power', 'speed'].map((stat) => (
            <div key={stat} style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ textTransform: 'capitalize' }}>{stat}</span>
                <span>{stats[stat as keyof typeof stats]}</span>
              </div>
              <input
                type="range"
                min="0"
                max="10"
                value={stats[stat as keyof typeof stats]}
                onChange={(e) => handleStatChange(stat as any, parseInt(e.target.value))}
                style={{ width: '100%' }}
              />
            </div>
          ))}
        </div>

        <button
          onClick={handleCreate}
          disabled={!newCharName || pointsRemaining !== 0}
          style={{
            width: '100%',
            padding: 16,
            fontSize: 18,
            background: (!newCharName || pointsRemaining !== 0) ? '#ccc' : '#0070f3',
            color: 'white',
            border: 'none',
            borderRadius: 4,
            cursor: (!newCharName || pointsRemaining !== 0) ? 'not-allowed' : 'pointer'
          }}
        >
          Create Character
        </button>
      </div>
    </div>
  );
}
