__all__ = ["JobService", "NewJobProcessor"]


def __getattr__(name: str):
    if name == "JobService":
        from service.jobs.application.job_service import JobService

        return JobService
    if name == "NewJobProcessor":
        from service.jobs.application.job_processor import NewJobProcessor

        return NewJobProcessor
    raise AttributeError(name)
