import React, { useEffect, useState } from 'react';
import { RunnerInfo, SimulationResult } from '../types/match';

interface BaseballFieldProps {
    runners: (RunnerInfo | null)[];
    pitcherName?: string;
    lastResult?: SimulationResult | null;
}

const BaseballField: React.FC<BaseballFieldProps> = ({ runners, pitcherName, lastResult }) => {
    // runners[0] -> 1st Base
    // runners[1] -> 2nd Base
    // runners[2] -> 3rd Base

    const isOccupied = (index: number) => runners[index] !== null;
    const [ballPos, setBallPos] = useState({ x: 200, y: 290, visible: false }); // Start at mound

    useEffect(() => {
        if (lastResult) {
            animateBall(lastResult);
        }
    }, [lastResult]);

    const animateBall = (result: SimulationResult) => {
        // 1. Pitch: Mound (200, 290) -> Home (200, 360)
        setBallPos({ x: 200, y: 290, visible: true });

        setTimeout(() => {
            setBallPos({ x: 200, y: 360, visible: true }); // Ball at plate

            // 2. Hit or Out
            setTimeout(() => {
                let targetX = 200;
                let targetY = 360;

                if (result.result_code.includes("HIT")) {
                    // Hit logic
                    if (result.description.includes("left")) { targetX = 80; targetY = 150; }
                    else if (result.description.includes("right")) { targetX = 320; targetY = 150; }
                    else { targetX = 200; targetY = 100; } // Center
                } else if (result.result_code.includes("OUT")) {
                    // Grounder to infield or flyout
                    targetX = 200 + (Math.random() * 100 - 50);
                    targetY = 270 + (Math.random() * 50);
                }

                if (targetX !== 200 || targetY !== 360) {
                    setBallPos({ x: targetX, y: targetY, visible: true });
                }

                // Hide after animation
                setTimeout(() => {
                    setBallPos(prev => ({ ...prev, visible: false }));
                }, 1500);

            }, 600); // Wait for "pitch" to reach plate
        }, 100);
    };

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

                {/* Main Field Shape (Grass) - Large Arc */}
                <path d="M200,360 L377,183 A250,250 0 0,0 23,183 L200,360 Z" fill="url(#grassGradient)" stroke="#166534" strokeWidth="2" />

                {/* Warning Track */}
                <path d="M377,183 A250,250 0 0,0 23,183" fill="none" stroke="#a16207" strokeWidth="15" strokeLinecap="butt" />

                {/* Foul Lines */}
                <line x1="200" y1="360" x2="23" y2="183" stroke="white" strokeWidth="2" />
                <line x1="200" y1="360" x2="377" y2="183" stroke="white" strokeWidth="2" />

                {/* Infield Dirt (Diamond) - Expanded */}
                {/* Home: 200,360. 1st: 270,290. 2nd: 200,220. 3rd: 130,290 */}
                <path d="M200,355 L275,285 Q280,280 275,275 L200,200 L125,275 Q120,280 125,285 Z" fill="#d97706" stroke="#b45309" strokeWidth="1" />

                {/* Grass Infield Cutout */}
                <rect x="165" y="255" width="70" height="70" transform="rotate(45 200 290)" fill="url(#grassGradient)" rx="5" />

                {/* Bases */}
                {/* 2nd Base (200, 220) */}
                <rect
                    x="191" y="211" width="18" height="18" transform="rotate(45 200 220)"
                    fill={isOccupied(1) ? "#facc15" : "white"}
                    stroke="#333" strokeWidth="1"
                    style={{ transition: 'fill 0.3s ease', filter: 'drop-shadow(1px 1px 2px rgba(0,0,0,0.5))' }}
                />

                {/* 3rd Base (130, 290) */}
                <rect
                    x="121" y="281" width="18" height="18" transform="rotate(45 130 290)"
                    fill={isOccupied(2) ? "#facc15" : "white"}
                    stroke="#333" strokeWidth="1"
                    style={{ transition: 'fill 0.3s ease', filter: 'drop-shadow(1px 1px 2px rgba(0,0,0,0.5))' }}
                />

                {/* 1st Base (270, 290) */}
                <rect
                    x="261" y="281" width="18" height="18" transform="rotate(45 270 290)"
                    fill={isOccupied(0) ? "#facc15" : "white"}
                    stroke="#333" strokeWidth="1"
                    style={{ transition: 'fill 0.3s ease', filter: 'drop-shadow(1px 1px 2px rgba(0,0,0,0.5))' }}
                />

                {/* Home Plate Area (Dirt Circle) */}
                <circle cx="200" cy="360" r="18" fill="#d97706" stroke="none" />

                {/* Home Plate */}
                <path d="M194,356 L206,356 L206,362 L200,368 L194,362 Z" fill="white" stroke="#333" strokeWidth="1" />

                {/* Pitcher's Mound (200, 290) */}
                <circle cx="200" cy="290" r="16" fill="#d97706" stroke="#b45309" strokeWidth="1" />
                <rect x="196" y="288" width="8" height="3" fill="white" />

                {/* THE BALL */}
                <circle
                    cx={ballPos.x}
                    cy={ballPos.y}
                    r="3"
                    fill="white"
                    stroke="#ccc"
                    strokeWidth="1"
                    style={{
                        opacity: ballPos.visible ? 1 : 1, // Keep visible for debugging if needed, but logic handles it
                        transition: 'cx 0.5s ease-out, cy 0.5s ease-out, opacity 0.2s',
                        filter: 'drop-shadow(0 2px 2px rgba(0,0,0,0.3))'
                    }}
                />

            </svg>

            {/* Pitcher Name Overlay */}
            {pitcherName && (
                <div style={{ position: 'absolute', top: '75%', left: '50%', transform: 'translateX(-50%)', fontSize: '10px', fontWeight: 'bold', background: 'rgba(0,0,0,0.6)', color: '#60a5fa', padding: '2px 6px', borderRadius: '4px', border: '1px solid #60a5fa', zIndex: 10 }}>
                    {pitcherName}
                </div>
            )}

            {/* Runner Names Overlay */}
            {isOccupied(1) && (
                <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translateX(-50%)', fontSize: '10px', fontWeight: 'bold', background: 'rgba(0,0,0,0.8)', color: '#facc15', padding: '2px 6px', borderRadius: '4px', border: '1px solid #facc15', zIndex: 10 }}>
                    {runners[1]?.name}
                </div>
            )}
            {isOccupied(2) && (
                <div style={{ position: 'absolute', top: '72%', left: '18%', transform: 'translateY(-50%)', fontSize: '10px', fontWeight: 'bold', background: 'rgba(0,0,0,0.8)', color: '#facc15', padding: '2px 6px', borderRadius: '4px', border: '1px solid #facc15', zIndex: 10 }}>
                    {runners[2]?.name}
                </div>
            )}
            {isOccupied(0) && (
                <div style={{ position: 'absolute', top: '72%', right: '18%', transform: 'translateY(-50%)', fontSize: '10px', fontWeight: 'bold', background: 'rgba(0,0,0,0.8)', color: '#facc15', padding: '2px 6px', borderRadius: '4px', border: '1px solid #facc15', zIndex: 10 }}>
                    {runners[0]?.name}
                </div>
            )}
        </div>
    );
};

export default BaseballField;
