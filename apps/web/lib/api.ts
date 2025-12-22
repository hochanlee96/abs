export interface User {
  account_id: number;
  google_sub: string;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
  created_at: string;
}

export async function apiGetMe(idToken: string): Promise<User> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/me`, {
    headers: { Authorization: `Bearer ${idToken}` }
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export interface Character {
  character_id: number;
  world_id: number;
  owner_account_id: number;
  nickname: string;
  contact: number;
  power: number;
  speed: number;
  contact_xp: number;
  power_xp: number;
  speed_xp: number;
  created_at: string;
  is_user_created: boolean;
}

const LOCAL_STORAGE_KEY = 'abs_character_data';

export interface CharacterStats {
  games_played: number;
  at_bats: number;
  hits: number;
  homeruns: number;
  rbis: number;
  batting_average: number;
}

export async function apiGetCharacterStats(characterId: number): Promise<CharacterStats> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/characters/${characterId}/stats`, {
    headers: {
      "Cache-Control": "no-cache, no-store, must-revalidate",
      "Pragma": "no-cache",
      "Expires": "0"
    }
  });
  if (!res.ok) {
    throw new Error("Failed to fetch stats");
  }
  return res.json();
}

export async function apiCreateCharacter(idToken: string, data: { nickname: string; contact: number; power: number; speed: number }): Promise<Character> {
  // 1. Create a World for this character (MVP simplification)
  const worldRes = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/worlds`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ world_name: `World for ${data.nickname} ${Date.now()}` })
  });
  if (!worldRes.ok) throw new Error("Failed to create world");
  const world = await worldRes.json();

  // 2. Get User Profile to get account_id (needed for owner_account_id)
  // Actually, the backend create_character endpoint takes owner_account_id.
  // But wait, the backend endpoint `create_character` doesn't automatically set owner from token?
  // It takes `owner_account_id` in the body.
  // So we need to fetch /me first to get the ID.

  const me = await apiGetMe(idToken);

  // 3. Create Character
  console.log("Creating character with token:", idToken?.substring(0, 10) + "...");
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/characters`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${idToken}`
    },
    body: JSON.stringify({
      world_id: world.world_id,
      nickname: data.nickname,
      owner_account_id: me.account_id,
      is_user_created: true,
      contact: data.contact,
      power: data.power,
      speed: data.speed
    })
  });

  if (!res.ok) {
    throw new Error("Failed to create character");
  }
  return res.json();
}

export async function apiGetMyCharacter(idToken: string): Promise<Character | null> {
  // Try backend first
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/me/characters`, {
      headers: {
        Authorization: `Bearer ${idToken}`,
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
      }
    });
    if (res.ok) {
      const chars = await res.json();
      if (chars.length > 0) {
        // Sync to local storage
        if (typeof window !== 'undefined') {
          localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(chars[0]));
        }
        return chars[0];
      } else {
        // Backend says no characters. Trust it.
        // Clear local storage to remove stale data.
        if (typeof window !== 'undefined') {
          localStorage.removeItem(LOCAL_STORAGE_KEY);
        }
        return null;
      }
    }
  } catch (e) {
    console.warn("Backend fetch failed, checking local storage", e);
  }

  // Fallback to local storage ONLY if backend fetch failed (network error)
  if (typeof window !== 'undefined') {
    const stored = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  }
  return null;
}

export async function apiDeleteCharacter(idToken: string): Promise<void> {
  // Always clear local storage first
  if (typeof window !== 'undefined') {
    localStorage.removeItem(LOCAL_STORAGE_KEY);
  }

  // Try backend delete
  try {
    const char = await apiGetMyCharacter(idToken);
    if (!char) return;

    await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/characters/${char.character_id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${idToken}` }
    });
  } catch (e) {
    console.warn("Backend delete failed", e);
  }
}

// =====================
// Training
// =====================

export interface Training {
  training_id: number;
  train_name: string;
  contact_delta: number;
  power_delta: number;
  speed_delta: number;
}

export async function apiListTrainings(idToken?: string): Promise<Training[]> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/trainings`, {
    headers: idToken ? { Authorization: `Bearer ${idToken}` } : undefined
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export interface TrainingStatus {
  is_locked: boolean;
  reason: string | null;
  last_training: string | null;
  last_match: string | null;
}

export async function apiGetTrainingStatus(idToken: string, characterId: number): Promise<TrainingStatus> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/characters/${characterId}/training-status`, {
    headers: { Authorization: `Bearer ${idToken}` }
  });
  if (!res.ok) throw new Error("Failed to fetch training status");
  return res.json();
}

export interface TrainingResult {
  success: boolean;
  character: Character;
  xp_gained: number;
  is_critical: boolean;
  leveled_up: boolean;
  new_level: number | null;
}

export async function apiPerformTraining(
  characterId: number,
  trainingId: number,
  idToken: string
): Promise<TrainingResult> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/characters/${characterId}/train`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${idToken}`
    },
    body: JSON.stringify({ training_id: trainingId })
  });

  if (!res.ok) {
    const errorData = await res.json();
    throw new Error(errorData.detail || "Training failed");
  }
  return res.json();
}

export async function apiInitLeague(idToken: string, userCharacterId: number, worldName: string): Promise<any> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/league/init`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${idToken}`
    },
    body: JSON.stringify({ user_character_id: userCharacterId, world_name: worldName })
  });
  if (!res.ok) throw new Error(`Failed to init league: ${res.status}`);
  return res.json();
}

export async function apiGetWorldTeams(idToken: string, worldId: number): Promise<any[]> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/worlds/${worldId}/teams`, {
    headers: { Authorization: `Bearer ${idToken}` }
  });
  if (!res.ok) throw new Error("Failed to get teams");
  return res.json();
}

export async function apiGetWorldMatches(idToken: string, worldId: number): Promise<any[]> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/worlds/${worldId}/matches`, {
    headers: { Authorization: `Bearer ${idToken}` }
  });
  if (!res.ok) throw new Error("Failed to get matches");
  return res.json();
}

export async function apiPlayMatch(idToken: string, worldId?: number): Promise<{ status: string; match_id: number }> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/play`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${idToken}`
    },
    body: JSON.stringify({ world_id: worldId })
  });
  if (!res.ok) throw new Error("Failed to start match simulation");
  return res.json();
}

export async function apiGetMatch(idToken: string, matchId: number): Promise<any> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/matches/${matchId}`, {
    headers: {
      "Authorization": `Bearer ${idToken}`,
      "Cache-Control": "no-cache, no-store, must-revalidate",
      "Pragma": "no-cache",
      "Expires": "0"
    }
  });
  if (!res.ok) throw new Error("Failed to get match details");
  return res.json();
}