from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import time

app = FastAPI(title="EDRCF 5.0 | M&A Signal Radar", version="5.0.0")

# Restrict CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Business Logic & Scoring Constants ---

SIGNAL_WEIGHTS = {
    "holding_creation": 5,
    "sci_creation": 3,
    "shares_contribution": 5,
    "capital_modification": 3,
    "cfo_recruitment": 4,
    "ceo_non_founder": 4,
    "m_and_a_director": 5,
    "founder_retirement": 5,
    "refinancing": 3,
    "debt_surge": 4,
    "profitability_drop": 3,
    "abnormal_growth": 4,
    "filialisation": 4,
    "carve_out": 5,
    "asset_separation": 4,
    "acquisition_disposal": 4,
    "strategic_refocus": 3,
    "sector_consolidation": 5,
    "founder_age_58_plus": 5,
    "no_succession": 4,
}

# --- Mock Data ---

MOCK_TARGETS: List[Dict[str, Any]] = [
    {
        "id": "edrcf-1",
        "name": "TechFlow Industrials",
        "sector": "Industrial Tech",
        "globalScore": 42.5,
        "priorityLevel": "Strong Opportunity",
        "topSignals": [
            {"id": "cfo_recruitment", "label": "CFO Recruitment (ex-PE)", "family": "Management"},
            {"id": "holding_creation", "label": "Holding Structure Creation", "family": "Ownership"},
            {"id": "founder_age_58_plus", "label": "Founder Age > 60", "family": "Executive"},
            {"id": "carve_out", "label": "Non-core branch Filialisation", "family": "Structure"}
        ],
        "analysis": {
            "type": "Transmission / LBO",
            "window": "6-12 months",
            "narrative": "The convergence of signals suggests ownership restructuring prior to a transmission or minority opening within 6 to 12 months. The recent recruitment of a CFO from a Private Equity background confirms professionalization in view of a process."
        },
        "activation": {
            "deciders": ["Jean-Marc Vallet (Founder)", "Sophie Durand (CFO)"],
            "approach": "Direct approach via alumni network (Ivy League/Mines)",
            "reason": "Discussion on industrial sustainability and capital structuring post-carveout."
        },
        "risks": {
            "falsePositive": "Low (0.12)",
            "uncertainties": "Founder's actual willingness to delegate the operational process."
        },
        "scores": {
            "ownership": 85,
            "management": 92,
            "financial": 45,
            "structure": 88,
            "strategic": 70
        }
    },
    {
        "id": "edrcf-2",
        "name": "BioGrid Pharma",
        "sector": "MedTech",
        "globalScore": 31.2,
        "priorityLevel": "Priority Target",
        "topSignals": [
            {"id": "strategic_refocus", "label": "Strategic refocus announced", "family": "Strategy"},
            {"id": "debt_surge", "label": "Surge in financial debt", "family": "Financial"},
            {"id": "ceo_non_founder", "label": "External CEO in place", "family": "Management"}
        ],
        "analysis": {
            "type": "Capital Opening",
            "window": "12-18 months",
            "narrative": "The rise in debt combined with a focus on core assets indicates a probable need for equity to finance the next growth phase or a partial exit of historical shareholders."
        },
        "activation": {
            "deciders": ["Marc Lepic (CEO)", "Board of Directors"],
            "approach": "Sector angle / Consolidation",
            "reason": "Support for the 2027 strategic plan and optimization of the balance sheet structure."
        },
        "risks": {
            "falsePositive": "Medium (0.21)",
            "uncertainties": "Refinancing calendar for senior debt."
        },
        "scores": {
            "ownership": 40,
            "management": 75,
            "financial": 88,
            "structure": 30,
            "strategic": 82
        }
    },
    {
        "id": "edrcf-3",
        "name": "Lumix Logistics",
        "sector": "Logistics",
        "globalScore": 24.8,
        "priorityLevel": "Preparation Needed",
        "topSignals": [
            {"id": "sci_creation", "label": "Real Estate Holding Creation", "family": "Ownership"},
            {"id": "sector_consolidation", "label": "Strong sector consolidation", "family": "Sector"}
        ],
        "analysis": {
            "type": "Disposal / Consolidation",
            "window": "18+ months",
            "narrative": "Isolating real estate assets is a classic signal of preparing for an operating business sale. In a rapidly consolidating sector, Lumix is a natural target for a roll-up strategy."
        },
        "activation": {
            "deciders": ["Luminaire Family"],
            "approach": "Strategic monitoring / Partnership",
            "reason": "Discussion on the value of real estate vs. operational assets in the current market."
        },
        "risks": {
            "falsePositive": "High (0.35)",
            "uncertainties": "Emotional attachment of the family to the business."
        },
        "scores": {
            "ownership": 90,
            "management": 30,
            "financial": 50,
            "structure": 60,
            "strategic": 75
        }
    }
]

