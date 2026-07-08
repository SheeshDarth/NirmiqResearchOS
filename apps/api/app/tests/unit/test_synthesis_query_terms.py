from app.services.synthesis_service import SynthesisService


def test_synthesis_query_terms_expand_token_positions() -> None:
    terms = SynthesisService._query_terms("How does the Transformer represent token positions?")

    assert "positional" in terms
    assert "encodings" in terms
    assert "embeddings" in terms


def test_synthesis_query_terms_expand_multi_head_attention() -> None:
    terms = SynthesisService._query_terms("Why does the paper use multi-head attention?")

    assert "representation" in terms
    assert "subspaces" in terms
    assert "positions" in terms


def test_synthesis_query_terms_expand_privacy_language() -> None:
    terms = SynthesisService._query_terms("What privacy protections are listed for generative AI workflows?")

    assert "personal" in terms
    assert "information" in terms
    assert "retention" in terms

