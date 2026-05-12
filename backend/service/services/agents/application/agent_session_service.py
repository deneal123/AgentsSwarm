from service.services.agents.domain.sessions import PseudoSession


class AgentSessionService:
    @staticmethod
    def create(session_id: str) -> PseudoSession:
        return PseudoSession(session_id=session_id)
