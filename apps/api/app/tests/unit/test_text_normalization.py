from app.domain.text_normalization import normalize_phrase_match_text, normalize_token_text


def test_normalize_token_text_repairs_common_pdf_ocr_glyphs() -> None:
    text = "sensi\u019fve informa\u019fon reten\u019fon and \ufb01ltered \ufb02ow"

    assert normalize_token_text(text) == "sensitive information retention and filtered flow"


def test_normalize_token_text_repairs_common_ai_acronym_ocr_substitution() -> None:
    assert normalize_token_text("An Al model and an A1 workflow") == "an ai model and an ai workflow"


def test_phrase_matching_ignores_equation_and_decimal_punctuation() -> None:
    source = "M = (target - measured) / max(abs(target), epsilon); drift is 0.5%."

    assert normalize_phrase_match_text(source) == (
        "m target measured max abs target epsilon drift is 0 5"
    )
