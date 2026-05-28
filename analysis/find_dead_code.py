"""Identify dead code: programs and copybooks that are never referenced.

Dead code detection rules:
- A copybook is dead if no program COPYs it
- A program is dead if no other program CALLs it AND no JCL job EXECutes it
  (unless it's a CICS online program — those are invoked by transaction ID)
- A dataset is orphaned if only one program reads/writes it and that program is dead
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from analysis.parse_cobol import CobolProgram, parse_all_programs
from analysis.parse_copybooks import Copybook, parse_all_copybooks
from analysis.parse_jcl import JclJob, parse_all_jcl


@dataclass
class DeadCodeReport:
    dead_copybooks: list[dict] = field(default_factory=list)
    dead_programs: list[dict] = field(default_factory=list)
    unreferenced_datasets: list[str] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "dead_copybooks": self.dead_copybooks,
            "dead_programs": self.dead_programs,
            "unreferenced_datasets": self.unreferenced_datasets,
            "summary": self.summary,
        }


def find_dead_code(
    programs: list[CobolProgram],
    copybooks: list[Copybook],
    jcl_jobs: list[JclJob],
) -> DeadCodeReport:
    """Identify unreferenced programs and copybooks."""
    report = DeadCodeReport()

    # Build reference sets
    all_copy_refs: set[str] = set()
    all_call_targets: set[str] = set()
    all_jcl_programs: set[str] = set()

    for prog in programs:
        for ref in prog.copy_refs:
            all_copy_refs.add(ref.upper())
        for target in prog.call_targets:
            all_call_targets.add(target.upper())

    for job in jcl_jobs:
        for step in job.steps:
            all_jcl_programs.add(step.program.upper())

    # Find dead copybooks
    copybook_names = {cb.name.upper(): cb for cb in copybooks}
    for name_upper, cb in sorted(copybook_names.items()):
        if name_upper not in all_copy_refs:
            report.dead_copybooks.append({
                "name": cb.name,
                "file_path": cb.file_path,
                "field_count": len(cb.fields),
                "total_bytes": cb.total_bytes,
                "reason": "Not referenced by any COPY statement",
            })

    # Find dead programs
    program_ids = {p.program_id.upper(): p for p in programs}
    for pid_upper, prog in sorted(program_ids.items()):
        is_called = pid_upper in all_call_targets
        is_jcl_exec = pid_upper in all_jcl_programs
        has_cics = len(prog.cics_commands) > 0

        if not is_called and not is_jcl_exec and not has_cics:
            report.dead_programs.append({
                "program_id": prog.program_id,
                "file_path": prog.file_path,
                "loc": prog.loc,
                "reason": "Not called by any program, not executed by any JCL job, no CICS commands",
            })

    # Summary
    total_programs = len(programs)
    total_copybooks = len(copybooks)
    report.summary = {
        "total_programs": total_programs,
        "total_copybooks": total_copybooks,
        "dead_programs": len(report.dead_programs),
        "dead_copybooks": len(report.dead_copybooks),
        "dead_program_pct": round(len(report.dead_programs) / max(total_programs, 1) * 100, 1),
        "dead_copybook_pct": round(len(report.dead_copybooks) / max(total_copybooks, 1) * 100, 1),
    }

    return report


def find_dead_code_from_source(source_dir: Path) -> DeadCodeReport:
    """Parse all artifacts and find dead code."""
    programs = parse_all_programs(source_dir)
    copybooks = parse_all_copybooks(source_dir)
    jcl_jobs = parse_all_jcl(source_dir)
    return find_dead_code(programs, copybooks, jcl_jobs)


if __name__ == "__main__":
    import json
    import sys

    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("carddemo-source/app")
    report = find_dead_code_from_source(source)
    print(json.dumps(report.to_dict(), indent=2))
    s = report.summary
    print(f"\nDead code: {s['dead_programs']} programs, {s['dead_copybooks']} copybooks", file=sys.stderr)
