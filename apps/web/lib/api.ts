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
  created_at: string;
  is_user_created: boolean;
}

const LOCAL_STORAGE_KEY = 'abs_character_data';

export async function apiGetMyCharacter(idToken: string): Promise<Character | null> {
  // Try backend first
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/me/characters`, {
      headers: { Authorization: `Bearer ${idToken}` }
    });
    if (res.ok) {
      const chars = await res.json();
      if (chars.length > 0) {
        // Sync to local storage
        if (typeof window !== 'undefined') {
          localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(chars[0]));
        }
        return chars[0];
      }
    }
  } catch (e) {
    console.warn("Backend fetch failed, checking local storage", e);
  }

  // Fallback to local storage
  if (typeof window !== 'undefined') {
    const stored = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  }
  return null;
}

export async function apiCreateCharacter(idToken: string, data: { nickname: string; contact: number; power: number; speed: number }): Promise<Character> {
  let character: Character | null = null;

  try {
    // 1. Create a World for this character (MVP simplification)
    const worldRes = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/worlds`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ world_name: `World for ${data.nickname} ${Date.now()}` })
    });

    if (worldRes.ok) {
      const world = await worldRes.json();
      const me = await apiGetMe(idToken);

      // 3. Create Character
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/characters`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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

      if (res.ok) {
        character = await res.json();
      }
    }
  } catch (e) {
    console.warn("Backend creation failed, falling back to local storage", e);
  }

  // Fallback if backend failed
  if (!character) {
    character = {
      character_id: Date.now(), // Fake ID
      world_id: 0,
      owner_account_id: 0,
      nickname: data.nickname,
      contact: data.contact,
      power: data.power,
      speed: data.speed,
      created_at: new Date().toISOString(),
      is_user_created: true
    };
  }

  // Save to local storage
  if (typeof window !== 'undefined' && character) {
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(character));
  }

  return character;
}

export async function apiDeleteCharacter(idToken: string): Promise<void> {
  // Clear local storage
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

export async function apiPerformTraining(
  characterId: number,
  trainingId: number,
  idToken?: string
): Promise<Character> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/characters/${characterId}/train`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(idToken ? { Authorization: `Bearer ${idToken}` } : {})
    },
    body: JSON.stringify({ training_id: trainingId })
  });

  if (!res.ok) {
    let msg = `API error: ${res.status}`;
    try {
      const err = await res.json();
      msg = err?.detail || msg;
    } catch { }
    throw new Error(msg);
  }
  return res.json();
}