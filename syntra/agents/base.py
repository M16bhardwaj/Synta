try:
    from agno.agent import Agent
except Exception:  # pragma: no cover - keeps imports usable if Agno changes its import path
    Agent = None


class SyntraAgent:
    name = "Syntra Agent"
    instructions = ""

    def agno_agent(self):
        if Agent is None:
            return None
        return Agent(name=self.name, instructions=self.instructions)
