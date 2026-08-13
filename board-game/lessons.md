# lessons — hard rules from real builds

Injected into every DRAFT, BUILD and REPAIR prompt. These are not advice;
violating one is how a previous build failed.

Repair rounds append here. **A lesson that appears twice must GRADUATE into
code** — a lint rule in `gate.py`, a threshold, a golden block, or a
constraint in the brief-writer's template — and is then marked
`[GRADUATED -> where]`. Prose that repeats is prose nobody acted on: the
pipeline this replaced knew one fact for three turns and changed nothing.

`improve.py` flags repeats mechanically, but only catches the ones that look
alike. Reading for repeated *meaning* is a human's job, and the auditor's.

---

- [GRADUATED -> gate.py lint] Never fillet all three edge directions of a box at once (`.edges().fillet(r)`). OCCT synthesises a spherical vertex blend at each corner and tessellates it into phantom sliver bodies that pass a no-error check and fail the watertight/body count. Bake corner rounds into the 2D profile and apply top/bottom fillets afterwards.
- [GRADUATED -> gate.py bill check + blocks.add_piece_family] Pieces the rules require to be loose must be separately named `cq.Assembly` children. Never `union()` them: 48 tiles arriving as one continuous mat is what ended fifteen turns of the previous pipeline.
- [GRADUATED -> ergonomics_check.MIN_RELIEF_MM] Relief under 0.6mm is modelled faithfully and then invisible — in the print and in every render. If a motif carries identity, give it depth worth printing.
- [GRADUATED -> blocks.shared_positions] When two layers must line up, generate the pattern once and reuse the same list for both. Two coordinate lists that agree today stop agreeing after one edit.
