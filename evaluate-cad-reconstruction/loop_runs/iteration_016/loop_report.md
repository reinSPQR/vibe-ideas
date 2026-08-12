# Evaluation Skill Improvement Loop - Iteration 016

- Batch evaluated: 4 explicit projects under `outputs/reconstructions/step-to-cadquery`
- Artifact policy: final `evaluation_report.json` only in each project; temporary `.eval_tmp` files removed
- Evaluator change applied: none

## Batch Scores

| Project | Printability | Physical | Feature |
|---|---:|---:|---:|
| `gridfinity-sd-card-microsd-card-and-usb-stick-hold` | 10.0 | 10.0 | 9.4 |
| `gridfinity-under-desk-drawer` | 9.4 | 4.0 | 8.0 |
| `gridfinity-usb-cablemanager` | 10.0 | 10.0 | 9.0 |
| `gridfinity-utensil-holder` | 10.0 | 10.0 | 8.2 |

## Helper Usage

- Used checks: `assembly_component_count`, `part_component_count`, `part_collision`, `relative_pose`, `clear_path_proxy`
- New helper added: none
- Regression reruns: not applicable because no evaluator code or scoring policy changed

## Batch Findings

- The three single-body Gridfinity holders/trays were fully covered by existing component-count and `clear_path_proxy` checks.
- `gridfinity-under-desk-drawer` was split into temporary placed components from the assembled STL. The scorer mapped `component_000` to the tray and `component_001` to the mount flange/legs, then found a critical tray/flange interpenetration with `part_collision`.
- Fresh `render_views.py` rendering was attempted for all four projects but failed in this sandbox because `cadquery` is not installed. Existing original/rebuilt render PNGs were used as visual context and the limitation is recorded in each final report.

## Improvement Decision

No narrow deterministic helper/proxy/scoring-policy change was made this iteration.

The batch did not expose a local missing-helper gap. Remaining unmeasured relationships are external-object or real-use checks, such as exact SD/microSD/USB/cable/utensil fit, desk mounting hardware behavior, load/friction, and ergonomics. Those require project-specific external proxies or broader physical modeling, not a small evaluator helper.

## Before/After

Because no evaluator change was applied, before and after scores are identical:

| Project | Before | After |
|---|---|---|
| `gridfinity-sd-card-microsd-card-and-usb-stick-hold` | P 10.0 / Phys 10.0 / F 9.4 | P 10.0 / Phys 10.0 / F 9.4 |
| `gridfinity-under-desk-drawer` | P 9.4 / Phys 4.0 / F 8.0 | P 9.4 / Phys 4.0 / F 8.0 |
| `gridfinity-usb-cablemanager` | P 10.0 / Phys 10.0 / F 9.0 | P 10.0 / Phys 10.0 / F 9.0 |
| `gridfinity-utensil-holder` | P 10.0 / Phys 10.0 / F 8.2 | P 10.0 / Phys 10.0 / F 8.2 |

## Residual Risks

- `clear_path_proxy` validates sampled straight paths only; it does not measure full opening diameter, profile fidelity, card/cable insertion envelope, or ergonomic usability.
- Drawer physical correctness depends on sampled mesh collision between extracted STL components. It is useful as a deterministic proxy, but exact functional sliding/mounting behavior would require explicit use-pose or hardware geometry.
- Feature-retention scores remain LLM-judged from specs, code, scorer outputs, and existing renders because fresh renders could not be generated in the current environment.
