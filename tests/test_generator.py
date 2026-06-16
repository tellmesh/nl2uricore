from __future__ import annotations

from nl2uricore.generator import GenerationRequest, generate_markpact


def test_generate_cache_pack_without_llm():
    text = generate_markpact(
        GenerationRequest(
            prompt="Stwórz URI pack cache:// do statusu i komendy run",
            prefix="cache",
        ),
        use_llm=False,
    )
    assert "markpact:pack" in text
    assert "cache://" in text
    assert "markpact:handler id=status" in text
    assert "markpact:handler id=run" in text
