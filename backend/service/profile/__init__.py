__all__ = ["AuthService", "ProfileService"]


def __getattr__(name: str):
    if name == "AuthService":
        from service.profile.application.auth_service import AuthService

        return AuthService
    if name == "ProfileService":
        from service.profile.application.profile_service import ProfileService

        return ProfileService
    raise AttributeError(name)
