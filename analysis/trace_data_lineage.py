"""Trace data lineage across programs and copybooks.

Maps the flow of data:
- Dataset → Program (via JCL DD statements)
- Program → Copybook (via COPY statements)
- Copybook → Fields (via field definitions)
- Field → Field (via shared copybook references across programs)

The key insight for the demo: a field like WS-FIELD-01 in one program
may be CUST-TAX-NUM in another, connected only by byte position in a
shared copybook. This implicit dependency is invisible without
systematic tracing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from analysis.parse_cobol import CobolProgram, parse_all_programs
from analysis.parse_copybooks import Copybook, parse_all_copybooks
from analysis.parse_jcl import JclJob, parse_all_jcl


@dataclass
class DataFlow:
    source_type: str  # "dataset", "program", "copybook", "field"
    source_name: str
    target_type: str
    target_name: str
    relationship: str  # "read_by", "written_by", "defines", "uses_field"


@dataclass
class DataLineageReport:
    flows: list[dict] = field(default_factory=list)
    shared_copybooks: list[dict] = field(default_factory=list)
    file_io_map: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "flows": self.flows,
            "shared_copybooks": self.shared_copybooks,
            "file_io_map": self.file_io_map,
            "summary": self.summary,
        }


def trace_lineage(
    programs: list[CobolProgram],
    copybooks: list[Copybook],
    jcl_jobs: list[JclJob],
) -> DataLineageReport:
    """Trace data lineage across all artifacts."""
    report = DataLineageReport()

    # 1. Map copybook usage: which programs share which copybooks
    copybook_users: dict[str, list[str]] = {}
    for prog in programs:
        for ref in prog.copy_refs:
            key = ref.upper()
            if key not in copybook_users:
                copybook_users[key] = []
            copybook_users[key].append(prog.program_id)

    # Find shared copybooks (used by 2+ programs) — this is the key data lineage insight
    for cpy_name, users in sorted(copybook_users.items()):
        if len(users) >= 2:
            report.shared_copybooks.append({
                "copybook": cpy_name,
                "used_by": users,
                "sharing_count": len(users),
            })

    # 2. Map file I/O from JCL
    dataset_readers: dict[str, list[str]] = {}
    dataset_writers: dict[str, list[str]] = {}

    for job in jcl_jobs:
        for step in job.steps:
            for dd in step.dd_statements:
                if not dd.dsn:
                    continue
                disp = (dd.disposition or "").upper()
                if disp in ("NEW", "MOD"):
                    if dd.dsn not in dataset_writers:
                        dataset_writers[dd.dsn] = []
                    dataset_writers[dd.dsn].append(step.program)
                else:
                    if dd.dsn not in dataset_readers:
                        dataset_readers[dd.dsn] = []
                    dataset_readers[dd.dsn].append(step.program)

    # Build file I/O map
    all_datasets = set(list(dataset_readers.keys()) + list(dataset_writers.keys()))
    for dsn in sorted(all_datasets):
        readers = dataset_readers.get(dsn, [])
        writers = dataset_writers.get(dsn, [])
        report.file_io_map.append({
            "dataset": dsn,
            "read_by": list(set(readers)),
            "written_by": list(set(writers)),
        })

    # 3. Build data flow edges
    for cpy_name, users in copybook_users.items():
        for user in users:
            report.flows.append({
                "source_type": "program",
                "source_name": user,
                "target_type": "copybook",
                "target_name": cpy_name,
                "relationship": "copies",
            })

    for dsn, readers in dataset_readers.items():
        for reader in readers:
            report.flows.append({
                "source_type": "dataset",
                "source_name": dsn,
                "target_type": "program",
                "target_name": reader,
                "relationship": "read_by",
            })

    for dsn, writers in dataset_writers.items():
        for writer in writers:
            report.flows.append({
                "source_type": "program",
                "source_name": writer,
                "target_type": "dataset",
                "target_name": dsn,
                "relationship": "writes",
            })

    # Summary
    report.summary = {
        "total_flows": len(report.flows),
        "shared_copybooks": len(report.shared_copybooks),
        "datasets_mapped": len(report.file_io_map),
        "programs_with_file_io": len(set(
            p for readers in dataset_readers.values() for p in readers
        ) | set(
            p for writers in dataset_writers.values() for p in writers
        )),
    }

    return report


def trace_from_source(source_dir: Path) -> DataLineageReport:
    """Parse all artifacts and trace data lineage."""
    programs = parse_all_programs(source_dir)
    copybooks = parse_all_copybooks(source_dir)
    jcl_jobs = parse_all_jcl(source_dir)
    return trace_lineage(programs, copybooks, jcl_jobs)


if __name__ == "__main__":
    import json
    import sys

    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("carddemo-source/app")
    report = trace_from_source(source)
    print(json.dumps(report.to_dict(), indent=2))
    s = report.summary
    print(
        f"\nLineage: {s['total_flows']} flows, "
        f"{s['shared_copybooks']} shared copybooks, "
        f"{s['datasets_mapped']} datasets",
        file=sys.stderr,
    )
