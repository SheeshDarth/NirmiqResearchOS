from app.domain.text_normalization import normalize_token_text


def test_normalize_token_text_repairs_common_pdf_ocr_glyphs() -> None:
    text = "sensi\u019fve informa\u019fon reten\u019fon and \ufb01ltered \ufb02ow"

    assert normalize_token_text(text) == "sensitive information retention and filtered flow"
