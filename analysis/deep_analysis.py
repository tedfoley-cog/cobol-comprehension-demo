"""Deep analysis: field-level cross-referencing and implicit dependency detection.

This is the "wow" module — it finds the connections that are invisible without
systematic tracing:

1. Field-level cross-reference: which programs reference which specific fields
   from each shared copybook, with byte offsets
2. Implicit field connections: fields in different copybooks that occupy the
   same byte range when passed through COMMAREA or record buffers
3. REDEFINES chain analysis: overlapping memory layouts
4. Program-to-program data flow: tracing COMMAREA fields through XCTL/LINK chains
5. Impact analysis: if you change field X, which programs break
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from analysis.parse_cobol import CobolProgram, parse_all_programs
from analysis.parse_copybooks import Copybook, CopybookField, parse_all_copybooks


@dataclass
class FieldReference:
    program_id: str
    field_name: str
    copybook: str
    line_numbers: list[int]
    usage_type: str  # "read", "write", "both", "condition"
    context: str  # snippet of the line


@dataclass
class ImplicitConnection:
    """Two fields that are semantically connected through shared memory layout."""
    copybook_a: str
    field_a: str
    offset_a: int
    size_a: int
    pic_a: str
    copybook_b: str
    field_b: str
    offset_b: int
    size_b: int
    pic_b: str
    connection_type: str  # "same_offset_same_copybook", "commarea_passthrough", "record_overlay"
    programs_affected: list[str]


@dataclass
class RedefinesChain:
    copybook: str
    base_field: str
    base_offset: int
    base_size: int
    base_pic: str | None
    overlays: list[dict]  # [{name, pic, size, offset}]
    programs_using: list[str]


@dataclass
class CriticalPath:
    """A data flow path where a field change would cascade."""
    field_name: str
    copybook: str
    byte_offset: int
    byte_size: int
    programs_affected: list[str]
    downstream_fields: list[dict]  # fields in other copybooks at same offset
    risk_level: str  # "high", "medium", "low"


@dataclass
class DeepAnalysisReport:
    field_crossref: list[dict] = field(default_factory=list)
    implicit_connections: list[dict] = field(default_factory=list)
    redefines_chains: list[dict] = field(default_factory=list)
    critical_paths: list[dict] = field(default_factory=list)
    commarea_flows: list[dict] = field(default_factory=list)
    program_coupling: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "field_crossref": self.field_crossref,
            "implicit_connections": self.implicit_connections,
            "redefines_chains": self.redefines_chains,
            "critical_paths": self.critical_paths,
            "commarea_flows": self.commarea_flows,
            "program_coupling": self.program_coupling,
            "summary": self.summary,
        }


def _scan_field_references(
    program: CobolProgram, copybook_fields: dict[str, list[CopybookField]],
) -> list[FieldReference]:
    """Scan a program's source for references to copybook-defined fields."""
    refs: list[FieldReference] = []
    source_path = Path(program.file_path)
    if not source_path.exists():
        return refs

    text = source_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    for cpy_name in program.copy_refs:
        cpy_upper = cpy_name.upper()
        fields = copybook_fields.get(cpy_upper, [])
        for fld in fields:
            if fld.is_condition or fld.byte_size == 0:
                continue
            if fld.name.upper() == "FILLER":
                continue
            pattern = re.compile(r"\b" + re.escape(fld.name) + r"\b", re.IGNORECASE)
            matched_lines: list[int] = []
            contexts: list[str] = []
            usage = "read"

            for i, line in enumerate(lines, 1):
                if len(line) > 6 and line[6] in ("*", "/"):
                    continue
                if pattern.search(line):
                    matched_lines.append(i)
                    stripped = line.strip()[:120]
                    contexts.append(stripped)
                    upper_line = line.upper()
                    if "MOVE" in upper_line and f"TO {fld.name.upper()}" in upper_line.replace("  ", " "):
                        usage = "write"
                    elif "MOVE" in upper_line and fld.name.upper() in upper_line.split("TO")[0] if "TO" in upper_line else False:
                        if usage != "write":
                            usage = "read"

            if matched_lines:
                if usage == "read" and any("MOVE" in c.upper() and f"TO {fld.name.upper()}" in c.upper().replace("  ", " ") for c in contexts):
                    usage = "write"
                if len(matched_lines) > 1:
                    has_read = any(fld.name.upper() in c.upper().split("TO")[0] for c in contexts if "MOVE" in c.upper() and "TO" in c.upper())
                    has_write = any(f"TO {fld.name.upper()}" in c.upper().replace("  ", " ") for c in contexts if "MOVE" in c.upper())
                    if has_read and has_write:
                        usage = "both"

                refs.append(FieldReference(
                    program_id=program.program_id,
                    field_name=fld.name,
                    copybook=cpy_upper,
                    line_numbers=matched_lines[:10],
                    usage_type=usage,
                    context=contexts[0] if contexts else "",
                ))
    return refs


