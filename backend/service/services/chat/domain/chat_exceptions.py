from fastapi import HTTPException, status

from service.shared.exceptions import ApplicationError


class ChatDomainError(ApplicationError):
    def __init__(self, message: str = "Chat domain error", code: str = "chat_domain_error", status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(message=message, code=code, status_code=status_code)


class ModelRoutingError(ChatDomainError):
    pass


class JobOrchestrationError(ChatDomainError):
    pass


class JobServiceUnavailableError(JobOrchestrationError):
    pass


class JobCreationError(JobOrchestrationError):
    pass


class JobEnqueueError(JobOrchestrationError):
    pass


class JobExecutionError(JobOrchestrationError):
    pass


class ChatErrorMapper:
    ERROR_CODE_MAP = {
        ModelRoutingError: "model_routing_failed",
        JobServiceUnavailableError: "job_service_unavailable",
        JobCreationError: "job_creation_failed",
        JobEnqueueError: "job_enqueue_failed",
        JobExecutionError: "job_execution_failed",
        JobOrchestrationError: "job_orchestration_failed",
    }

    TRANSPORT_MAP = {
        ModelRoutingError: (status.HTTP_422_UNPROCESSABLE_ENTITY, "Model routing failed"),
        JobServiceUnavailableError: (status.HTTP_503_SERVICE_UNAVAILABLE, "Job service unavailable"),
        JobCreationError: (status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to create chat job"),
        JobEnqueueError: (status.HTTP_502_BAD_GATEWAY, "Failed to enqueue chat task"),
        JobExecutionError: (status.HTTP_504_GATEWAY_TIMEOUT, "Failed to execute chat task"),
        JobOrchestrationError: (status.HTTP_500_INTERNAL_SERVER_ERROR, "Chat orchestration failed"),
    }

    @classmethod
    def to_code(cls, error: Exception) -> str:
        for err_type, code in cls.ERROR_CODE_MAP.items():
            if isinstance(error, err_type):
                return code
        return "chat_service_error"

    @classmethod
    def to_http(cls, error: Exception) -> HTTPException:
        for err_type, payload in cls.TRANSPORT_MAP.items():
            if isinstance(error, err_type):
                status_code, detail = payload
                return HTTPException(status_code=status_code, detail={"code": cls.to_code(error), "message": detail})
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": cls.to_code(error), "message": "Agent error"},
        )


def map_chat_exception_to_http(error: Exception) -> HTTPException:
    return ChatErrorMapper.to_http(error)
