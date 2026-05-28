/**
 * COBOL Comprehension Dashboard
 */
(function () {
  "use strict";

  const DATA_DIR = "data";
  let allPrograms = [];
  let allDeep = null;

  async function init() {
    try {
      const summary = await loadJSON("summary.json");
      if (!summary) return;

      document.getElementById("loading-state").style.display = "none";
      document.getElementById("dashboard").style.display = "block";

      renderSummaryCards(summary);
      setupTabs();
      setupSubTabs();

      const [inventory, depGraph, deadCode, lineage, deep] = await Promise.all([
        loadJSON("inventory.json"),
        loadJSON("dependency_graph.json"),
        loadJSON("dead_code.json"),
        loadJSON("data_lineage.json"),
        loadJSON("deep_analysis.json"),
      ]);

      if (inventory) {
        allPrograms = inventory.programs || [];
        renderProgramTable(allPrograms);
        renderCopybookDetails(inventory.copybooks);
        renderBatchFlows(inventory.jcl_jobs);
        setupProgramFilters();
      }
      if (depGraph) renderDependencyGraph(depGraph);
      if (deadCode) renderDeadCode(deadCode);
      if (lineage) renderLineage(lineage);
      if (deep) {
        allDeep = deep;
        renderCrossRef(deep);
        renderImplicitConnections(deep);
        renderCommareaFlows(deep);
        renderRedefines(deep);
        renderCoupling(deep);
        renderImpactAnalysis(deep);
        setupFieldFilter();
      }
    } catch (err) {
      console.error("Dashboard init error:", err);
    }
  }

  async function loadJSON(filename) {
    try {
      const resp = await fetch(DATA_DIR + "/" + filename);
      if (!resp.ok) return null;
      return await resp.json();
    } catch (e) {
      return null;
    }
  }

  // ── Tabs ───────────────────────────────────────────────────
  function setupTabs() {
    document.querySelectorAll(".tab").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll(".tab").forEach(function (b) { b.classList.remove("active"); });
        document.querySelectorAll("main > .panel").forEach(function (p) { p.classList.remove("active"); });
        btn.classList.add("active");
        var panel = document.getElementById("panel-" + btn.dataset.panel);
        if (panel) panel.classList.add("active");
      });
    });
  }

  function setupSubTabs() {
    document.querySelectorAll(".sub-tab").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var parent = btn.closest(".panel");
        parent.querySelectorAll(".sub-tab").forEach(function (b) { b.classList.remove("active"); });
        parent.querySelectorAll(".sub-panel").forEach(function (p) { p.classList.remove("active"); });
        btn.classList.add("active");
        var panel = parent.querySelector("#sub-" + btn.dataset.subtab);
        if (panel) panel.classList.add("active");
      });
    });
  }

  // ── Summary Cards ─────────────────────────────────────────
  function renderSummaryCards(summary) {
    var inv = summary.inventory || {};
    var dep = summary.dependency_graph || {};
    var dead = summary.dead_code || {};
    var lin = summary.data_lineage || {};
    var da = summary.deep_analysis || {};

    var cards = [
      { label: "Programs", value: inv.total_programs || 0, detail: (inv.total_loc || 0).toLocaleString() + " lines of code" },
      { label: "Copybooks", value: inv.total_copybooks || 0, detail: (lin.shared_copybooks || 0) + " shared across programs" },
      { label: "JCL Jobs", value: inv.total_jcl_jobs || 0, detail: (inv.programs_batch_only || 0) + " batch programs" },
      { label: "Dependencies", value: dep.total_edges || 0, detail: (dep.total_nodes || 0) + " nodes in graph" },
      { label: "Cross-Refs", value: da.fields_crossreferenced || 0, detail: (da.implicit_connections || 0) + " implicit connections" },
      { label: "High Risk", value: da.high_risk_fields || 0, detail: (da.commarea_flows || 0) + " COMMAREA flows" },
      { label: "Dead Code", value: (dead.dead_programs || 0) + (dead.dead_copybooks || 0), detail: (dead.dead_program_pct || 0) + "% of programs" },
      { label: "REDEFINES", value: da.redefines_chains || 0, detail: "memory overlay chains" },
    ];

    var container = document.getElementById("summary-cards");
    container.innerHTML = "";
    cards.forEach(function (c) {
      var div = document.createElement("div");
      div.className = "card";
      var lbl = document.createElement("div");
      lbl.className = "label";
      lbl.textContent = c.label;
      var val = document.createElement("div");
      val.className = "value";
      val.textContent = c.value;
      var det = document.createElement("div");
      det.className = "detail";
      det.textContent = c.detail;
      div.appendChild(lbl);
      div.appendChild(val);
      div.appendChild(det);
      container.appendChild(div);
    });
  }

  // ── Program Inventory ─────────────────────────────────────
  function renderProgramTable(programs) {
    var tbody = document.querySelector("#program-table tbody");
    tbody.innerHTML = "";
    programs
      .sort(function (a, b) { return b.complexity_score - a.complexity_score; })
      .forEach(function (p) {
        var tr = document.createElement("tr");
        var badge = p.complexity_score > 40 ? "high" : p.complexity_score > 20 ? "med" : "low";
        var typeBadge = p.cics_commands.length ? "cics" : "batch";
        var typeLabel = p.cics_commands.length ? "CICS" : "Batch";

        tr.innerHTML =
          "<td><code>" + esc(p.program_id) + "</code></td>" +
          "<td>" + p.loc + "</td>" +
          "<td><span class='badge badge-" + badge + "'>" + p.complexity_score + "</span></td>" +
          "<td>" + p.copy_refs.length + "</td>" +
          "<td>" + (p.call_targets.length ? p.call_targets.map(function (t) { return "<code>" + esc(t) + "</code>"; }).join(" ") : "\u2014") + "</td>" +
          "<td><span class='badge badge-" + typeBadge + "'>" + typeLabel + "</span></td>" +
          "<td>" + (p.cics_commands.length ? p.cics_commands.map(esc).join(", ") : "\u2014") + "</td>";
        tbody.appendChild(tr);
      });
  }

  function setupProgramFilters() {
    var filterInput = document.getElementById("prog-filter");
    var typeSelect = document.getElementById("prog-type-filter");
    function applyFilter() {
      var text = filterInput.value.toUpperCase();
      var type = typeSelect.value;
      var filtered = allPrograms.filter(function (p) {
        if (text && p.program_id.toUpperCase().indexOf(text) === -1) return false;
        if (type === "cics" && !p.cics_commands.length) return false;
        if (type === "batch" && p.cics_commands.length) return false;
        return true;
      });
      renderProgramTable(filtered);
    }
    filterInput.addEventListener("input", applyFilter);
    typeSelect.addEventListener("change", applyFilter);
  }

  // ── Dependency Graph ──────────────────────────────────────
  function renderDependencyGraph(data) {
    var container = document.getElementById("dep-graph");
    var width = container.clientWidth || 900;
    var height = 550;

    var colorMap = { program: "#3b82f6", copybook: "#10b981", jcl_job: "#f59e0b", dataset: "#8b5cf6" };

    var svg = d3.select("#dep-graph").append("svg")
      .attr("width", width).attr("height", height)
      .attr("viewBox", [0, 0, width, height]);
    var g = svg.append("g");

    svg.call(d3.zoom().scaleExtent([0.1, 6]).on("zoom", function (e) { g.attr("transform", e.transform); }));

    function getVisibleTypes() {
      var types = [];
      if (document.getElementById("show-programs").checked) types.push("program");
      if (document.getElementById("show-copybooks").checked) types.push("copybook");
      if (document.getElementById("show-jcl").checked) types.push("jcl_job");
      if (document.getElementById("show-datasets").checked) types.push("dataset");
      return types;
    }

    function render() {
      g.selectAll("*").remove();
      var visTypes = getVisibleTypes();
      var visIds = new Set();
      data.nodes.forEach(function (n) { if (visTypes.indexOf(n.type) !== -1) visIds.add(n.id); });
      var nodes = data.nodes.filter(function (n) { return visIds.has(n.id); });
      var links = data.edges.filter(function (e) { return visIds.has(e.source.id || e.source) && visIds.has(e.target.id || e.target); });

      if (!nodes.length) return;

      var sim = d3.forceSimulation(nodes)
        .force("link", d3.forceLink(links).id(function (d) { return d.id; }).distance(60))
        .force("charge", d3.forceManyBody().strength(-120))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide(20));

      var link = g.append("g").selectAll("line").data(links).join("line")
        .attr("stroke", "#cbd5e1").attr("stroke-width", 1).attr("stroke-opacity", 0.4);

      var node = g.append("g").selectAll("g").data(nodes).join("g")
        .call(d3.drag().on("start", dragstart).on("drag", dragged).on("end", dragend));

      node.append("circle").attr("r", function (d) {
        return d.type === "program" ? 7 : d.type === "copybook" ? 5 : 4;
      }).attr("fill", function (d) { return colorMap[d.type] || "#999"; })
        .attr("stroke", "#fff").attr("stroke-width", 1);

      node.append("text").text(function (d) { return d.label; })
        .attr("x", 10).attr("y", 3).attr("font-size", "9px").attr("fill", "#475569");

      // Click to highlight connected
      node.on("click", function (event, d) {
        var connectedIds = new Set([d.id]);
        links.forEach(function (l) {
          var sid = l.source.id || l.source;
          var tid = l.target.id || l.target;
          if (sid === d.id) connectedIds.add(tid);
          if (tid === d.id) connectedIds.add(sid);
        });
        node.select("circle").attr("opacity", function (n) { return connectedIds.has(n.id) ? 1 : 0.15; });
        node.select("text").attr("opacity", function (n) { return connectedIds.has(n.id) ? 1 : 0.1; });
        link.attr("stroke-opacity", function (l) {
          var sid = l.source.id || l.source;
          var tid = l.target.id || l.target;
          return (sid === d.id || tid === d.id) ? 0.8 : 0.05;
        });

        var detail = document.getElementById("node-detail");
        detail.style.display = "block";
        var connected = [];
        links.forEach(function (l) {
          var sid = l.source.id || l.source;
          var tid = l.target.id || l.target;
          if (sid === d.id) connected.push(tid);
          if (tid === d.id) connected.push(sid);
        });
        detail.innerHTML = "<h4>" + esc(d.type.toUpperCase()) + ": " + esc(d.label) + "</h4>" +
          "<p>" + connected.length + " connections: " + connected.map(function (c) { return "<code>" + esc(c) + "</code>"; }).join(" ") + "</p>";
      });

      // Double-click to reset
      svg.on("dblclick", function () {
        node.select("circle").attr("opacity", 1);
        node.select("text").attr("opacity", 1);
        link.attr("stroke-opacity", 0.4);
        document.getElementById("node-detail").style.display = "none";
      });

      sim.on("tick", function () {
        link.attr("x1", function (d) { return d.source.x; }).attr("y1", function (d) { return d.source.y; })
          .attr("x2", function (d) { return d.target.x; }).attr("y2", function (d) { return d.target.y; });
        node.attr("transform", function (d) { return "translate(" + d.x + "," + d.y + ")"; });
      });

      function dragstart(event, d) { if (!event.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }
      function dragged(event, d) { d.fx = event.x; d.fy = event.y; }
      function dragend(event, d) { if (!event.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }
    }

    render();
    document.querySelectorAll(".graph-controls input").forEach(function (cb) { cb.addEventListener("change", render); });
  }

  // ── Field Cross-Reference ─────────────────────────────────
  function renderCrossRef(deep) {
    var tbody = document.querySelector("#crossref-table tbody");
    tbody.innerHTML = "";
    (deep.field_crossref || []).forEach(function (f) {
      var tr = document.createElement("tr");
      var progs = f.referenced_by.map(function (r) {
        return "<span class='prog-tag'>" + esc(r.program) + " <span style='color:#94a3b8'>(" + r.usage + ")</span></span>";
      }).join("");
      tr.innerHTML =
        "<td><code>" + esc(f.copybook) + "</code></td>" +
        "<td><code>" + esc(f.field) + "</code></td>" +
        "<td><code>" + esc(f.picture || "GROUP") + "</code></td>" +
        "<td>" + f.byte_offset + "</td>" +
        "<td>" + f.byte_size + "B</td>" +
        "<td>" + f.referenced_by.length + "</td>" +
        "<td>" + progs + "</td>";
      tbody.appendChild(tr);
    });
  }

  function setupFieldFilter() {
    var filterInput = document.getElementById("field-filter");
    if (!filterInput || !allDeep) return;
    filterInput.addEventListener("input", function () {
      var text = filterInput.value.toUpperCase();
      var rows = document.querySelectorAll("#crossref-table tbody tr");
      rows.forEach(function (row) {
        row.style.display = row.textContent.toUpperCase().indexOf(text) !== -1 ? "" : "none";
      });
    });
  }

  // ── Implicit Connections ──────────────────────────────────
  function renderImplicitConnections(deep) {
    var tbody = document.querySelector("#implicit-table tbody");
    tbody.innerHTML = "";
    (deep.implicit_connections || []).forEach(function (c) {
      var tr = document.createElement("tr");
      tr.innerHTML =
        "<td><code>" + esc(c.copybook_a) + "</code></td>" +
        "<td><code>" + esc(c.field_a) + "</code></td>" +
        "<td><code>" + esc(c.pic_a || "") + "</code></td>" +
        "<td><code>" + esc(c.copybook_b) + "</code></td>" +
        "<td><code>" + esc(c.field_b) + "</code></td>" +
        "<td><code>" + esc(c.pic_b || "") + "</code></td>" +
        "<td>" + c.size_a + "B</td>" +
        "<td>" + c.programs_affected.length + "</td>";
      tbody.appendChild(tr);
    });
  }

  // ── COMMAREA Flow ─────────────────────────────────────────
  function renderCommareaFlows(deep) {
    // Table
    var tbody = document.querySelector("#commarea-table tbody");
    tbody.innerHTML = "";
    (deep.commarea_flows || []).forEach(function (f) {
      var tr = document.createElement("tr");
      tr.innerHTML =
        "<td><code>" + esc(f.from_program) + "</code></td>" +
        "<td><code>" + esc(f.to_program) + "</code></td>" +
        "<td><span class='badge badge-cics'>" + esc(f.mechanism) + "</span></td>" +
        "<td>" + esc(f.target_type || "literal") + "</td>";
      tbody.appendChild(tr);
    });

    // Graph
    var flows = deep.commarea_flows || [];
    if (!flows.length) return;

    var nodeSet = new Set();
    flows.forEach(function (f) { nodeSet.add(f.from_program); nodeSet.add(f.to_program); });
    var nodes = Array.from(nodeSet).map(function (id) { return { id: id }; });
    var links = flows.map(function (f) { return { source: f.from_program, target: f.to_program, mechanism: f.mechanism }; });

    var container = document.getElementById("commarea-graph");
    var width = container.clientWidth || 800;
    var height = 400;

    var svg = d3.select("#commarea-graph").append("svg")
      .attr("width", width).attr("height", height);
    var g = svg.append("g");

    svg.call(d3.zoom().scaleExtent([0.2, 4]).on("zoom", function (e) { g.attr("transform", e.transform); }));

    // Arrow marker
    svg.append("defs").append("marker")
      .attr("id", "arrowhead").attr("viewBox", "0 -5 10 10")
      .attr("refX", 20).attr("refY", 0).attr("markerWidth", 6).attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path").attr("d", "M0,-5L10,0L0,5").attr("fill", "#94a3b8");

    var sim = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id(function (d) { return d.id; }).distance(100))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2));

    var link = g.append("g").selectAll("line").data(links).join("line")
      .attr("stroke", "#94a3b8").attr("stroke-width", 1.5)
      .attr("marker-end", "url(#arrowhead)");

    var node = g.append("g").selectAll("g").data(nodes).join("g")
      .call(d3.drag()
        .on("start", function (e, d) { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
        .on("drag", function (e, d) { d.fx = e.x; d.fy = e.y; })
        .on("end", function (e, d) { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }));

    node.append("rect").attr("x", -35).attr("y", -12).attr("width", 70).attr("height", 24)
      .attr("rx", 4).attr("fill", "#eff6ff").attr("stroke", "#3b82f6").attr("stroke-width", 1);
    node.append("text").text(function (d) { return d.id; })
      .attr("text-anchor", "middle").attr("y", 4).attr("font-size", "8px").attr("fill", "#1e40af")
      .attr("font-family", "'SF Mono', Menlo, Consolas, monospace");

    sim.on("tick", function () {
      link.attr("x1", function (d) { return d.source.x; }).attr("y1", function (d) { return d.source.y; })
        .attr("x2", function (d) { return d.target.x; }).attr("y2", function (d) { return d.target.y; });
      node.attr("transform", function (d) { return "translate(" + d.x + "," + d.y + ")"; });
    });
  }

  // ── REDEFINES ─────────────────────────────────────────────
  function renderRedefines(deep) {
    var container = document.getElementById("redefines-list");
    container.innerHTML = "";
    var chains = (deep.redefines_chains || []).filter(function (c) { return c.overlays.length > 0; });
    // Group by copybook, show top 30
    chains.slice(0, 30).forEach(function (c) {
      var div = document.createElement("div");
      div.className = "redef-card";
      var overlays = c.overlays.map(function (o) {
        return "<div class='redef-overlay'>REDEFINES " + esc(o.name) + " PIC " + esc(o.pic || "GROUP") + " (" + o.size + "B)</div>";
      }).join("");
      var users = c.programs_using.length
        ? "<div class='redef-users'>Used by: " + c.programs_using.map(function (u) { return "<code>" + esc(u) + "</code>"; }).join(" ") + "</div>"
        : "";
      div.innerHTML =
        "<div class='redef-header'>" + esc(c.copybook) + "." + esc(c.base_field) +
        " <span style='color:#64748b;font-weight:400'>PIC " + esc(c.base_pic || "GROUP") +
        " @" + c.base_offset + " (" + c.base_size + "B)</span></div>" +
        overlays + users;
      container.appendChild(div);
    });
    if (!chains.length) {
      container.textContent = "No REDEFINES chains found.";
    }
  }

  // ── Coupling ──────────────────────────────────────────────
  function renderCoupling(deep) {
    var tbody = document.querySelector("#coupling-table tbody");
    tbody.innerHTML = "";
    (deep.program_coupling || []).forEach(function (c) {
      var tr = document.createElement("tr");
      tr.innerHTML =
        "<td><code>" + esc(c.program_a) + "</code></td>" +
        "<td><code>" + esc(c.program_b) + "</code></td>" +
        "<td>" + c.shared_copybooks.map(function (s) { return "<code>" + esc(s) + "</code>"; }).join(" ") + "</td>" +
        "<td><span class='badge badge-" + (c.coupling_score >= 8 ? "high" : c.coupling_score >= 4 ? "med" : "low") + "'>" + c.coupling_score + "</span></td>";
      tbody.appendChild(tr);
    });
  }

  // ── Impact Analysis ───────────────────────────────────────
  function renderImpactAnalysis(deep) {
    var tbody = document.querySelector("#impact-table tbody");
    tbody.innerHTML = "";
    (deep.critical_paths || []).forEach(function (c) {
      var tr = document.createElement("tr");
      var riskClass = "risk-" + c.risk_level;
      tr.innerHTML =
        "<td><span class='" + riskClass + "'>" + c.risk_level.toUpperCase() + "</span></td>" +
        "<td><code>" + esc(c.copybook) + "</code></td>" +
        "<td><code>" + esc(c.field) + "</code></td>" +
        "<td><code>" + esc(c.picture || "") + "</code></td>" +
        "<td>" + c.byte_offset + "</td>" +
        "<td>" + c.programs_affected + "</td>" +
        "<td>" + (c.writers.length ? c.writers.map(function (w) { return "<code>" + esc(w) + "</code>"; }).join(" ") : "\u2014") + "</td>" +
        "<td>" + c.downstream_connections + "</td>";
      tbody.appendChild(tr);
    });
  }

  // ── Dead Code ─────────────────────────────────────────────
  function renderDeadCode(data) {
    var s = data.summary || {};
    var summ = document.getElementById("dead-summary");
    summ.innerHTML = "";

    var stats = [
      { num: s.dead_programs || 0, label: "Dead Programs (" + (s.dead_program_pct || 0) + "%)" },
      { num: s.dead_copybooks || 0, label: "Dead Copybooks (" + (s.dead_copybook_pct || 0) + "%)" },
    ];
    stats.forEach(function (st) {
      var div = document.createElement("div");
      div.className = "dead-stat";
      var n = document.createElement("div");
      n.className = "number";
      n.textContent = st.num;
      var l = document.createElement("div");
      l.className = "label";
      l.textContent = st.label;
      div.appendChild(n);
      div.appendChild(l);
      summ.appendChild(div);
    });

    var progTbody = document.querySelector("#dead-programs-table tbody");
    progTbody.innerHTML = "";
    (data.dead_programs || []).forEach(function (p) {
      var tr = document.createElement("tr");
      tr.innerHTML = "<td><code>" + esc(p.program_id) + "</code></td><td>" + p.loc + "</td><td>" + esc(p.reason) + "</td>";
      progTbody.appendChild(tr);
    });

    var cpyTbody = document.querySelector("#dead-copybooks-table tbody");
    cpyTbody.innerHTML = "";
    (data.dead_copybooks || []).forEach(function (c) {
      var tr = document.createElement("tr");
      tr.innerHTML = "<td><code>" + esc(c.name) + "</code></td><td>" + c.field_count + "</td><td>" + c.total_bytes + "</td><td>" + esc(c.reason) + "</td>";
      cpyTbody.appendChild(tr);
    });
  }

  // ── Data Lineage ──────────────────────────────────────────
  function renderLineage(data) {
    var linTbody = document.querySelector("#lineage-table tbody");
    linTbody.innerHTML = "";
    (data.shared_copybooks || [])
      .sort(function (a, b) { return b.sharing_count - a.sharing_count; })
      .forEach(function (c) {
        var tr = document.createElement("tr");
        tr.innerHTML =
          "<td><code>" + esc(c.copybook) + "</code></td>" +
          "<td>" + c.sharing_count + "</td>" +
          "<td>" + c.used_by.map(function (u) { return "<span class='prog-tag'>" + esc(u) + "</span>"; }).join("") + "</td>";
        linTbody.appendChild(tr);
      });

    var ioTbody = document.querySelector("#fileio-table tbody");
    ioTbody.innerHTML = "";
    (data.file_io_map || []).forEach(function (f) {
      var tr = document.createElement("tr");
      tr.innerHTML =
        "<td><code>" + esc(f.dataset) + "</code></td>" +
        "<td>" + (f.read_by.length ? f.read_by.map(function (r) { return "<code>" + esc(r) + "</code>"; }).join(" ") : "\u2014") + "</td>" +
        "<td>" + (f.written_by.length ? f.written_by.map(function (w) { return "<code>" + esc(w) + "</code>"; }).join(" ") : "\u2014") + "</td>";
      ioTbody.appendChild(tr);
    });
  }

  // ── Batch Flows ───────────────────────────────────────────
  function renderBatchFlows(jobs) {
    var container = document.getElementById("batch-flows");
    container.innerHTML = "";
    var filtered = (jobs || []).filter(function (j) { return j.steps && j.steps.length > 0; });
    if (!filtered.length) {
      container.textContent = "No batch jobs with steps found.";
      return;
    }
    filtered.forEach(function (j) {
      var div = document.createElement("div");
      div.className = "batch-card";
      var h4 = document.createElement("h4");
      h4.textContent = j.job_name;
      div.appendChild(h4);
      var chain = document.createElement("div");
      chain.className = "step-chain";
      j.steps.forEach(function (s, i) {
        if (i > 0) {
          var arrow = document.createElement("span");
          arrow.className = "step-arrow";
          arrow.innerHTML = "&rarr;";
          chain.appendChild(arrow);
        }
        var box = document.createElement("span");
        box.className = "step-box";
        box.textContent = s.program;
        box.title = "Step: " + s.step_name;
        chain.appendChild(box);
      });
      div.appendChild(chain);
      container.appendChild(div);
    });
  }

  // ── Copybook Memory Layouts ───────────────────────────────
  function renderCopybookDetails(copybooks) {
    var container = document.getElementById("copybook-details");
    container.innerHTML = "";
    var sorted = (copybooks || [])
      .filter(function (c) { return c.fields && c.fields.length > 0; })
      .sort(function (a, b) { return b.total_bytes - a.total_bytes; });

    sorted.forEach(function (c) {
      var div = document.createElement("div");
      div.className = "copybook-card";
      div.dataset.name = c.name.toUpperCase();

      var h4 = document.createElement("h4");
      h4.textContent = c.name;
      div.appendChild(h4);

      var meta = document.createElement("div");
      meta.className = "meta";
      meta.textContent = c.total_bytes + " bytes total, " + c.fields.length + " fields";
      div.appendChild(meta);

      var grid = document.createElement("div");
      grid.className = "field-grid";
      // Header
      ["Lvl", "Field Name", "PIC Clause", "Size", "Byte Range"].forEach(function (h) {
        var fh = document.createElement("div");
        fh.className = "fh";
        fh.textContent = h;
        grid.appendChild(fh);
      });

      c.fields.forEach(function (f) {
        if (f.is_condition) return;

        var lvlDiv = document.createElement("div");
        lvlDiv.textContent = String(f.level).padStart(2, "0");
        grid.appendChild(lvlDiv);

        var nameDiv = document.createElement("div");
        nameDiv.textContent = f.name;
        if (f.level > 5) nameDiv.className = "indent";
        if (f.redefines) nameDiv.className = (nameDiv.className + " redef").trim();
        if (!f.picture && f.byte_size === 0) nameDiv.className = (nameDiv.className + " group-field").trim();
        grid.appendChild(nameDiv);

        var picDiv = document.createElement("div");
        picDiv.textContent = f.redefines ? "REDEFINES " + f.redefines : (f.picture || "GROUP");
        if (f.redefines) picDiv.className = "redef";
        grid.appendChild(picDiv);

        var sizeDiv = document.createElement("div");
        sizeDiv.textContent = f.byte_size > 0 ? f.byte_size + "B" : "\u2014";
        grid.appendChild(sizeDiv);

        var rangeDiv = document.createElement("div");
        rangeDiv.textContent = f.byte_size > 0 ? f.byte_offset + "-" + (f.byte_offset + f.byte_size - 1) : "\u2014";
        grid.appendChild(rangeDiv);
      });

      div.appendChild(grid);
      container.appendChild(div);
    });

    // Copybook filter
    var filterInput = document.getElementById("cpy-filter");
    if (filterInput) {
      filterInput.addEventListener("input", function () {
        var text = filterInput.value.toUpperCase();
        container.querySelectorAll(".copybook-card").forEach(function (card) {
          card.style.display = card.dataset.name.indexOf(text) !== -1 ? "" : "none";
        });
      });
    }
  }

  // ── Utility ───────────────────────────────────────────────
  function esc(s) {
    if (s == null) return "";
    var el = document.createElement("span");
    el.textContent = String(s);
    return el.innerHTML;
  }

  document.addEventListener("DOMContentLoaded", init);
})();
