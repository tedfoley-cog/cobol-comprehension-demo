"""Parse JCL files and extract job step chains.

Extracts:
- Job name and class
- EXEC PGM= references (programs executed)
- DD DSN= references (datasets read/written)
- Step sequence for batch flow visualization
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DDStatement:
    name: str
    dsn: str | None
    disposition: str | None


@dataclass
class JclStep:
    step_name: str
    program: str
    dd_statements: list[DDStatement] = field(default_factory=list)


@dataclass
class JclJob:
    file_path: str
    job_name: str
    steps: list[JclStep] = field(default_factory=list)
    programs_referenced: list[str] = field(default_factory=list)
    datasets_referenced: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "job_name": self.job_name,
            "steps": [
                {
                    "step_name": s.step_name,
                    "program": s.program,
                    "dd_statements": [
                        {"name": d.name, "dsn": d.dsn, "disposition": d.disposition}
                        for d in s.dd_statements
                    ],
                }
                for s in self.steps
            ],
            "programs_referenced": self.programs_referenced,
            "datasets_referenced": self.datasets_referenced,
        }


RE_JOB = re.compile(r"^//(\w+)\s+JOB\s", re.IGNORECASE)
RE_EXEC = re.compile(r"^//(\w+)\s+EXEC\s+PGM=(\w+)", re.IGNORECASE)
RE_DD = re.compile(r"^//(\w+)\s+DD\s", re.IGNORECASE)
RE_DSN = re.compile(r"DSN=([^\s,]+)", re.IGNORECASE)
RE_DISP = re.compile(r"DISP=\(?([^\s,)]+)", re.IGNORECASE)
RE_CONTINUATION_DSN = re.compile(r"^\s*//\s+DSN=([^\s,]+)", re.IGNORECASE)


def parse_jcl_file(path: Path) -> JclJob:
    """Parse a single JCL file."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    job_name = path.stem
    steps: list[JclStep] = []
    current_step: JclStep | None = None
    programs: list[str] = []
    datasets: list[str] = []

    for line in lines:
        # Skip comments
        if line.startswith("//*"):
            continue

        # Job card
        m = RE_JOB.match(line)
        if m:
            job_name = m.group(1)
            continue

        # EXEC PGM=
        m = RE_EXEC.match(line)
        if m:
            current_step = JclStep(step_name=m.group(1), program=m.group(2))
            steps.append(current_step)
            pgm = m.group(2)
            if pgm not in programs:
                programs.append(pgm)
            continue

        # DD statement
        m = RE_DD.match(line)
        if m and current_step is not None:
            dd_name = m.group(1)
            dsn_match = RE_DSN.search(line)
            disp_match = RE_DISP.search(line)
            dsn = dsn_match.group(1).rstrip(",") if dsn_match else None
            disp = disp_match.group(1) if disp_match else None
            current_step.dd_statements.append(DDStatement(
                name=dd_name, dsn=dsn, disposition=disp,
            ))
            if dsn and dsn not in datasets:
                datasets.append(dsn)
            continue

        # Continuation line with DSN
        if current_step is not None and "DSN=" in line.upper():
            dsn_match = RE_DSN.search(line)
            if dsn_match:
                dsn = dsn_match.group(1).rstrip(",")
                if current_step.dd_statements:
                    last_dd = current_step.dd_statements[-1]
                    if last_dd.dsn is None:
                        last_dd.dsn = dsn
                if dsn not in datasets:
                    datasets.append(dsn)

    return JclJob(
        file_path=str(path),
        job_name=job_name,
        steps=steps,
        programs_referenced=programs,
        datasets_referenced=datasets,
    )


def parse_all_jcl(source_dir: Path) -> list[JclJob]:
    """Parse all JCL files under the given directory."""
    jobs: list[JclJob] = []
    for pattern in ("**/*.jcl", "**/*.JCL"):
        for path in sorted(source_dir.glob(pattern)):
            jobs.append(parse_jcl_file(path))
    seen: set[str] = set()
    unique: list[JclJob] = []
    for j in jobs:
        if j.file_path not in seen:
            seen.add(j.file_path)
            unique.append(j)
    return unique


if __name__ == "__main__":
    import json
    import sys

    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("carddemo-source/app")
    jobs = parse_all_jcl(source)
    print(json.dumps([j.to_dict() for j in jobs], indent=2))
    print(f"\nParsed {len(jobs)} JCL jobs", file=sys.stderr)
