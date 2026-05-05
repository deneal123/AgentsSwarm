import uuid

from service.models.db.db_models import UserFile
from service.models.key_value import ServiceType


def test_user_file_repr_handles_column_alias_mode() -> None:
    model = UserFile(
        user_id=uuid.uuid4(),
        type=ServiceType.CHAT,
        file_name="smoke.txt",
        file_url="/tmp/smoke.txt",
    )

    rendered = repr(model)

    assert "UserFile" in rendered
    assert "mode=" in rendered
