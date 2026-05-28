"""Parse COBOL source files and extract program structure.

Extracts:
- IDENTIFICATION DIVISION program name
- COPY statement references (copybook dependencies)
- CALL targets (inter-program calls)
- WORKING-STORAGE field definitions
- PROCEDURE DIVISION paragraph/section names
- Lines of code (LOC) and complexity estimate
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CobolField:
    level: int
    name: str
    picture: str
    line_number: int
    byte_offset: int | None = None


@dataclass
class CobolProgram:
    file_path: str
    program_id: str
    loc: int
    comment_lines: int
    copy_refs: list[str] = field(default_factory=list)
    call_targets: list[str] = field(default_factory=list)
    working_storage_fields: list[CobolField] = field(default_factory=list)
    paragraphs: list[str] = field(default_factory=list)
    sections: list[str] = field(default_factory=list)
    cics_commands: list[str] = field(default_factory=list)
    complexity_score: int = 0

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "program_id": self.program_id,
            "loc": self.loc,
            "comment_lines": self.comment_lines,
            "copy_refs": self.copy_refs,
            "call_targets": self.call_targets,
            "working_storage_fields": [
                {"level": f.level, "name": f.name, "picture": f.picture, "line": f.line_number}
                for f in self.working_storage_fields
            ],
            "paragraphs": self.paragraphs,
            "sections": self.sections,
            "cics_commands": self.cics_commands,
            "complexity_score": self.complexity_score,
        }


# Patterns for COBOL parsing
RE_PROGRAM_ID = re.compile(r"PROGRAM-ID\.\s+(\S+?)[\.\s]", re.IGNORECASE)
RE_COPY = re.compile(r"\bCOPY\s+(\S+?)[\.\s]", re.IGNORECASE)
RE_CALL = re.compile(r"\bCALL\s+['\"](\S+?)['\"]", re.IGNORECASE)
RE_FIELD = re.compile(
    r"^\s+(\d{2})\s+(\S+)\s+PIC\s+(.+?)\.?\s*$",
    re.IGNORECASE,
)
RE_PARAGRAPH = re.compile(r"^       ([A-Z0-9][\w-]+)\.\s*$")
RE_SECTION = re.compile(r"^       ([A-Z0-9][\w-]+)\s+SECTION\.\s*$", re.IGNORECASE)
RE_CICS = re.compile(r"EXEC\s+CICS\s+(\w+)", re.IGNORECASE)


def _is_comment(line: str) -> bool:
    """Check if a COBOL line is a comment (col 7 = '*' or '/')."""
    return len(line) > 6 and line[6] in ("*", "/")


def _is_blank(line: str) -> bool:
    return line.strip() == ""


def parse_cobol_file(path: Path) -> CobolProgram:
    """Parse a single COBOL source file."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    program_id = ""
    copy_refs: list[str] = []
    call_targets: list[str] = []
    ws_fields: list[CobolField] = []
    paragraphs: list[str] = []
    sections: list[str] = []
    cics_commands: list[str] = []
    comment_count = 0
    code_count = 0
    in_working_storage = False
    in_procedure = False

    for i, line in enumerate(lines, 1):
        if _is_blank(line):
            continue
        if _is_comment(line):
            comment_count += 1
            continue
        code_count += 1

        upper = line.upper()

        # Track divisions
        if "WORKING-STORAGE SECTION" in upper:
            in_working_storage = True
            in_procedure = False
        elif "PROCEDURE DIVISION" in upper:
            in_working_storage = False
            in_procedure = True
        elif "LINKAGE SECTION" in upper or "LOCAL-STORAGE SECTION" in upper:
            in_working_storage = False

        # Program ID
        if not program_id:
            m = RE_PROGRAM_ID.search(line)
            if m:
                program_id = m.group(1).rstrip(".")

        # COPY references
        for m in RE_COPY.finditer(line):
            ref = m.group(1).rstrip(".")
            if ref not in copy_refs:
                copy_refs.append(ref)

        # CALL targets
        for m in RE_CALL.finditer(line):
            target = m.group(1)
            if target not in call_targets:
                call_targets.append(target)

        # Working storage fields
        if in_working_storage:
            m = RE_FIELD.match(line)
            if m:
                ws_fields.append(CobolField(
                    level=int(m.group(1)),
                    name=m.group(2),
                    picture=m.group(3).strip().rstrip("."),
                    line_number=i,
                ))

        # Paragraphs and sections in PROCEDURE DIVISION
        if in_procedure:
            m = RE_SECTION.match(line)
            if m:
                sections.append(m.group(1))
            else:
                m = RE_PARAGRAPH.match(line)
                if m:
                    name = m.group(1)
                    if name.upper() not in ("PROCEDURE", "IDENTIFICATION", "ENVIRONMENT",
                                            "DATA", "WORKING-STORAGE", "LINKAGE"):
                        paragraphs.append(name)

        # CICS commands
        for m in RE_CICS.finditer(line):
            cmd = m.group(1).upper()
            if cmd not in cics_commands:
                cics_commands.append(cmd)

    # Complexity score: weighted combination
    complexity = (
        len(call_targets) * 3
        + len(copy_refs) * 2
        + len(paragraphs)
        + len(cics_commands) * 2
        + (1 if code_count > 200 else 0) * 5
        + (1 if code_count > 500 else 0) * 5
    )

    return CobolProgram(
        file_path=str(path),
        program_id=program_id or path.stem,
        loc=code_count,
        comment_lines=comment_count,
        copy_refs=copy_refs,
        call_targets=call_targets,
        working_storage_fields=ws_fields,
        paragraphs=paragraphs,
        sections=sections,
        cics_commands=cics_commands,
        complexity_score=complexity,
    )


def parse_all_programs(source_dir: Path) -> list[CobolProgram]:
    """Parse all COBOL programs under the given directory."""
    programs: list[CobolProgram] = []
    for pattern in ("**/*.cbl", "**/*.CBL"):
        for path in sorted(source_dir.glob(pattern)):
            programs.append(parse_cobol_file(path))
    # Deduplicate by path
    seen: set[str] = set()
    unique: list[CobolProgram] = []
    for p in programs:
        if p.file_path not in seen:
            seen.add(p.file_path)
            unique.append(p)
    return unique


if __name__ == "__main__":
    import json
    import sys

    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("carddemo-source/app")
    programs = parse_all_programs(source)
    print(json.dumps([p.to_dict() for p in programs], indent=2))
    print(f"\nParsed {len(programs)} programs", file=sys.stderr)
