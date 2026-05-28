"""Parse COBOL copybook files and extract field definitions.

Extracts:
- Field hierarchy (level numbers 01-49, 66, 77, 88)
- PIC clauses with byte sizes
- REDEFINES relationships
- 88-level condition names
- Estimated byte offsets for data lineage tracing
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CopybookField:
    level: int
    name: str
    picture: str | None
    byte_size: int
    byte_offset: int
    redefines: str | None = None
    is_condition: bool = False
    condition_values: list[str] = field(default_factory=list)


@dataclass
class Copybook:
    file_path: str
    name: str
    fields: list[CopybookField] = field(default_factory=list)
    total_bytes: int = 0

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "name": self.name,
            "total_bytes": self.total_bytes,
            "fields": [
                {
                    "level": f.level,
                    "name": f.name,
                    "picture": f.picture,
                    "byte_size": f.byte_size,
                    "byte_offset": f.byte_offset,
                    "redefines": f.redefines,
                    "is_condition": f.is_condition,
                }
                for f in self.fields
            ],
        }


RE_FIELD_LINE = re.compile(
    r"^\s+(\d{2})\s+(\S+)(.*?)\.?\s*$", re.IGNORECASE
)
RE_PIC = re.compile(r"PIC(?:TURE)?\s+IS\s+(\S+)|PIC(?:TURE)?\s+(\S+)", re.IGNORECASE)
RE_REDEFINES = re.compile(r"REDEFINES\s+(\S+)", re.IGNORECASE)
RE_VALUE = re.compile(r"VALUE\s+(.+?)\.?\s*$", re.IGNORECASE)


def _estimate_pic_size(pic: str) -> int:
    """Estimate byte size from a PIC clause.

    The input may include trailing USAGE modifiers (COMP, COMP-3) from the
    field definition line. We strip non-PIC keywords like VALUE, JUSTIFIED,
    etc. before counting characters.
    """
    pic = pic.upper().rstrip(".")

    # Strip everything after common non-PIC keywords
    for kw in ("VALUE", "JUSTIFIED", "JUST", "BLANK", "OCCURS", "SYNC"):
        idx = pic.find(kw)
        if idx > 0:
            pic = pic[:idx]

    # COMP / COMP-3 modifiers change storage
    if "COMP-3" in pic or "PACKED" in pic:
        digits = sum(int(m) for m in re.findall(r"9\((\d+)\)", pic))
        digits += pic.count("9") - len(re.findall(r"9\(\d+\)", pic))
        return (digits + 2) // 2

    if "COMP" in pic:
        digits = sum(int(m) for m in re.findall(r"9\((\d+)\)", pic))
        digits += pic.count("9") - len(re.findall(r"9\(\d+\)", pic))
        if digits <= 4:
            return 2
        if digits <= 9:
            return 4
        return 8

    # Standard display format
    size = 0
    # Expand X(nn), 9(nn), A(nn) notation
    for m in re.finditer(r"[XA9]\((\d+)\)", pic):
        size += int(m.group(1))
    # Count standalone X, 9, A characters not in X(nn) notation
    stripped = re.sub(r"[XA9]\(\d+\)", "", pic)
    size += stripped.count("X") + stripped.count("9") + stripped.count("A")
    # V (implied decimal) doesn't add bytes
    # S (sign) adds 0 bytes in display (embedded)
    if size == 0:
        size = 1
    return size


def parse_copybook_file(path: Path) -> Copybook:
    """Parse a single copybook file."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    fields: list[CopybookField] = []
    current_offset = 0
    group_offsets: dict[int, int] = {}

    for line in lines:
        # Skip comments
        if len(line) > 6 and line[6] in ("*", "/"):
            continue

        m = RE_FIELD_LINE.match(line)
        if not m:
            continue

        level = int(m.group(1))
        name = m.group(2).rstrip(".")
        rest = m.group(3) if m.group(3) else ""

        # 88-level condition names
        if level == 88:
            value_match = RE_VALUE.search(rest)
            values = [value_match.group(1).strip()] if value_match else []
            fields.append(CopybookField(
                level=88, name=name, picture=None,
                byte_size=0, byte_offset=current_offset,
                is_condition=True, condition_values=values,
            ))
            continue

        # REDEFINES
        redefines = None
        redef_match = RE_REDEFINES.search(rest)
        if redef_match:
            redefines = redef_match.group(1).rstrip(".")

        # PIC clause
        pic_match = RE_PIC.search(rest)
        picture = None
        byte_size = 0
        if pic_match:
            picture = (pic_match.group(1) or pic_match.group(2)).rstrip(".")
            # Pass USAGE modifiers (COMP/COMP-3) after the PIC match
            after_pic = rest[pic_match.end():]
            byte_size = _estimate_pic_size(picture + " " + after_pic)

        # Reset offset for new 01-level
        if level == 1 or level == 77:
            current_offset = 0

        # Track group offsets for hierarchy
        if level <= 49:
            group_offsets[level] = current_offset

        offset = current_offset

        # REDEFINES doesn't advance the offset
        if redefines is None and byte_size > 0:
            current_offset += byte_size

        fields.append(CopybookField(
            level=level, name=name, picture=picture,
            byte_size=byte_size, byte_offset=offset,
            redefines=redefines,
        ))

    total = max((f.byte_offset + f.byte_size for f in fields if not f.is_condition), default=0)

    return Copybook(
        file_path=str(path),
        name=path.stem,
        fields=fields,
        total_bytes=total,
    )


def parse_all_copybooks(source_dir: Path) -> list[Copybook]:
    """Parse all copybook files under the given directory."""
    copybooks: list[Copybook] = []
    for pattern in ("**/*.cpy", "**/*.CPY"):
        for path in sorted(source_dir.glob(pattern)):
            copybooks.append(parse_copybook_file(path))
    seen: set[str] = set()
    unique: list[Copybook] = []
    for c in copybooks:
        if c.file_path not in seen:
            seen.add(c.file_path)
            unique.append(c)
    return unique


if __name__ == "__main__":
    import json
    import sys

    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("carddemo-source/app")
    copybooks = parse_all_copybooks(source)
    print(json.dumps([c.to_dict() for c in copybooks], indent=2))
    print(f"\nParsed {len(copybooks)} copybooks", file=sys.stderr)
