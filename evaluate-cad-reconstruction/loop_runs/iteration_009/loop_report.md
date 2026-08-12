# Evaluation Skill Improvement Loop

- Generated: `2026-07-09T09:46:09.758464+00:00`
- Root: `outputs/reconstructions/step-to-cadquery`
- Projects: `9`

## Scores

| Project | Printability | Physical | Feature |
|---|---:|---:|---:|
| `outputs/reconstructions/step-to-cadquery/3d-printable-jet-engine` | 0.4 | 6.2 | 8.6 |
| `outputs/reconstructions/step-to-cadquery/5015-radial-fan-3d-model-for-conception-step-stl-f` | 9.2 | 8.0 | 8.4 |
| `outputs/reconstructions/step-to-cadquery/all-in-one-temperature-bridging-tower` | 4.0 | 9.2 | 9.2 |
| `outputs/reconstructions/step-to-cadquery/arduino-uno` | 9.9 | 10.0 | 8.8 |
| `outputs/reconstructions/step-to-cadquery/phone-holder` | 4.0 | 10.0 | 5.5 |
| `outputs/reconstructions/step-to-cadquery/silica-gel-spool-container` | 3.6 | 6.0 | 8.0 |
| `outputs/reconstructions/step-to-cadquery/simple-twist-open-mushroom` | 4.0 | 4.0 | 9.1 |
| `outputs/reconstructions/step-to-cadquery/spool-holder-and-drybox-for-enclosure-v2-with-humi` | 4.0 | 4.0 | 7.6 |
| `outputs/reconstructions/step-to-cadquery/tablet-and-notebook-stand` | 4.0 | 10.0 | 8.7 |

## Check Usage

- Used checks: `part_component_count, clear_path_proxy, assembly_component_count, part_contact, feature_count, opening_presence, cylindrical_fit, part_clearance, axis_alignment, assembly_sequence`
- Unused checks: `part_collision, linear_motion_collision, linear_motion_clearance, rotation_motion_collision, relative_pose, vent_opening_proxy, vent_grid_open_area_proxy, contact_graph`
- Failed checks: `{"assembly_component_count": 3, "clear_path_proxy": 2, "part_component_count": 3}`

## Improvement Candidates

- `implement_now` x1: vent holes/grilles: opening presence could be sampled but is unreliable on highly perforated non-watertight STL
- `implement_now` x1: dot/eye inserts vs body sockets: clearance-fit/contact/glue seating, missing socket proxy/clearance helper
- `implement_now` x1: Snap/press-fit compliance for bracket slots and beam tabs is not implemented.
- `implement_now` x1: Full folding motion path for the linkage needs joint-aware kinematic helpers; current rotation helper is too coarse for seated hinge geometry.
- `proxy_now` x1: body vs cap: cylindrical/threaded fit and rotation-motion; current helper cannot validate helical thread
- `proxy_now` x1: cap/body pairs: rotation-motion/thread or bayonet engagement, missing twist-cam helper
- `proxy_now` x1: True screw thread engagement and torque retention are not implemented.
- `proxy_now` x1: Load-bearing stiffness, tipping stability, and device weight support are not implemented.
- `missing_helper` x1: thread fit, cap/body screw engagement, silica containment, and fit inside a spool core need helpers/external proxies not implemented
- `missing_helper` x1: body/cap vs filament spool core: contains/fits; external spool proxy missing
- `missing_helper` x1: external spool/enclosure, humidity sensor, hinge/latch behavior, strength, and mounting loads are unmeasured
- `missing_helper` x1: drybox vs spool/enclosure: contains/supports/mounts; external objects missing
- `missing_helper` x1: sensor window vs humidity sensor: clearance-fit; external sensor proxy missing

## Low Score Causes

`{"feature_retention<8": 2, "physical_correctness<8": 4, "printability<8": 7}`

## Count Mismatch Review Signals

`{"assembly_vs_part_count": 3}`

## Next Codex Prompt

```text
Use the evaluate-cad-reconstruction skill. Read the latest loop report. Focus on this candidate: 'vent holes/grilles: opening presence could be sampled but is unreliable on highly perforated non-watertight STL'. Decide whether it is implement_now or proxy_now. If feasible, implement one narrow deterministic helper in cad_reconstruction_eval/physical_correctness_score.py, document it in references/physical-condition-manifests.md and references/scoring-guide.md, rerun the affected reports under outputs/reconstructions/step-to-cadquery, and summarize before/after scores. Also explain whether these unused checks are truly unused or just absent from this batch: ['part_collision', 'linear_motion_collision', 'linear_motion_clearance', 'rotation_motion_collision', 'relative_pose', 'vent_opening_proxy', 'vent_grid_open_area_proxy', 'contact_graph'].
```
