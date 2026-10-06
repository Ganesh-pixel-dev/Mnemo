import pytest

from ingestion import IngestionError, chunk_text, extract_text
from tests.conftest import make_pdf


def test_chunks_have_requested_size_and_overlap():
    text = " ".join(f"w{i}" for i in range(700))
    chunks = chunk_text(text, size=300, overlap=50)
    assert [len(c.split()) for c in chunks] == [300, 300, 200]
    assert chunks[0].split()[-50:] == chunks[1].split()[:50]
    assert chunks[1].split()[-50:] == chunks[2].split()[:50]


def test_every_word_lands_in_some_chunk():
    words = [f"w{i}" for i in range(1234)]
    covered = set()
    for chunk in chunk_text(" ".join(words), 300, 50):
        covered.update(chunk.split())
    assert covered == set(words)


def test_short_text_is_one_chunk():
    assert chunk_text("just a few words", 300, 50) == ["just a few words"]


def test_empty_text_has_no_chunks():
    assert chunk_text("   \n ") == []


def test_exact_size_is_one_chunk():
    assert len(chunk_text(" ".join(["x"] * 300), 300, 50)) == 1


@pytest.mark.parametrize("size,overlap", [(10, 10), (10, 20), (0, 0), (10, -1)])
def test_bad_sizes_are_rejected(size, overlap):
    with pytest.raises(ValueError):
        chunk_text("a b c", size, overlap)


def test_extract_text_from_pdf(tmp_path):
    path = tmp_path / "a.pdf"
    path.write_bytes(make_pdf("Photosynthesis converts light energy into chemical energy stored in glucose. " * 3))
    assert "Photosynthesis converts light energy" in extract_text(path)


def test_pdf_without_text_gets_a_clear_message(tmp_path):
    path = tmp_path / "scan.pdf"
    path.write_bytes(make_pdf(""))
    with pytest.raises(IngestionError, match="OCR"):
        extract_text(path)


def test_garbage_pdf_gets_a_clear_message(tmp_path):
    path = tmp_path / "bad.pdf"
    path.write_bytes(b"%PDF-1.4 this is not really a pdf")
    with pytest.raises(IngestionError, match="Couldn't read"):
        extract_text(path)


def test_non_utf8_text_file(tmp_path):
    path = tmp_path / "a.txt"
    path.write_bytes(b"\xff\xfe\x00bad bytes \xe9" * 5)
    with pytest.raises(IngestionError, match="UTF-8"):
        extract_text(path)
