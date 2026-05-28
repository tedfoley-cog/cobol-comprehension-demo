# Demo Cheat Sheet — COBOL Comprehension

## Setup (do this before joining the call)
- [ ] Open the repo in a fresh Devin session
- [ ] Confirm the submodule is checked out: `ls carddemo-source/app/cbl/` should show COBOL files

## Demo Flow
1. **Set the stage**: "Comprehension is the hardest part of mainframe modernization — 68% of efforts fail because teams don't understand what the code does before they try to change it."
2. **Prompt Devin**: "Analyze the COBOL source in carddemo-source/ and populate the comprehension dashboard" — Devin runs the full analysis pipeline against 31 programs, 30+ copybooks, and 38 JCL jobs.
3. **Open the dashboard** in the browser tab once Devin finishes — walk through the six panels: inventory, dependency graph, data lineage, batch flows, dead code, copybook tracing.
4. **Zoom into copybook tracing**: "A field like WS-FIELD-01 in one program is CUST-TAX-NUM in another, connected only by byte position in a shared copybook — Devin traces these implicit dependencies automatically."
5. **Show the dependency graph**: drag nodes to highlight how a single copybook like COCOM01Y connects 15+ programs — a change to one field ripples everywhere.
6. **(Optional) Modernization snippet**: Prompt Devin to convert CBTRN02C to Python — shows the comprehension-to-conversion pipeline in action.