def _find_redefines_chains(copybooks: list[Copybook]) -> list[RedefinesChain]:
    """Find REDEFINES chains in copybooks."""
    chains: list[RedefinesChain] = []
    for cpy in copybooks:
        base_fields: dict[str, CopybookField] = {}
        for fld in cpy.fields:
            if fld.redefines:
                base_name = fld.redefines.upper()
                if base_name not in base_fields:
                    for bf in cpy.fields:
                        if bf.name.upper() == base_name:
                            base_fields[base_name] = bf
                            break
            else:
                base_fields[fld.name.upper()] = fld

        redef_groups: dict[str, list[CopybookField]] = {}
        for fld in cpy.fields:
            if fld.redefines:
                key = fld.redefines.upper()
                if key not in redef_groups:
                    redef_groups[key] = []
                redef_groups[key].append(fld)

        for base_name, overlays in redef_groups.items():
            base = base_fields.get(base_name)
            if not base:
                continue
            chains.append(RedefinesChain(
                copybook=cpy.name,
                base_field=base.name,
                base_offset=base.byte_offset,
                base_size=base.byte_size,
                base_pic=base.picture,
                overlays=[
                    {"name": o.name, "pic": o.picture, "size": o.byte_size, "offset": o.byte_offset}
                    for o in overlays
                ],
                programs_using=[],
            ))
    return chains


def _find_commarea_flows(programs: list[CobolProgram]) -> list[dict]:
    """Track COMMAREA-based data flow between programs via XCTL/LINK.

    Most CardDemo programs use dynamic dispatch: XCTL PROGRAM(CDEMO-TO-PROGRAM)
    where CDEMO-TO-PROGRAM is a variable set via MOVE. We detect both literal
    and variable-based targets.
    """
    flows: list[dict] = []
    prog_ids = {p.program_id.upper() for p in programs}

    for prog in programs:
        source_path = Path(prog.file_path)
        if not source_path.exists():
            continue
        text = source_path.read_text(encoding="utf-8", errors="replace")
        upper_text = text.upper()

        has_commarea = "COMMAREA" in upper_text or "DFHCOMMAREA" in upper_text
        if not has_commarea:
            continue

        targets: list[tuple[str, str, str]] = []  # (target, mechanism, target_type)

        # Literal targets: PROGRAM('COTRN01C')
        for m in re.finditer(r"EXEC\s+CICS\s+(XCTL|LINK).*?PROGRAM\s*\(\s*['\"]([A-Z0-9]+)['\"]\s*\)", upper_text, re.DOTALL):
            targets.append((m.group(2), m.group(1), "literal"))

        # Variable targets: PROGRAM(CDEMO-TO-PROGRAM)
        for m in re.finditer(r"EXEC\s+CICS\s+(XCTL|LINK).*?PROGRAM\s*\(\s*([A-Z0-9][-A-Z0-9]+)\s*\)", upper_text, re.DOTALL):
            var_name = m.group(2)
            if var_name in prog_ids:
                targets.append((var_name, m.group(1), "literal"))
                continue
            # Find what values are MOVEd into this variable
            for mv in re.finditer(
                r"MOVE\s+['\"]?([A-Z0-9]+)['\"]?\s+TO\s+" + re.escape(var_name),
                upper_text,
            ):
                val = mv.group(1)
                if val in prog_ids or len(val) <= 8:
                    targets.append((val, m.group(1), "dynamic"))

        # Also check for XCTL without EXEC CICS prefix (some programs use shorthand)
        for m in re.finditer(r"XCTL\s+PROGRAM\s*\(\s*([A-Z0-9][-A-Z0-9()]+)\s*\)", upper_text):
            target = m.group(1).strip("'\"")
            if target in prog_ids:
                targets.append((target, "XCTL", "literal"))

        seen: set[str] = set()
        for target, mechanism, target_type in targets:
            key = f"{target}:{mechanism}"
            if key in seen:
                continue
            seen.add(key)
            flows.append({
                "from_program": prog.program_id,
                "to_program": target,
                "mechanism": mechanism,
                "target_type": target_type,
                "passes_commarea": True,
            })
    return flows


