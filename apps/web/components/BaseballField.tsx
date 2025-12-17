import React from 'react';
import { RunnerInfo } from '../types/match';

interface BaseballFieldProps {
    runners: (RunnerInfo | null)[];
    pitcherName?: string;
}

const BaseballField: React.FC<BaseballFieldProps> = ({ runners, pitcherName }) => {
    // runners[0] -> 1st Base
    // runners[1] -> 2nd Base
    // runners[2] -> 3rd Base

    const isOccupied = (index: number) => runners[index] !== null;

    return (
        <div style={{ width: '100%', maxWidth: '500px', margin: '0 auto', aspectRatio: '1/1', position: 'relative' }}>
            <svg viewBox="0 0 400 400" style={{ width: '100%', height: '100%', overflow: 'visible' }}>
                <defs>
                    {/* Grass Gradient */}
                    <radialGradient id="grassGradient" cx="50%" cy="100%" r="100%" fx="50%" fy="100%">
                        <stop offset="0%" stopColor="#4ade80" />
                        <stop offset="100%" stopColor="#15803d" />
                    </radialGradient>
                    {/* Dirt Pattern/Color */}
                    <pattern id="dirtPattern" width="10" height="10" patternUnits="userSpaceOnUse">
                        <rect width="10" height="10" fill="#d97706" />
                        <path d="M0 10L10 0M-2 2L2 -2M8 12L12 8" stroke="#b45309" strokeWidth="0.5" opacity="0.3" />
                    </pattern>
                </defs>

                {/* Main Field Shape (Grass) */}
                <path d="M200,350 L350,200 A212,212 0 0,0 50,200 L200,350 Z" fill="url(#grassGradient)" stroke="#166534" strokeWidth="2" />

                {/* Warning Track */}
                <path d="M350,200 A212,212 0 0,0 50,200" fill="none" stroke="#a16207" strokeWidth="20" strokeLinecap="butt" />

                {/* Foul Lines */}
                <line x1="200" y1="350" x2="50" y2="200" stroke="white" strokeWidth="2" />
                <line x1="200" y1="350" x2="350" y2="200" stroke="white" strokeWidth="2" />

                {/* Infield Dirt (Diamond) */}
                <path d="M200,340 L290,250 Q295,245 290,240 L200,150 L110,240 Q105,245 110,250 Z" fill="#d97706" stroke="#b45309" strokeWidth="1" />

                {/* Grass Infield Cutout */}
                <rect x="155" y="205" width="90" height="90" transform="rotate(45 200 250)" fill="url(#grassGradient)" rx="5" />

                {/* Bases */}
                {/* 2nd Base */}
                <rect
                    x="192" y="142" width="16" height="16" transform="rotate(45 200 150)"
                    fill={isOccupied(1) ? "#facc15" : "white"}
                    stroke="#333" strokeWidth="1"
                    style={{ transition: 'fill 0.3s ease', filter: 'drop-shadow(1px 1px 2px rgba(0,0,0,0.5))' }}
                />

                {/* 3rd Base */}
                <rect
                    x="102" y="232" width="16" height="16" transform="rotate(45 110 240)"
                    fill={isOccupied(2) ? "#facc15" : "white"}
                    stroke="#333" strokeWidth="1"
                    style={{ transition: 'fill 0.3s ease', filter: 'drop-shadow(1px 1px 2px rgba(0,0,0,0.5))' }}
                />

                {/* 1st Base */}
                <rect
                    x="282" y="232" width="16" height="16" transform="rotate(45 290 240)"
                    fill={isOccupied(0) ? "#facc15" : "white"}
                    stroke="#333" strokeWidth="1"
                    style={{ transition: 'fill 0.3s ease', filter: 'drop-shadow(1px 1px 2px rgba(0,0,0,0.5))' }}
                />

                {/* Home Plate Area (Dirt Circle) */}
                <circle cx="200" cy="350" r="20" fill="#d97706" stroke="none" />

                {/* Home Plate */}
                <path d="M192,345 L208,345 L208,353 L200,361 L192,353 Z" fill="white" stroke="#333" strokeWidth="1" />

                {/* Pitcher's Mound */}
                <circle cx="200" cy="250" r="18" fill="#d97706" stroke="#b45309" strokeWidth="1" />
                <rect x="195" y="248" width="10" height="4" fill="white" />

            </svg>

            {/* Pitcher Name Overlay */}
            {pitcherName && (
                <div style={{ position: 'absolute', top: '65%', left: '50%', transform: 'translateX(-50%)', fontSize: '11px', fontWeight: 'bold', background: 'rgba(0,0,0,0.6)', color: '#60a5fa', padding: '2px 6px', borderRadius: '4px', border: '1px solid #60a5fa', zIndex: 10 }}>
                    {pitcherName}
                </div>
            )}

            {/* Runner Names Overlay */}
            {isOccupied(1) && (
                <div style={{ position: 'absolute', top: '28%', left: '50%', transform: 'translateX(-50%)', fontSize: '11px', fontWeight: 'bold', background: 'rgba(0,0,0,0.8)', color: '#facc15', padding: '2px 6px', borderRadius: '4px', border: '1px solid #facc15', zIndex: 10 }}>
                    {runners[1]?.name}
                </div>
            )}
            {isOccupied(2) && (
                <div style={{ position: 'absolute', top: '55%', left: '15%', transform: 'translateY(-50%)', fontSize: '11px', fontWeight: 'bold', background: 'rgba(0,0,0,0.8)', color: '#facc15', padding: '2px 6px', borderRadius: '4px', border: '1px solid #facc15', zIndex: 10 }}>
                    {runners[2]?.name}
                </div>
            )}
            {isOccupied(0) && (
                <div style={{ position: 'absolute', top: '55%', right: '15%', transform: 'translateY(-50%)', fontSize: '11px', fontWeight: 'bold', background: 'rgba(0,0,0,0.8)', color: '#facc15', padding: '2px 6px', borderRadius: '4px', border: '1px solid #facc15', zIndex: 10 }}>
                    {runners[0]?.name}
                </div>
            )}
        </div>
    );
};

export default BaseballField;
