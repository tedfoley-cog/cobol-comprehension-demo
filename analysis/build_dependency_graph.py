"""Build program-to-copybook-to-program dependency graph.

Creates a graph structure showing:
- Which programs COPY which copybooks
- Which programs CALL which other programs
- Which JCL jobs execute which programs
- Bidirectional edges for full dependency tracing
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from analysis.parse_cobol import CobolProgram, parse_all_programs
from analysis.parse_copybooks import Copybook, parse_all_copybooks
from analysis.parse_jcl import JclJob, parse_all_jcl


@dataclass
class DependencyNode:
    id: str
    type: str  # "program", "copybook", "jcl_job", "dataset"
    label: str
    metadata: dict = field(default_factory=dict)


@dataclass
class DependencyEdge:
    source: str
    target: str
    type: str  # "copies", "calls", "executes", "reads", "writes"


@dataclass
class DependencyGraph:
    nodes: list[DependencyNode] = field(default_factory=list)
    edges: list[DependencyEdge] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "nodes": [
                {"id": n.id, "type": n.type, "label": n.label, "metadata": n.metadata}
                for n in self.nodes
            ],
            "edges": [
                {"source": e.source, "target": e.target, "type": e.type}
                for e in self.edges
            ],
            "summary": {
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "programs": sum(1 for n in self.nodes if n.type == "program"),
                "copybooks": sum(1 for n in self.nodes if n.type == "copybook"),
                "jcl_jobs": sum(1 for n in self.nodes if n.type == "jcl_job"),
                "datasets": sum(1 for n in self.nodes if n.type == "dataset"),
            },
        }


def build_graph(
    programs: list[CobolProgram],
    copybooks: list[Copybook],
    jcl_jobs: list[JclJob],
) -> DependencyGraph:
    """Build a dependency graph from parsed artifacts."""
    graph = DependencyGraph()
    node_ids: set[str] = set()

    def add_node(node_id: str, node_type: str, label: str, **meta: object) -> None:
        if node_id not in node_ids:
            node_ids.add(node_id)
            graph.nodes.append(DependencyNode(
                id=node_id, type=node_type, label=label, metadata=dict(meta),
            ))

    # Add program nodes
    for prog in programs:
        pid = f"pgm:{prog.program_id}"
        add_node(pid, "program", prog.program_id,
                 loc=prog.loc, complexity=prog.complexity_score,
                 cics_commands=prog.cics_commands)

    # Add copybook nodes
    for cb in copybooks:
        cid = f"cpy:{cb.name}"
        add_node(cid, "copybook", cb.name,
                 total_bytes=cb.total_bytes, field_count=len(cb.fields))

    # Add program → copybook edges
    for prog in programs:
        pid = f"pgm:{prog.program_id}"
        for ref in prog.copy_refs:
            cid = f"cpy:{ref}"
            # Add copybook node even if we didn't parse it (e.g., DFHAID, DFHBMSCA)
            add_node(cid, "copybook", ref)
            graph.edges.append(DependencyEdge(source=pid, target=cid, type="copies"))

    # Add program → program CALL edges
    for prog in programs:
        pid = f"pgm:{prog.program_id}"
        for target in prog.call_targets:
            tid = f"pgm:{target}"
            add_node(tid, "program", target)
            graph.edges.append(DependencyEdge(source=pid, target=tid, type="calls"))

    # Add JCL job nodes and edges
    for job in jcl_jobs:
        jid = f"jcl:{job.job_name}"
        add_node(jid, "jcl_job", job.job_name,
                 step_count=len(job.steps))

        for step in job.steps:
            pgm_id = f"pgm:{step.program}"
            add_node(pgm_id, "program", step.program)
            graph.edges.append(DependencyEdge(source=jid, target=pgm_id, type="executes"))

            for dd in step.dd_statements:
                if dd.dsn:
                    dsn_id = f"dsn:{dd.dsn}"
                    add_node(dsn_id, "dataset", dd.dsn)
                    disp = (dd.disposition or "").upper()
                    if disp in ("NEW", "MOD"):
                        graph.edges.append(DependencyEdge(
                            source=pgm_id, target=dsn_id, type="writes",
                        ))
                    else:
                        graph.edges.append(DependencyEdge(
                            source=pgm_id, target=dsn_id, type="reads",
                        ))

    return graph


def build_from_source(source_dir: Path) -> DependencyGraph:
    """Parse all artifacts and build a dependency graph."""
    programs = parse_all_programs(source_dir)
    copybooks = parse_all_copybooks(source_dir)
    jcl_jobs = parse_all_jcl(source_dir)
    return build_graph(programs, copybooks, jcl_jobs)


if __name__ == "__main__":
    import json
    import sys

    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("carddemo-source/app")
    graph = build_from_source(source)
    print(json.dumps(graph.to_dict(), indent=2))
    summary = graph.to_dict()["summary"]
    print(f"\nGraph: {summary}", file=sys.stderr)
