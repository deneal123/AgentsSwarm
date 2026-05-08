__all__ = ["AuthService", "ProfileService"]


def __getattr__(name: str):
    if name == "AuthService":
        from service.services.profile.application.auth_service import AuthService

        return AuthService
    if name == "ProfileService":
        from service.services.profile.application.profile_service import ProfileService

        return ProfileService
    raise AttributeError(name)
