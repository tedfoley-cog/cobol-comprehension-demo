"""Orchestrator: runs all analysis scripts and writes JSON to dashboard/data/.

This is the main entry point Devin calls during the live demo.
It produces all the JSON files the dashboard consumes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from analysis.parse_cobol import parse_all_programs
from analysis.parse_copybooks import parse_all_copybooks
from analysis.parse_jcl import parse_all_jcl
from analysis.build_dependency_graph import build_graph
from analysis.find_dead_code import find_dead_code
from analysis.trace_data_lineage import trace_lineage
from analysis.deep_analysis import run_deep_analysis


def generate_all(source_dir: Path, output_dir: Path) -> dict:
    """Run all analyses and write results to output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Analyzing COBOL source in: {source_dir}")
    print(f"Writing dashboard data to: {output_dir}")
    print()

    # 1. Parse all artifacts
    print("Parsing COBOL programs...")
    programs = parse_all_programs(source_dir)
    print(f"  Found {len(programs)} programs")

    print("Parsing copybooks...")
    copybooks = parse_all_copybooks(source_dir)
    print(f"  Found {len(copybooks)} copybooks")

    print("Parsing JCL jobs...")
    jcl_jobs = parse_all_jcl(source_dir)
    print(f"  Found {len(jcl_jobs)} JCL jobs")
    print()

    # 2. Program inventory
    print("Building program inventory...")
    inventory = {
        "programs": [p.to_dict() for p in programs],
        "copybooks": [c.to_dict() for c in copybooks],
        "jcl_jobs": [j.to_dict() for j in jcl_jobs],
        "summary": {
            "total_programs": len(programs),
            "total_copybooks": len(copybooks),
            "total_jcl_jobs": len(jcl_jobs),
            "total_loc": sum(p.loc for p in programs),
            "total_comment_lines": sum(p.comment_lines for p in programs),
            "avg_complexity": round(
                sum(p.complexity_score for p in programs) / max(len(programs), 1), 1
            ),
            "programs_with_cics": sum(1 for p in programs if p.cics_commands),
            "programs_batch_only": sum(1 for p in programs if not p.cics_commands),
        },
    }
    _write_json(output_dir / "inventory.json", inventory)

    # 3. Dependency graph
    print("Building dependency graph...")
    graph = build_graph(programs, copybooks, jcl_jobs)
    graph_data = graph.to_dict()
    _write_json(output_dir / "dependency_graph.json", graph_data)

    # 4. Dead code analysis
    print("Identifying dead code...")
    dead = find_dead_code(programs, copybooks, jcl_jobs)
    dead_data = dead.to_dict()
    _write_json(output_dir / "dead_code.json", dead_data)

    # 5. Data lineage
    print("Tracing data lineage...")
    lineage = trace_lineage(programs, copybooks, jcl_jobs)
    lineage_data = lineage.to_dict()
    _write_json(output_dir / "data_lineage.json", lineage_data)

    # 6. Deep analysis (field-level cross-referencing)
    print("Running deep analysis...")
    deep = run_deep_analysis(programs, copybooks)
    deep_data = deep.to_dict()
    _write_json(output_dir / "deep_analysis.json", deep_data)

    # 7. Summary report
    summary = {
        "source_directory": str(source_dir),
        "inventory": inventory["summary"],
        "dependency_graph": graph_data["summary"],
        "dead_code": dead_data["summary"],
        "data_lineage": lineage_data["summary"],
        "deep_analysis": deep_data["summary"],
    }
    _write_json(output_dir / "summary.json", summary)

    print()
    print("=" * 60)
    print("COMPREHENSION ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"  Programs analyzed:     {summary['inventory']['total_programs']}")
    print(f"  Copybooks analyzed:    {summary['inventory']['total_copybooks']}")
    print(f"  JCL jobs analyzed:     {summary['inventory']['total_jcl_jobs']}")
    print(f"  Total lines of code:   {summary['inventory']['total_loc']}")
    print(f"  Dependency edges:      {summary['dependency_graph']['total_edges']}")
    print(f"  Dead programs:         {summary['dead_code']['dead_programs']}")
    print(f"  Dead copybooks:        {summary['dead_code']['dead_copybooks']}")
    print(f"  Shared copybooks:      {summary['data_lineage']['shared_copybooks']}")
    print(f"  Data flows traced:     {summary['data_lineage']['total_flows']}")
    print(f"  Field cross-refs:      {summary['deep_analysis']['fields_crossreferenced']}")
    print(f"  Implicit connections:  {summary['deep_analysis']['implicit_connections']}")
    print(f"  REDEFINES chains:      {summary['deep_analysis']['redefines_chains']}")
    print(f"  COMMAREA flows:        {summary['deep_analysis']['commarea_flows']}")
    print(f"  High-risk fields:      {summary['deep_analysis']['high_risk_fields']}")
    print("=" * 60)
    print(f"\nDashboard data written to: {output_dir}")
    print("Open dashboard/index.html to view results.")

    return summary


def _write_json(path: Path, data: object) -> None:
    """Write JSON data to a file."""
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"  Wrote {path}")


if __name__ == "__main__":
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("carddemo-source/app")
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("dashboard/data")
    generate_all(source, output)
