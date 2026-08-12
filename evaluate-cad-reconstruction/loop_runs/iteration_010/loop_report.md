# Evaluation Skill Improvement Loop

- Generated: `2026-07-09T09:53:07.192602+00:00`
- Root: `outputs/reconstructions/step-to-cadquery`
- Projects: `13`

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
| `outputs/reconstructions/step-to-cadquery/phone-holder` | 4.0 | 10.0 | 5.5 |
| `outputs/reconstructions/step-to-cadquery/silica-gel-spool-container` | 3.6 | 6.0 | 8.0 |
| `outputs/reconstructions/step-to-cadquery/simple-twist-open-mushroom` | 4.0 | 4.0 | 9.1 |
| `outputs/reconstructions/step-to-cadquery/spool-holder-and-drybox-for-enclosure-v2-with-humi` | 4.0 | 4.0 | 7.6 |
| `outputs/reconstructions/step-to-cadquery/tablet-and-notebook-stand` | 4.0 | 10.0 | 8.7 |

## Check Usage

- Used checks: `part_component_count, assembly_component_count, clear_path_proxy, part_contact, cylindrical_fit, feature_count, opening_presence, part_clearance, axis_alignment, assembly_sequence`
- Unused checks: `part_collision, linear_motion_collision, linear_motion_clearance, rotation_motion_collision, relative_pose, vent_opening_proxy, vent_grid_open_area_proxy, contact_graph`
- Failed checks: `{"assembly_component_count": 6, "clear_path_proxy": 2, "part_component_count": 3}`

## Improvement Candidates

- `implement_now` x1: {'relationship': 'ball socket seating and articulation', 'triage': 'proxy_now', 'reason': 'Could be approximated by placed-instance contact/axis checks after component extraction; not implemented in this iteration.'}
- `implement_now` x1: {'relationship': 'full hinge rotation path for each seated joint', 'triage': 'missing_helper', 'reason': 'Needs joint-aware kinematics and placed-instance geometry; existing rotation helper is too coarse for print-in-place seated hinge knuckles.'}
- `implement_now` x1: {'relationship': 'pot drains and saucer drain grid open-area preservation', 'triage': 'proxy_now', 'reason': 'Existing vent/opening proxies could sample rays if placed component meshes or coordinates were prepared; not needed as a new helper.'}
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
- `missing_helper` x1: thread fit, cap/body screw engagement, silica containment, and fit inside a spool core need helpers/external proxies not implemented
- `missing_helper` x1: body/cap vs filament spool core: contains/fits; external spool proxy missing
- `missing_helper` x1: external spool/enclosure, humidity sensor, hinge/latch behavior, strength, and mounting loads are unmeasured
- `missing_helper` x1: drybox vs spool/enclosure: contains/supports/mounts; external objects missing

## Low Score Causes

`{"feature_retention<8": 2, "physical_correctness<8": 7, "printability<8": 11}`

## Count Mismatch Review Signals

`{"assembly_vs_part_count": 3}`

## Next Codex Prompt

```text
Use the evaluate-cad-reconstruction skill. Read the latest loop report. Focus on this candidate: "{'relationship': 'ball socket seating and articulation', 'triage': 'proxy_now', 'reason': 'Could be approximated by placed-instance contact/axis checks after component extraction; not implemented in this iteration.'}". Decide whether it is implement_now or proxy_now. If feasible, implement one narrow deterministic helper in cad_reconstruction_eval/physical_correctness_score.py, document it in references/physical-condition-manifests.md and references/scoring-guide.md, rerun the affected reports under outputs/reconstructions/step-to-cadquery, and summarize before/after scores. Also explain whether these unused checks are truly unused or just absent from this batch: ['part_collision', 'linear_motion_collision', 'linear_motion_clearance', 'rotation_motion_collision', 'relative_pose', 'vent_opening_proxy', 'vent_grid_open_area_proxy', 'contact_graph'].
```
