# Evaluation Skill Improvement Loop - Iteration 15 Batch

- Projects root: `outputs/reconstructions/step-to-cadquery`
- Batch projects: 4
- Improvement applied: `clear_path_proxy` exact segment-bounds triangle prefilter

## Scores

| Project | Printability | Physical | Feature |
|---|---:|---:|---:|
| `outputs/reconstructions/step-to-cadquery/gridfinity-micro-sd-card-holder-1x1x3-added-step-f` | 10.0 | 10.0 | 9.2 |
| `outputs/reconstructions/step-to-cadquery/gridfinity-plain-bin` | 10.0 | 10.0 | 9.4 |
| `outputs/reconstructions/step-to-cadquery/gridfinity-screw-together-baseplate` | 10.0 | 8.0 | 8.6 |
| `outputs/reconstructions/step-to-cadquery/gridfinity-sd-card-holder` | 10.0 | 10.0 | 9.1 |

## Check Usage

- Used checks: `assembly_component_count, clear_path_proxy`
- Failed checks: `{"clear_path_proxy": 1}`

## Improvement

- Before: baseplate physical correctness was interrupted after more than 60 seconds in `clear_path_proxy` while scanning all 290,602 triangles for each sampled path.
- Change: `clear_path_proxy` now prefilters candidate triangles by the sampled segment bounding box before running the exact segment-triangle intersection test, and reports candidate triangle counts.
- After: the same baseplate manifest completed in 6.84 seconds. Physical score is 8.0 because representative magnet/screw boss axis paths failed; other batch reports remained 10.0 physical.
- Regression: focused clear-path unit tests passed with `PYTHONPATH=skills/evaluate-cad-reconstruction python3 -m unittest skills/evaluate-cad-reconstruction/tests/test_physical_correctness_score.py -k clear_path_proxy`.

## Remaining Missing Helpers / Risks
- cadquery is unavailable, so fresh render_views.py renders could not be generated; existing renders were used for plain-bin and sd-card-holder only.
- Gridfinity external mating geometry was not generated, so foot/lip fit is recorded as an external-geometry missing-helper note.
- Baseplate boss-axis clear-path samples failed; needs follow-up to distinguish actual blocked passages from proxy sensitivity around conical/counterbore transition surfaces.
