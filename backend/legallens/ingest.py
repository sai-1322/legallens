"""Load .txt / .md / .pdf files and split them into legal sections."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

SUPPORTED = {".txt", ".md", ".pdf"}
HEADING = re.compile(r"^(Section|Sec\.|Article|Rule|Regulation)\s+(\d+[A-Za-z]?)[.:]?\s*(.*)$", re.IGNORECASE)
PART_LINE = re.compile(r"^(PART|CHAPTER)\s+[IVXLC\d]+\b.*$", re.IGNORECASE)


@dataclass
class Section:
    doc: str
    kind: str      # "Section", "Article", ...
    number: str    # "9", "26A", or "preamble"
    title: str
    body: str

    @property
    def label(self) -> str:
        return "Preamble" if self.number == "preamble" else f"{self.kind.title()} {self.number}"

    @property
    def heading(self) -> str:
        return self.label if not self.title else f"{self.label}. {self.title}"


def read_file(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        return "\n".join((page.extract_text() or "") for page in PdfReader(str(path)).pages)
    return path.read_text(encoding="utf-8", errors="replace")


def split_sections(doc: str, text: str) -> list[Section]:
    """Split on lines like 'Section 9. Rent increases'. Text before the first heading is the preamble."""
    sections: list[Section] = []
    cur = Section(doc, "Section", "preamble", "", "")
    buf: list[str] = []

    def flush() -> None:
        body = " ".join(" ".join(buf).split())
        if body or cur.title:
            cur.body = body
            sections.append(cur)

    for raw in text.splitlines():
        line = raw.strip()
        if not line or PART_LINE.match(line):
            continue
        m = HEADING.match(line)
        if m:
            flush()
            buf = []
            cur = Section(doc, m.group(1).rstrip(".").title(), m.group(2), m.group(3).strip(), "")
        else:
            buf.append(line)
    flush()
    return sections


def load_sections(data_dir: Path) -> list[Section]:
    out: list[Section] = []
    if not data_dir.exists():
        return out
    for path in sorted(data_dir.iterdir()):
        if path.suffix.lower() in SUPPORTED and path.is_file():
            out.extend(split_sections(path.name, read_file(path)))
    return out