def _calculate_coupling(
    programs: list[CobolProgram],
    shared_copybooks: dict[str, list[str]],
) -> list[dict]:
    """Calculate coupling scores between program pairs based on shared data."""
    pair_scores: dict[tuple[str, str], dict] = {}

    for cpy_name, users in shared_copybooks.items():
        for i, p1 in enumerate(users):
            for p2 in users[i + 1:]:
                key = tuple(sorted([p1, p2]))
                if key not in pair_scores:
                    pair_scores[key] = {
                        "program_a": key[0],
                        "program_b": key[1],
                        "shared_copybooks": [],
                        "coupling_score": 0,
                    }
                pair_scores[key]["shared_copybooks"].append(cpy_name)
                pair_scores[key]["coupling_score"] += 1

    results = sorted(pair_scores.values(), key=lambda x: x["coupling_score"], reverse=True)
    return results[:50]


def run_deep_analysis(
    programs: list[CobolProgram],
    copybooks: list[Copybook],
) -> DeepAnalysisReport:
    """Run the deep analysis phase."""
    report = DeepAnalysisReport()

    # Build copybook field lookup
    cpy_field_map: dict[str, list[CopybookField]] = {}
    cpy_lookup: dict[str, Copybook] = {}
    for cpy in copybooks:
        cpy_field_map[cpy.name.upper()] = cpy.fields
        cpy_lookup[cpy.name.upper()] = cpy

    # Build copybook users map
    shared_copybooks: dict[str, list[str]] = {}
    for prog in programs:
        for ref in prog.copy_refs:
            key = ref.upper()
            if key not in shared_copybooks:
                shared_copybooks[key] = []
            shared_copybooks[key].append(prog.program_id)

    # 1. Field-level cross-reference
    print("  Scanning field-level references across all programs...")
    all_refs: list[FieldReference] = []
    for prog in programs:
        refs = _scan_field_references(prog, cpy_field_map)
        all_refs.extend(refs)

    # Group by copybook.field for the crossref view (deduplicated per program)
    field_xref: dict[str, dict] = {}
    for ref in all_refs:
        key = f"{ref.copybook}.{ref.field_name}"
        if key not in field_xref:
            fld_info = None
            for f in cpy_field_map.get(ref.copybook, []):
                if f.name.upper() == ref.field_name.upper():
                    fld_info = f
                    break
            field_xref[key] = {
                "copybook": ref.copybook,
                "field": ref.field_name,
                "byte_offset": fld_info.byte_offset if fld_info else -1,
                "byte_size": fld_info.byte_size if fld_info else 0,
                "picture": fld_info.picture if fld_info else None,
                "referenced_by": [],
                "_seen_programs": set(),
            }
        if ref.program_id not in field_xref[key]["_seen_programs"]:
            field_xref[key]["_seen_programs"].add(ref.program_id)
            field_xref[key]["referenced_by"].append({
                "program": ref.program_id,
                "usage": ref.usage_type,
                "line_count": len(ref.line_numbers),
                "sample_line": ref.context[:100],
            })

    # Remove internal tracking key and filter to fields used by 2+ distinct programs
    for v in field_xref.values():
        del v["_seen_programs"]

    report.field_crossref = sorted(
        [v for v in field_xref.values() if len(v["referenced_by"]) >= 2],
        key=lambda x: len(x["referenced_by"]),
        reverse=True,
    )

    # 2. Implicit field connections across copybooks
    print("  Detecting implicit field connections via byte-offset matching...")
    all_entity_fields: dict[str, list[tuple[str, CopybookField]]] = {}
    entity_copybooks = {}
    for cpy in copybooks:
        for fld in cpy.fields:
            if fld.level == 1 or fld.is_condition or fld.byte_size == 0:
                continue
            if fld.name.upper() == "FILLER":
                continue
            pic_key = fld.picture.upper().strip() if fld.picture else ""
            if not pic_key:
                continue
            if pic_key not in all_entity_fields:
                all_entity_fields[pic_key] = []
            all_entity_fields[pic_key].append((cpy.name, fld))
            entity_copybooks[cpy.name.upper()] = cpy

    connections: list[dict] = []
    seen_pairs: set[str] = set()
    for pic_key, field_list in all_entity_fields.items():
        if len(field_list) < 2:
            continue
        for i, (cpy_a, fld_a) in enumerate(field_list):
            for cpy_b, fld_b in field_list[i + 1:]:
                if cpy_a == cpy_b:
                    continue
                pair_key = f"{cpy_a}.{fld_a.name}:{cpy_b}.{fld_b.name}"
                rev_key = f"{cpy_b}.{fld_b.name}:{cpy_a}.{fld_a.name}"
                if pair_key in seen_pairs or rev_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                if fld_a.byte_size == fld_b.byte_size and fld_a.byte_size > 0:
                    progs_a = set(shared_copybooks.get(cpy_a.upper(), []))
                    progs_b = set(shared_copybooks.get(cpy_b.upper(), []))
                    affected = sorted(progs_a | progs_b)

                    connections.append({
                        "copybook_a": cpy_a,
                        "field_a": fld_a.name,
                        "offset_a": fld_a.byte_offset,
                        "size_a": fld_a.byte_size,
                        "pic_a": fld_a.picture,
                        "copybook_b": cpy_b,
                        "field_b": fld_b.name,
                        "offset_b": fld_b.byte_offset,
                        "size_b": fld_b.byte_size,
                        "pic_b": fld_b.picture,
                        "connection_type": "same_pic_same_size",
                        "programs_affected": affected,
                    })

    report.implicit_connections = sorted(
        connections,
        key=lambda x: len(x["programs_affected"]),
        reverse=True,
    )[:100]

    # 3. REDEFINES chains
    print("  Analyzing REDEFINES overlay chains...")
    chains = _find_redefines_chains(copybooks)
    for chain in chains:
        users = shared_copybooks.get(chain.copybook.upper(), [])
        chain.programs_using = users
    report.redefines_chains = [
        {
            "copybook": c.copybook,
            "base_field": c.base_field,
            "base_offset": c.base_offset,
            "base_size": c.base_size,
            "base_pic": c.base_pic,
            "overlays": c.overlays,
            "programs_using": c.programs_using,
        }
        for c in chains
    ]

    # 4. COMMAREA flows
    print("  Tracing COMMAREA data flows between programs...")
    report.commarea_flows = _find_commarea_flows(programs)

    # 5. Program coupling
    print("  Calculating program coupling scores...")
    report.program_coupling = _calculate_coupling(programs, shared_copybooks)

    # 6. Critical paths
    print("  Identifying critical data paths (high-impact change points)...")
    for xref in report.field_crossref[:30]:
        prog_count = len(xref["referenced_by"])
        writers = [r for r in xref["referenced_by"] if r["usage"] in ("write", "both")]
        risk = "high" if prog_count >= 10 else "medium" if prog_count >= 5 else "low"

        downstream = [
            c for c in report.implicit_connections
            if c["field_a"] == xref["field"] or c["field_b"] == xref["field"]
        ]

        report.critical_paths.append({
            "field": xref["field"],
            "copybook": xref["copybook"],
            "byte_offset": xref["byte_offset"],
            "byte_size": xref["byte_size"],
            "picture": xref["picture"],
            "programs_affected": prog_count,
            "writers": [w["program"] for w in writers],
            "downstream_connections": len(downstream),
            "risk_level": risk,
        })

    report.critical_paths.sort(key=lambda x: x["programs_affected"], reverse=True)

    # Summary
    report.summary = {
        "fields_crossreferenced": len(report.field_crossref),
        "total_field_references": len(all_refs),
        "implicit_connections": len(report.implicit_connections),
        "redefines_chains": len(report.redefines_chains),
        "commarea_flows": len(report.commarea_flows),
        "high_risk_fields": sum(1 for c in report.critical_paths if c["risk_level"] == "high"),
        "medium_risk_fields": sum(1 for c in report.critical_paths if c["risk_level"] == "medium"),
        "most_coupled_pair": (
            f"{report.program_coupling[0]['program_a']} <-> {report.program_coupling[0]['program_b']}"
            if report.program_coupling else "none"
        ),
        "max_coupling_score": report.program_coupling[0]["coupling_score"] if report.program_coupling else 0,
    }

    return report


def deep_analysis_from_source(source_dir: Path) -> DeepAnalysisReport:
    """Parse all artifacts and run deep analysis."""
    programs = parse_all_programs(source_dir)
    copybooks = parse_all_copybooks(source_dir)
    return run_deep_analysis(programs, copybooks)


if __name__ == "__main__":
    import json
    import sys

    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("carddemo-source/app")
    report = deep_analysis_from_source(source)
    print(json.dumps(report.to_dict(), indent=2))
    s = report.summary
    print(
        f"\nDeep analysis: {s['fields_crossreferenced']} shared fields, "
        f"{s['implicit_connections']} implicit connections, "
        f"{s['redefines_chains']} REDEFINES chains, "
        f"{s['commarea_flows']} COMMAREA flows",
        file=sys.stderr,
    )
