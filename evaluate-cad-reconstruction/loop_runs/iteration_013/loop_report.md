# Evaluation Skill Improvement Loop

- Generated: `2026-07-09T10:31:12.724476+00:00`
- Root: `outputs/reconstructions/step-to-cadquery`
- Projects: `25`

## Scores

| Project | Printability | Physical | Feature |
|---|---:|---:|---:|
| `outputs/reconstructions/step-to-cadquery/3d-printable-jet-engine` | 0.4 | 6.2 | 8.6 |
| `outputs/reconstructions/step-to-cadquery/5015-radial-fan-3d-model-for-conception-step-stl-f` | 9.2 | 8.0 | 8.4 |
| `outputs/reconstructions/step-to-cadquery/all-in-one-temperature-bridging-tower` | 4.0 | 9.2 | 9.2 |
| `outputs/reconstructions/step-to-cadquery/arduino-uno` | 9.9 | 10.0 | 8.8 |
| `outputs/reconstructions/step-to-cadquery/articulated-snowman-fidget` | 5.5 | 6.0 | 8.6 |
| `outputs/reconstructions/step-to-cadquery/articulated-tie-step-file-included` | 5.5 | 8.0 | 8.7 |
| `outputs/reconstructions/step-to-cadquery/aspire-planter` | 6.7 | 6.0 | 8.2 |
| `outputs/reconstructions/step-to-cadquery/astronomical-telescope-hadley-an-easy-assembly-hig` | 4.0 | 6.0 | 8.0 |
| `outputs/reconstructions/step-to-cadquery/bambu-lab-filament-poop-bin-x1c-p1s-and-p2s` | 4.0 | 10.0 | 8.6 |
| `outputs/reconstructions/step-to-cadquery/bentobox-v20-carbon-filter-for-bambu-lab-x1c-enclo` | 9.6 | 10.0 | 8.4 |
| `outputs/reconstructions/step-to-cadquery/build-tray` | 8.4 | 10.0 | 9.3 |
| `outputs/reconstructions/step-to-cadquery/cable-spool-holder-gridfinity` | 4.0 | 8.0 | 7.6 |
| `outputs/reconstructions/step-to-cadquery/cricut-material-holder` | None | None | None |
| `outputs/reconstructions/step-to-cadquery/crossbow-kit-card-fully-printed` | None | None | None |
| `outputs/reconstructions/step-to-cadquery/customizable-stackable-beer-crate` | None | None | None |
| `outputs/reconstructions/step-to-cadquery/dewalt-battery-holder` | None | None | None |
| `outputs/reconstructions/step-to-cadquery/dummy-13-frame-step-file` | 1.2 | 7.2 | 8.4 |
| `outputs/reconstructions/step-to-cadquery/easy-filament-swap-gingerbread-cookie` | 4.0 | 10.0 | 8.8 |
| `outputs/reconstructions/step-to-cadquery/easy-to-print-functional-janney-coupler-including` | 4.0 | 8.0 | 8.6 |
| `outputs/reconstructions/step-to-cadquery/ender-3-v2-step-file-for-easy-modification-and-des` | 2.4 | 8.0 | 9.0 |
| `outputs/reconstructions/step-to-cadquery/phone-holder` | 4.0 | 10.0 | 5.5 |
| `outputs/reconstructions/step-to-cadquery/silica-gel-spool-container` | 3.6 | 6.0 | 8.0 |
| `outputs/reconstructions/step-to-cadquery/simple-twist-open-mushroom` | 4.0 | 4.0 | 9.1 |
| `outputs/reconstructions/step-to-cadquery/spool-holder-and-drybox-for-enclosure-v2-with-humi` | 4.0 | 4.0 | 7.6 |
| `outputs/reconstructions/step-to-cadquery/tablet-and-notebook-stand` | 4.0 | 10.0 | 8.7 |

## Check Usage

- Used checks: `part_component_count, assembly_component_count, clear_path_proxy, cylindrical_fit, part_contact, feature_count, opening_presence, assembly_sequence, part_clearance, axis_alignment, vent_opening_proxy, spherical_fit`
- Unused checks: `part_collision, linear_motion_collision, linear_motion_clearance, rotation_motion_collision, relative_pose, vent_grid_open_area_proxy, contact_graph`
- Failed checks: `{"assembly_component_count": 10, "clear_path_proxy": 2, "part_component_count": 4}`

## Improvement Candidates

