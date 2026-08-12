# Evaluation Skill Improvement Loop

- Generated: `2026-07-09T11:12:08.052983+00:00`
- Root: `outputs/reconstructions/step-to-cadquery`
- Projects: `33`

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
| `outputs/reconstructions/step-to-cadquery/fidget-clicking-wheel-20` | 5.55 | 9.2 | 8.2 |
| `outputs/reconstructions/step-to-cadquery/filament-cutter` | 4.0 | 7.2 | 9.2 |
| `outputs/reconstructions/step-to-cadquery/final-eiffel-tower` | 4.0 | 10.0 | 9.5 |
| `outputs/reconstructions/step-to-cadquery/fractal-vise` | 2.7 | 8.0 | 8.4 |
| `outputs/reconstructions/step-to-cadquery/gravity-broom-holder` | 4.0 | 10.0 | 8.6 |
| `outputs/reconstructions/step-to-cadquery/gridfinity-1xy-multi-compartment-lidded-bins-with` | 3.2 | 8.0 | 7.4 |
| `outputs/reconstructions/step-to-cadquery/gridfinity-battery-hopper` | 9.6 | 8.0 | 8.7 |
| `outputs/reconstructions/step-to-cadquery/gridfinity-magnet-dispenser` | 10.0 | 10.0 | 9.1 |
| `outputs/reconstructions/step-to-cadquery/phone-holder` | 4.0 | 10.0 | 5.5 |
| `outputs/reconstructions/step-to-cadquery/silica-gel-spool-container` | 3.6 | 6.0 | 8.0 |
| `outputs/reconstructions/step-to-cadquery/simple-twist-open-mushroom` | 4.0 | 4.0 | 9.1 |
| `outputs/reconstructions/step-to-cadquery/spool-holder-and-drybox-for-enclosure-v2-with-humi` | 4.0 | 4.0 | 7.6 |
| `outputs/reconstructions/step-to-cadquery/tablet-and-notebook-stand` | 4.0 | 10.0 | 8.7 |

## Check Usage

- Used checks: `part_component_count, assembly_component_count, clear_path_proxy, cylindrical_fit, part_contact, feature_count, opening_presence, axis_alignment, assembly_sequence, part_clearance, vent_opening_proxy, spherical_fit`
- Unused checks: `part_collision, linear_motion_collision, linear_motion_clearance, rotation_motion_collision, relative_pose, vent_grid_open_area_proxy, contact_graph`
- Failed checks: `{"assembly_component_count": 14, "clear_path_proxy": 4, "part_component_count": 4}`

## Improvement Candidates

- `implement_now` x1: {'relationship': 'ball socket seating and articulation', 'triage': 'proxy_now', 'reason': 'Could be approximated by placed-instance contact/axis checks after component extraction; not implemented in this iteration.'}
- `implement_now` x1: {'relationship': 'full hinge rotation path for each seated joint', 'triage': 'missing_helper', 'reason': 'Needs joint-aware kinematics and placed-instance geometry; existing rotation helper is too coarse for print-in-place seated hinge knuckles.'}
- `implement_now` x1: {'relationship': 'pot drains and saucer drain grid open-area preservation', 'triage': 'proxy_now', 'reason': 'Existing vent/opening proxies could sample rays if placed component meshes or coordinates were prepared; not needed as a new helper.'}
- `implement_now` x1: {'relationship': 'tab through arm slot clearance and seated contact', 'triage': 'implement_now/proxy_now candidate but not selected', 'reason': 'Requires localized slot/tab overlap or clearance profile after component extraction; current generic distance/contact is too coarse because the tab intentionally occupies the slot.'}
- `implement_now` x1: {'relationship': 'wheel/case/spring assembled clicking articulation', 'triage': 'missing_helper', 'reason': 'The exported file is a print/customizer layout, not an assembled use pose; checking pawl compliance and wheel rotation would require use-pose transforms and spring/contact compliance.'}
- `implement_now` x1: {'relationship': 'cap insertion/removal path against body and individual insert seating', 'triage': 'missing_helper', 'reason': 'Only whole assembly STL was used; robust checks need placed body/cap/insert instance meshes. Screw-channel ray intersections also need a radius-aware channel helper to distinguish stepped bore walls from blockage.'}
- `implement_now` x1: {'relationship': 'full nested lever/lead-screw jaw motion and clamping load', 'triage': 'missing_helper', 'reason': 'Requires joint-aware kinematics and load/contact modeling from a static 80-body pose; not a narrow local helper.'}
- `implement_now` x1: {'relationship': '80 placed-solid separation vs 48 STL connected components attribution', 'triage': 'proxy_now', 'reason': 'A placed-instance export/STEP topology proxy could classify touching contacts versus accidental fusions, but CadQuery/OCP was unavailable in this sandbox and the helper would be broader than this batch.'}
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

## Low Score Causes

`{"feature_retention<8": 4, "physical_correctness<8": 9, "printability<8": 23}`

## Count Mismatch Review Signals

`{"assembly_vs_part_count": 3}`
