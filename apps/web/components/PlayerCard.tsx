import React from 'react';
import { PlayerInfo } from '../types/match';

interface PlayerCardProps {
    player: PlayerInfo;
    isPitcher?: boolean;
    label?: string;
}

const PlayerCard: React.FC<PlayerCardProps> = ({ player, isPitcher = false, label }) => {
    if (!player) return null;

    return (
        <div style={{
            background: '#1f2937',
            borderRadius: '8px',
            padding: '12px',
            border: '1px solid #374151',
            color: 'white',
            width: '100%',
            marginBottom: '10px'
        }}>
            {label && <div style={{ fontSize: '10px', textTransform: 'uppercase', color: '#9ca3af', marginBottom: '4px' }}>{label}</div>}
            <div style={{ fontSize: '16px', fontWeight: 'bold', marginBottom: '2px' }}>{player.name}</div>
            <div style={{ fontSize: '12px', color: '#d1d5db', marginBottom: '8px' }}>{player.role}</div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '12px' }}>
                {Object.entries(player.stats || {}).map(([key, value]) => {
                    if (typeof value === 'object' && value !== null) {
                        return (
                             <div key={key} style={{ gridColumn: 'span 2', background: '#374151', padding: '4px 8px', borderRadius: '4px' }}>
                                <div style={{ color: '#9ca3af', textTransform: 'capitalize', marginBottom: '4px' }}>{key}</div>
                                <div style={{ display: 'flex', gap: '8px', fontSize: '11px' }}>
                                    {Object.entries(value).map(([subKey, subValue]) => (
                                        <div key={subKey}>
                                            <span style={{ color: '#d1d5db', marginRight: '4px' }}>{subKey}:</span>
                                            <span style={{ fontWeight: 'bold' }}>{String(subValue)}</span>
                                        </div>
                                    ))}
                                </div>
                             </div>
                        );
                    }
                    return (
                        <div key={key} style={{ display: 'flex', justifyContent: 'space-between', background: '#374151', padding: '4px 8px', borderRadius: '4px' }}>
                            <span style={{ color: '#9ca3af', textTransform: 'capitalize' }}>{key}</span>
                            <span style={{ fontWeight: 'bold' }}>{String(value)}</span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default PlayerCard;
