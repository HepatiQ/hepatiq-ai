"""Clinical reasoning agent with multi-step loop for HepatiQ."""
from typing import Any, Dict, List

from hepatiq.risk_bands import risk_category


class ClinicalAgent:
    """Stateless request-scoped agent loop."""

    def reason_loop(
        self, patient: Dict[str, Any], probability: float, contributions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        steps: List[str] = []
        assessment = self._assess_risk(probability)
        drivers = self._identify_drivers(contributions)
        steps.append("assessed")
        steps.append("identified_drivers")
        return {
            "assessment": assessment,
            "key_drivers": drivers,
            "reasoning_steps": steps,
            "confidence": "high" if probability < 0.8 and probability > 0.2 else "medium",
        }

    def _assess_risk(self, probability: float) -> Dict[str, Any]:
        band = risk_category(probability)
        urgency = {"high": "high", "intermediate": "moderate", "low": "low"}[band]
        return {
            "band": band,
            "urgency": urgency,
            "explanation": f"5-year severe event risk estimated at {probability:.1%}.",
        }

    def _identify_drivers(self, contributions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        valid = [c for c in contributions if isinstance(c.get("impact"), (int, float))]
        sorted_contrib = sorted(valid, key=lambda x: abs(x["impact"]), reverse=True)
        top_drivers = []
        for c in sorted_contrib[:5]:
            impact = c["impact"]
            direction = "increases" if impact > 0 else "decreases"
            top_drivers.append(
                {
                    "feature": c.get("feature", "unknown"),
                    "value": c.get("value", "imputed"),
                    "direction": direction,
                    "impact": impact,
                }
            )
        return top_drivers
