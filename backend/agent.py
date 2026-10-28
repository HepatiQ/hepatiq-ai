"""Clinical reasoning agent with multi-step loop for HepatiQ."""
from typing import Dict, List, Any


class ClinicalAgent:
    def __init__(self):
        self.reasoning_steps = []

    def reason_loop(self, patient: Dict[str, Any], probability: float, contributions: List[Dict[str, Any]]) -> Dict[str, Any]:
        self.reasoning_steps = []
        assessment = self._assess_risk(probability)
        drivers = self._identify_drivers(contributions)
        self.reasoning_steps.append("assessed")
        self.reasoning_steps.append("identified_drivers")
        return {
            "assessment": assessment,
            "key_drivers": drivers,
            "reasoning_steps": self.reasoning_steps,
            "confidence": "high" if probability < 0.8 and probability > 0.2 else "medium",
        }

    def _assess_risk(self, probability: float) -> Dict[str, Any]:
        if probability >= 0.40:
            band = "high"
            urgency = "high"
        elif probability >= 0.15:
            band = "intermediate"
            urgency = "moderate"
        else:
            band = "low"
            urgency = "low"
        return {
            "band": band,
            "urgency": urgency,
            "explanation": f"5-year severe event risk estimated at {probability:.1%}.",
        }

    def _identify_drivers(self, contributions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        sorted_contrib = sorted(contributions, key=lambda x: abs(x.get("impact", 0)), reverse=True)
        top_drivers = []
        for c in sorted_contrib[:5]:
            if c.get("impact") is None:
                continue
            direction = "increases" if c["impact"] > 0 else "decreases"
            top_drivers.append(
                {
                    "feature": c["feature"],
                    "value": c.get("value", "imputed"),
                    "direction": direction,
                    "impact": c["impact"],
                }
            )
        return top_drivers
