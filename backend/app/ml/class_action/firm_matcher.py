"""
Firm Matcher for Class Actions.

Ranks law firms based on their suitability for a specific class action signal.
Criteria:
1. Jurisdiction: Firms with an office in the action's province rank higher.
2. Practice Focus: Firms specialized in the action's type (securities, record-recall, etc.) rank higher.
3. Capacity/Tier: Tier 1 firms get a baseline reputation boost.
"""

from typing import Any

from app.scrapers.law_blogs.firm_blogs import ALL_FIRMS, FirmConfig

# Mapping firm IDs to their primary jurisdictions (HQ or strong presence)
FIRM_JURISDICTIONS = {
    "mccarthy": ["ON", "QC", "BC", "AB"],
    "osler": ["ON", "QC", "AB", "BC"],
    "torys": ["ON", "AB"],
    "stikeman": ["ON", "QC", "AB", "BC"],
    "bennett_jones": ["AB", "ON", "BC"],
    "blakes": ["ON", "QC", "AB", "BC"],
    "fasken": ["ON", "QC", "BC", "AB"],
    "goodmans": ["ON"],
    "gowling": ["ON", "QC", "BC", "AB"],
    "norton_rose": ["ON", "QC", "AB", "BC"],
    "cassels": ["ON", "AB", "BC"],
    "dentons": ["ON", "QC", "AB", "BC"],
    "dla_piper": ["ON", "BC", "AB"],
    "blg": ["ON", "QC", "AB", "BC"],
    "mcmillan": ["ON", "QC", "AB", "BC"],
    "lenczner_slaght": ["ON"],
    "lerners": ["ON"],
    "lax_oleary": ["ON"],
}

class FirmMatcher:
    def __init__(self, firms: list[FirmConfig] = ALL_FIRMS):
        self.firms = firms

    def match_firms(self, action_type: str, jurisdiction: str) -> list[dict[str, Any]]:
        """
        Ranks firms for a given class action.
        
        Args:
            action_type: e.g. 'securities_capital_markets', 'product_liability'
            jurisdiction: 'ON', 'BC', 'QC', 'AB', 'FED'
            
        Returns:
            List of {firm_id, name, score, match_reasons}
        """
        results = []
        for firm in self.firms:
            score = 0.5  # Baseline
            reasons = []

            # 1. Tier Boost
            if firm.tier == 1:
                score += 0.1
                reasons.append("Tier 1 reputation")

            # 2. Jurisdiction Match
            firm_locs = FIRM_JURISDICTIONS.get(firm.firm_id, ["ON"]) # Default ON
            if jurisdiction in firm_locs:
                score += 0.2
                reasons.append(f"Strong presence in {jurisdiction}")
            elif jurisdiction == "FED":
                score += 0.1
                reasons.append("National federal capacity")

            # 3. Practice Area Match
            # Map action_type to firm.practice_focus keys
            # action_type examples: securities_capital_markets, product_liability,
            # privacy_cybersecurity, employment_labour, environmental_indigenous_energy

            normalized_type = action_type.lower()
            match_found = False
            for focus in firm.practice_focus:
                if focus in normalized_type or normalized_type in focus:
                    match_found = True
                    break

            if match_found:
                score += 0.3
                reasons.append(f"Specialized in {action_type.replace('_', ' ')}")

            results.append({
                "firm_id": firm.firm_id,
                "name": firm.firm_name,
                "score": round(min(score, 1.0), 2),
                "match_reasons": reasons
            })

        # Sort by score desc
        return sorted(results, key=lambda x: x["score"], reverse=True)

matcher = FirmMatcher()
