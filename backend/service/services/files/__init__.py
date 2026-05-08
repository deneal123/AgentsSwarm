__all__ = ["FileSaverService", "BasicFileScanner"]


def __getattr__(name: str):
    if name == "FileSaverService":
        from service.services.files.application.file_saver_service import FileSaverService

        return FileSaverService
    if name == "BasicFileScanner":
        from service.services.files.application.file_scanner_service import BasicFileScanner

        return BasicFileScanner
    raise AttributeError(name)
