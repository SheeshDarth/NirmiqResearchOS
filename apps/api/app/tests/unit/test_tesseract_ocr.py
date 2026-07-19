from pathlib import Path

from app.adapters.parsing.tesseract_ocr import TesseractOCR


def test_tesseract_resolves_explicit_executable(tmp_path: Path) -> None:
    executable = tmp_path / "tesseract.exe"
    executable.write_bytes(b"test")

    assert TesseractOCR._resolve_executable(str(executable)) == str(executable.resolve())


def test_tesseract_resolves_environment_executable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    executable = tmp_path / "configured-tesseract.exe"
    executable.write_bytes(b"test")
    monkeypatch.setenv("TESSERACT_CMD", str(executable))
    monkeypatch.setattr("shutil.which", lambda _name: None)

    assert TesseractOCR._resolve_executable() == str(executable.resolve())


def test_tesseract_availability_requires_successful_binary_probe(
    tmp_path: Path,
    monkeypatch,
) -> None:
    executable = tmp_path / "tesseract.exe"
    executable.write_bytes(b"test")
    monkeypatch.setattr(
        TesseractOCR,
        "_probe_executable",
        staticmethod(lambda _command: False),
    )

    ocr = TesseractOCR(executable_path=executable)

    assert ocr.is_available() is False


def test_tesseract_availability_configures_verified_binary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    executable = tmp_path / "tesseract.exe"
    executable.write_bytes(b"test")
    monkeypatch.setattr(
        TesseractOCR,
        "_probe_executable",
        staticmethod(lambda _command: True),
    )

    ocr = TesseractOCR(executable_path=executable)

    assert ocr.is_available() is True
    assert ocr._resolved_command == str(executable.resolve())
