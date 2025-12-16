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
  id: number;
  user_id: number;
  nickname: string;
  contact: number;
  power: number;
  speed: number;
  created_at: string;
}

export async function apiGetMyCharacter(idToken: string): Promise<Character | null> {
  // Check if character exists in localStorage for mock persistence
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem('mock_character');
    if (saved) return JSON.parse(saved);
  }
  
  // Real API call would go here:
  // const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/my-character`, { ... });
  
  // Return null to simulate "Character does not exist"
  return null;
}

export async function apiCreateCharacter(idToken: string, data: { nickname: string; contact: number; power: number; speed: number }): Promise<Character> {
  // Mock creation
  const newChar: Character = {
    id: Date.now(),
    user_id: 123, // mock
    nickname: data.nickname,
    contact: data.contact,
    power: data.power,
    speed: data.speed,
    created_at: new Date().toISOString()
  };
  
  if (typeof window !== 'undefined') {
    localStorage.setItem('mock_character', JSON.stringify(newChar));
  }
  
  return newChar;
}

export async function apiDeleteCharacter(idToken: string): Promise<void> {
  // Mock deletion - remove from localStorage
  if (typeof window !== 'undefined') {
    localStorage.removeItem('mock_character');
  }
  
  // Real API call would go here:
  // const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/my-character`, {
  //   method: 'DELETE',
  //   headers: { Authorization: `Bearer ${idToken}` }
  // });
  // if (!res.ok) throw new Error(`API error: ${res.status}`);
}