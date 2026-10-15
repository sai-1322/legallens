import pytest

from legallens.chunking import MAX_SECTION_WORDS, chunk_sections
from legallens.ingest import split_sections
from legallens.text import sentences, stem, tokens

DOC = """ACT TITLE

Intro paragraph before any section.

PART I - GENERAL

Section 1. Short title
This Act is called the Test Act.

Section 2A. Definitions
In this Act, "thing" means a thing.

Article 7: Odd heading style
Some text here.
"""


def test_stem_and_tokens():
    assert stem("rents") == "rent" and stem("notices") == stem("notice") == stem("noticed")
    assert stem("returning") == stem("returned") == "return"
    assert tokens("What is the landlord's notice?") == ["landlord", "notic"]  # stop-words and 's removed


def test_sentences_split():
    assert len(sentences("First one. Second one. Third.")) == 3


def test_split_sections_headings_preamble_and_part_lines():
    secs = split_sections("t.txt", DOC)
    labels = [s.label for s in secs]
    assert labels == ["Preamble", "Section 1", "Section 2A", "Article 7"]
    assert "PART I" not in " ".join(s.body for s in secs)
    assert secs[1].title == "Short title" and "Test Act" in secs[1].body
    assert secs[0].body.startswith("ACT TITLE")


def test_section_chunks_one_per_section():
    secs = split_sections("t.txt", DOC)
    ch = chunk_sections(secs, "section")
    assert len(ch) == len(secs)
    assert ch[1].sections == ["Section 1"] and ch[1].text.startswith("Section 1. Short title")


def test_long_section_is_split():
    long = "Section 1. Big\n" + " ".join(f"w{i}" for i in range(MAX_SECTION_WORDS * 2))
    ch = chunk_sections(split_sections("t.txt", long), "section")
    assert len(ch) > 1 and all(c.sections == ["Section 1"] for c in ch)


def test_window_chunks_cover_text_and_report_sections():
    secs = split_sections("t.txt", "Section 1. A\n" + " ".join(["alpha"] * 40) + "\nSection 2. B\n" + " ".join(["beta"] * 40))
    ch = chunk_sections(secs, "window", 30)
    assert len(ch) >= 3
    assert ch[0].sections[0] == "Section 1" and ch[-1].sections[0] == "Section 2"
    assert all(c.sections for c in ch)


def test_unknown_strategy():
    with pytest.raises(ValueError):
        chunk_sections([], "nope")
