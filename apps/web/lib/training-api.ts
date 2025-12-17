// Training API functions
// These will need corresponding backend endpoints to be implemented

export interface CharacterWithXP {
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

export interface Training {
    training_id: number;
    name: string;
    description: string;
    stat_type: 'contact' | 'power' | 'speed';
    icon: string;
}

export interface TrainingResult {
    character: CharacterWithXP;
    xp_gained: number;
    leveled_up: boolean;
    new_level?: number;
    is_critical: boolean;
}

// Get character with XP data
export async function apiGetCharacterWithXP(idToken: string): Promise<CharacterWithXP> {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/me/character/xp`, {
        headers: { Authorization: `Bearer ${idToken}` }
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}

// Get available trainings
export async function apiGetTrainings(): Promise<Training[]> {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/trainings`);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}

// Perform training
export async function apiPerformTraining(
    idToken: string,
    characterId: number,
    trainingId: number
): Promise<TrainingResult> {
    const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/characters/${characterId}/train`,
        {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${idToken}`
            },
            body: JSON.stringify({ training_id: trainingId })
        }
    );
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}
