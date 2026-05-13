from service.shared.error_handling.exceptions import ApplicationError


class ChatDomainError(ApplicationError):
    def __init__(
        self,
        message: str = "Chat domain error",
        code: str = "chat_domain_error",
        status_code: int = 400,
    ):
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

    @classmethod
    def to_code(cls, error: Exception) -> str:
        for err_type, code in cls.ERROR_CODE_MAP.items():
            if isinstance(error, err_type):
                return code
        return "chat_service_error"