- `implement_now` x1: {'relationship': 'ball socket seating and articulation', 'triage': 'proxy_now', 'reason': 'Could be approximated by placed-instance contact/axis checks after component extraction; not implemented in this iteration.'}
- `implement_now` x1: {'relationship': 'full hinge rotation path for each seated joint', 'triage': 'missing_helper', 'reason': 'Needs joint-aware kinematics and placed-instance geometry; existing rotation helper is too coarse for print-in-place seated hinge knuckles.'}
- `implement_now` x1: {'relationship': 'pot drains and saucer drain grid open-area preservation', 'triage': 'proxy_now', 'reason': 'Existing vent/opening proxies could sample rays if placed component meshes or coordinates were prepared; not needed as a new helper.'}
- `implement_now` x1: {'relationship': 'tab through arm slot clearance and seated contact', 'triage': 'implement_now/proxy_now candidate but not selected', 'reason': 'Requires localized slot/tab overlap or clearance profile after component extraction; current generic distance/contact is too coarse because the tab intentionally occupies the slot.'}
- `implement_now` x1: vent holes/grilles: opening presence could be sampled but is unreliable on highly perforated non-watertight STL
- `implement_now` x1: dot/eye inserts vs body sockets: clearance-fit/contact/glue seating, missing socket proxy/clearance helper
- `implement_now` x1: Snap/press-fit compliance for bracket slots and beam tabs is not implemented.
- `implement_now` x1: Full folding motion path for the linkage needs joint-aware kinematic helpers; current rotation helper is too coarse for seated hinge geometry.
- `proxy_now` x1: body vs cap: cylindrical/threaded fit and rotation-motion; current helper cannot validate helical thread
- `proxy_now` x1: cap/body pairs: rotation-motion/thread or bayonet engagement, missing twist-cam helper
- `proxy_now` x1: True screw thread engagement and torque retention are not implemented.
- `proxy_now` x1: Load-bearing stiffness, tipping stability, and device weight support are not implemented.
- `missing_helper` x1: {'relationship': 'elastic cord through bottom/chest/head bores', 'triage': 'missing_helper', 'reason': 'Requires path continuity through internal cavities and flexible cord behavior; no placed-instance cavity/path extraction available in this environment.'}
- `missing_helper` x1: {'relationship': 'clip spring compliance and shirt retention', 'triage': 'missing_helper', 'reason': 'Requires material flexibility/friction and external fabric geometry.'}
- `missing_helper` x1: {'relationship': 'pot-in-saucer seating/support', 'triage': 'missing_helper', 'reason': 'Requires external/use-pose placement, since the exported assembly is a laid-out print set rather than nested pots in saucers.'}
- `missing_helper` x1: {'relationship': 'tube, truss pole, mirror, focuser, screw and clamp fit', 'triage': 'missing_helper', 'reason': 'External mating hardware is absent; requires external proxy dimensions not encoded in this report.'}
- `missing_helper` x1: {'relationship': 'thread engagement and load-bearing stiffness', 'triage': 'missing_helper', 'reason': 'Requires thread/material/load simulation beyond current deterministic helpers.'}
- `missing_helper` x1: {'relationship': 'snap-off tab breakability and assembled crossbow mechanics', 'triage': 'missing_helper', 'reason': 'Requires material/fracture/flexible limb behavior and post-separation assembly state not represented by the single fused print STL.'}
- `missing_helper` x1: {'relationship': 'true crate stacking/nesting and battery fit', 'triage': 'missing_helper', 'reason': 'Requires external crate/battery proxy sizes or use-pose stack transforms not present in the exported tray layout.'}
- `missing_helper` x1: {'relationship': 'DeWalt battery rail sliding fit and wall screw engagement', 'triage': 'missing_helper', 'reason': 'Requires external battery and screw geometry; current checks only proxy rail/hole openness on reconstructed holder geometry.'}

## Low Score Causes

`{"feature_retention<8": 3, "physical_correctness<8": 8, "printability<8": 17}`

## Count Mismatch Review Signals

`{"assembly_vs_part_count": 3}`

## Next Codex Prompt

```text
Use the evaluate-cad-reconstruction skill. Read the latest loop report. Focus on this candidate: "{'relationship': 'ball socket seating and articulation', 'triage': 'proxy_now', 'reason': 'Could be approximated by placed-instance contact/axis checks after component extraction; not implemented in this iteration.'}". Decide whether it is implement_now or proxy_now. If feasible, implement one narrow deterministic helper in cad_reconstruction_eval/physical_correctness_score.py, document it in references/physical-condition-manifests.md and references/scoring-guide.md, rerun the affected reports under outputs/reconstructions/step-to-cadquery, and summarize before/after scores. Also explain whether these unused checks are truly unused or just absent from this batch: ['part_collision', 'linear_motion_collision', 'linear_motion_clearance', 'rotation_motion_collision', 'relative_pose', 'vent_grid_open_area_proxy', 'contact_graph'].
```
