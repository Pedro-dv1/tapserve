"""Extract all source paragraphs and validate the official 134-section inventory."""

import hashlib
import re
from pathlib import Path
from zipfile import ZipFile

from defusedxml import ElementTree

ROOT = Path(__file__).resolve().parents[1]


def extract() -> list[tuple[int, str, str]]:
    source = next(ROOT.glob("Arquitetura*.docx"))
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with ZipFile(source) as archive:
        if archive.getinfo("word/document.xml").file_size > 5 * 1024 * 1024:
            raise ValueError("Architecture XML exceeds the 5 MiB extraction bound")
        body = ElementTree.fromstring(archive.read("word/document.xml"))
        paragraphs = [
            "".join(t.text or "" for t in p.findall(".//w:t", ns))
            for p in body.findall(".//w:body//w:p", ns)
        ]
    sections: list[tuple[int, str, str]] = []
    for paragraph in paragraphs:
        match = re.match(r"^(\d+)\. (.+)$", paragraph)
        if match and int(match[1]) == len(sections) + 1 and len(sections) < 134:
            sections.append((int(match[1]), match[2], ""))
        elif sections and paragraph.strip():
            number, title, content = sections[-1]
            sections[-1] = (number, title, content + paragraph + "\n\n")
    if [s[0] for s in sections] != list(range(1, 135)):
        raise ValueError("Official architecture must contain each section 1–134 exactly once")
    output = "# Extracted official architecture\n\n"
    output += (
        f"Source: {source.name}\nSHA256: {hashlib.sha256(source.read_bytes()).hexdigest()}\n\n"
    )
    output += "Text extraction preserves paragraph order; visual numbering and diagrams are not reconstructed. Source DOCX remains authoritative.\n\n"
    output += "".join(f"## {n}. {title}\n\n{body}" for n, title, body in sections)
    (ROOT / "docs" / "ARCHITECTURE_SOURCE.md").write_text(output, encoding="utf-8")
    return sections


if __name__ == "__main__":
    extracted = extract()
    print(f"Extracted {len(extracted)} sections; NFC extension: {len(extracted[110:])}")
