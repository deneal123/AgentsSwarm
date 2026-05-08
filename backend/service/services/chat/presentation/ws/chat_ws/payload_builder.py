from datetime import datetime

from service.services.chat.presentation.error_mapper import normalize_response_metadata


class ChatWsPayloadBuilder:
    @staticmethod
    def agent_reply_payload(result: dict) -> dict:
        fallback_result = result["fallback_result"]
        return {
            "type": "agent_reply",
            "reply": str(fallback_result.get("reply") or ""),
            "thread_id": result["thread_id"],
            "file_url": fallback_result.get("file_url"),
            "metadata": normalize_response_metadata(
                fallback_result.get("metadata"),
                selected_model=result["selected_model"],
            ),
            "message_id": result["message_id"],
            "timestamp": result["timestamp"],
        }

    @staticmethod
    def agent_complete_payload(result: dict) -> dict:
        fallback_result = result["fallback_result"]
        return {
            "type": "agent_complete",
            "agent_name": (fallback_result.get("metadata") or {}).get("agent_type", "general"),
            "message_id": result["message_id"],
            "timestamp": datetime.now().isoformat(),
        }