@app.get("/api/targets")
def get_targets(
    q: Optional[str] = Query(None),
    sector: Optional[str] = Query(None)
):
    results = MOCK_TARGETS
    if q:
        q_lower = q.lower()
        results = [t for t in results if q_lower in str(t["name"]).lower() or q_lower in str(t["sector"]).lower()]
    if sector:
        results = [t for t in results if str(t["sector"]).lower() == sector.lower()]
    return {"data": results}

@app.get("/api/targets/{target_id}")
def get_target(target_id: str):
    target = next((t for t in MOCK_TARGETS if t["id"] == target_id), None)
    if target:
        return {"data": target}
    raise HTTPException(status_code=404, detail="Target not found")

@app.get("/api/signals")
def get_signals():
    signals_feed = []
    for t in MOCK_TARGETS:
        for s in t["topSignals"]:
            signals_feed.append({
                "id": f"{t['id']}-{s['id']}",
                "type": s["family"],
                "title": f"{s['label']} detected at {t['name']}",
                "time": "Recent",
                "source": "EDRCF Radar",
                "severity": "high" if t["globalScore"] > 35 else "medium",
                "location": "Global",
                "tags": [s["family"], t["sector"]]
            })
    return {"data": signals_feed}

@app.get("/api/pipeline")
def get_pipeline():
    pipeline = [
        { "id": "id", "title": "Identification", "cards": [] },
        { "id": "qual", "title": "Qualification", "cards": [] },
        { "id": "prep", "title": "Preparation Needed", "cards": [] },
        { "id": "prio", "title": "Priority Target", "cards": [] },
        { "id": "opp", "title": "Strong Opportunity", "cards": [] }
    ]
    
    for t in MOCK_TARGETS:
        level = t["priorityLevel"]
        card = {
            "id": t["id"],
            "name": t["name"],
            "sector": t["sector"],
            "score": t["globalScore"],
            "tags": [t["analysis"]["type"]],
            "priority": "high" if t["globalScore"] > 30 else "medium"
        }
        if level == "Strong Opportunity": pipeline[4]["cards"].append(card)
        elif level == "Priority Target": pipeline[3]["cards"].append(card)
        elif level == "Preparation Needed": pipeline[2]["cards"].append(card)
        elif level == "Watchlist": pipeline[1]["cards"].append(card)
        else: pipeline[0]["cards"].append(card)
        
    return {"data": pipeline}

@app.get("/api/copilot/query")
def copilot_query(q: str = Query(...)):
    time.sleep(1)
    q_l = q.lower()
    
    # Intent Detection
    if "radar" in q_l or "signal" in q_l or "highest" in q_l:
        return {"response": "The EDRCF 5.0 Radar has identified a major convergence at **TechFlow Industrials**: Holding creation + CFO recruitment + Founder > 60 years. Global Score: **42.5** (Strong Opportunity). I recommend an immediate approach via the alumni network."}
    
    if "sector" in q_l or "industry" in q_l:
        return {"response": "Current High-Intensity sectors: **Industrial Tech** (Volatility +24%) and **MedTech** (6-12 month window opening). TechFlow and BioGrid are the leading entities in these clusters."}
    
    if "techflow" in q_l:
        t = MOCK_TARGETS[0]
        return {"response": f"**TechFlow Industrials** ({t['sector']}) analysis: {t['analysis']['narrative']} Window: {t['analysis']['window']}. Activation: {t['activation']['approach']}."}

    if "biogrid" in q_l:
        t = MOCK_TARGETS[1]
        return {"response": f"**BioGrid Pharma** ({t['sector']}) shows a debt surge and strategic refocus. This indicates a potential Capital Opening within {t['analysis']['window']}. Deciders: {', '.join(t['activation']['deciders'])}."}

    if "lumix" in q_l:
        return {"response": "Lumix Logistics is in the 'Preparation Needed' phase. The isolation of real estate assets suggests a future exit. Monitor for a 18+ month horizon."}

    if "how are you" in q_l or "hello" in q_l:
        return {"response": "I am fully operational. I am currently monitoring 2,408 entities and processing 14M signals per second. How can I assist your deal origination strategy today?"}

    return {"response": "I can provide deep-dives on specific targets (TechFlow, BioGrid, Lumix), analyze specific sectors, or filter the pipeline by deal type. What would you like to explore?"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
