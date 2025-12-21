
import os
import sys
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from collections import Counter

# Add project root
sys.path.append(os.getcwd())

from apps.simulation.models import SimulationResult, Character, PlayerState, Role, DirectorContext, PitcherDecision, BatterDecision, PitchType, PitchLocation, BattingStyle, UmpireZone, Weather
from apps.simulation.engine import RESOLVER_PROMPT

load_dotenv()

def test_resolver_diversity():
    print(">>> Starting AI Resolver Diversity Test (n=20)...")
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.5) # 엔진과 동일하게 0.5로 설정 (Balanced)
    prompt = ChatPromptTemplate.from_template(RESOLVER_PROMPT)
    chain = prompt | llm.with_structured_output(SimulationResult)
    
    results = []
    
    # Dummy Stats (Superstar vs Ace)
    pitcher_name = "Ryu"
    batter_name = "Lee"
    
    # Run 20 times
    for i in range(20):
        print(f"Iter {i+1}...", end="\r")
        res = chain.invoke({
            "weather": Weather.SUNNY,
            "wind": "None",
            "zone": UmpireZone.NORMAL,
            "outs": 0,
            "runners_status": "주자 없음",
            "defense_lineup": "Standard Defense",
            
            "pitcher_name": pitcher_name,
            "pitch_type": PitchType.FASTBALL,
            "pitch_location": PitchLocation.LOW,
            "velocity": 148,
            "stuff": 80, # Good Pitcher
            "control": 80,
            "mental": 80,
            
            "batter_name": batter_name,
            "aim_type": PitchType.FASTBALL,
            "aim_location": PitchLocation.LOW, # Correct Guess!
            "contact": 80, # Good Batter
            "power": 80,
            "speed": 70,
            "eye": 70,
            "clutch": 70,
            
            "validator_feedback": ""
        })
        results.append(res)
        
    print("\n\n>>> Distribution Results:")
    codes = [r.result_code for r in results]
    counts = Counter(codes)
    total = len(results)
    
    for code, count in counts.items():
        print(f"{code}: {count} ({count/total*100:.1f}%)")
        
    print("\n>>> Sample Descriptions:")
    for res in results[:5]:
        print(f"[{res.result_code}] {res.description}")

if __name__ == "__main__":
    test_resolver_diversity()
