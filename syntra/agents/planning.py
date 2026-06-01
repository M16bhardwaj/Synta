from syntra.agents.base import SyntraAgent


class PlanningAgent(SyntraAgent):
    name = "Planning Agent"
    instructions = "Create a minimal implementation and validation plan for a bug."

    def plan(self, bug: dict, analysis: dict) -> dict:
        files = analysis.get("candidate_files") or []
        return {
            "probable_root_cause": (
                "Likely localized to files matching the bug title/description. "
                "Confirm by reading candidate files before changing code."
            ),
            "files_to_modify": files[:6],
            "implementation_plan": [
                "Inspect candidate files.",
                "Make the smallest code change that addresses the reported behavior.",
                "Avoid unrelated formatting and refactors.",
            ],
            "validation_strategy": "Run repository validations detected from project markers.",
        }
