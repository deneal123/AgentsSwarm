from service.services.agents.domain.routing.policy import resolve_forced_category


def test_resolve_forced_category_audio_input_prioritizes_audio_transcribe():
    category = resolve_forced_category(
        route_override=None,
        input_type="audio",
        web_search=False,
        deep_research=False,
    )
    assert category == "audio_transcribe"


def test_resolve_forced_category_route_override_audio_transcribe():
    category = resolve_forced_category(
        route_override="audio_transcribe",
        input_type="text",
        web_search=False,
        deep_research=False,
    )
    assert category == "audio_transcribe"
