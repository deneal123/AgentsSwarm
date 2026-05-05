import os
import pytest


@pytest.mark.integration
def test_integration_placeholder():
    """Integration tests are skipped by default.

    This placeholder test asserts that the RUN_INTEGRATION env var controls
    execution of heavier E2E tests. CI does not set RUN_INTEGRATION by default.
    """
    run_integration = os.getenv("RUN_INTEGRATION", "0")
    if run_integration != "1":
        pytest.skip("Integration tests are disabled (set RUN_INTEGRATION=1 to enable)")

    # If enabled, place real integration assertions here (DB connectivity, Redis streams, etc.)
    assert True
