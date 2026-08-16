# spineward — engine notes

## Undefined

None raised. Every branch legal_moves() can reach has an explicit
precondition in idea.json, and `TURN` (rules:turn[4]) has no precondition at
all, so a seat is never left with zero legal moves — a deadlock proof that
also matches what `--quick` reported (0 stuck games in every batch).

## Assumptions

**`rob_needs_target_pearls`** (rules:turn[8]). ROB's four listed conditions
("an enemy urchin stands in a neighbouring pan, you have a spine pointing at
it, that urchin has NO spine pointing back at you, and you have an empty
socket") do not include "the target is carrying at least one pearl." If all
four hold and the target's sockets are all spines/empty, "Take any one pearl
from its sockets" has nothing to take. Chosen reading: not offered as a move
in that case (`not_legal`). Alternative wired in: legal, consumes one of your
two actions, transfers nothing (`legal_noop`). `--quick`'s tiny sample read
this as cosmetic (3% worst delta); that is not a calibrated verdict, just
confirmation the flip is actually wired to something measurable.

## Approximations / modeling choices

- **Sockets are stored indexed by the direction they currently point at**,
  not by a fixed physical socket id. Nothing in the rules ever distinguishes
  one physical socket from another, and this makes `TURN` a plain cyclic
  rotation of the list and `CREEP` a pure translation that leaves it
  untouched — exactly "keeps its facing" (rules:turn[5]).
- **Setup's pearl-seeding is played, not randomized away.** "Going clockwise
  from any player, each in turn ... stands it ... in any empty seed pan"
  (rules:setup[3]) is a real, visible (if grade-blind) placement decision, so
  it is a `setup_seed` move in the same legal_moves()/apply_move() loop as
  everything else, not something new_game() resolves for the players. The
  starting seat for that rotation is fixed at seat 0 — the rules say "any
  player," so this is a concretization of an explicitly free choice, not a
  guess, and it carries no more asymmetry than "choose a first player any way
  you like" already does for the rest of the game.
- **`LAND` (rules:turn[9]) is modeled as choosing any non-empty subset of
  currently-held pearls, up to the empty rack wells, landed in one action** —
  "you may land as many as you like" reads as a bulk choice within a single
  action, not one pearl per action. This is a faithful reading but it means a
  shelf-standing turn with many pearls aboard can offer up to 2^6-1 = 63
  `land` variants; bounded and small, but it is the single largest
  contributor to branching factor in the ladder/MC runs.
- **`scores()` is exactly the literal win-condition value at every point in
  time**: the sum of landed pearl grades, nothing else. Pearls still riding
  in a shell's sockets score zero until landed, per rules:turn[10]
  ("Pearls still sitting in your sockets are worth nothing at all"), so this
  is not a proxy, it is the rule. One consequence worth flagging: the greedy
  (1-ply) policy gets essentially no signal from `take`/`rob` themselves —
  only `land` moves change the score — so greedy's apparent strength in the
  ladder is really measuring willingness to reach a shelf, not cargo
  management. That is a property of the game's own economy, not something to
  correct for.

## Cross-check against review_rules.md

Read after writing the engine, as instructed, to compare independent
conclusions rather than to model its findings.

- **Finding 1 (six-pearl paralysis is unreachable)** — confirmed
  independently and for the same reason: `TAKE` and `ROB` both need a spine
  in one direction to reach with, and a *separate* empty direction to receive
  the pearl into. Once five sockets hold pearls and the sixth holds the only
  remaining spine, there is no direction left that is both empty and not the
  reach-spine, so `legal_moves` never offers a sixth `take`/`rob`. I did not
  special-case this; it falls straight out of the same precondition idea.json
  states for those two actions. It does mean the state described in
  rules:turn[10] ("an urchin with six pearls...") is never actually reached
  by play, which is the review's point, not mine to fix here.
- **Finding 2 (spine supply never binds)** — the engine models the true
  24-spine common pool (rules:setup[4], rules:turn[2]) with no adjustment;
  whether it ever actually runs dry under real playouts is exactly what the
  numbers in `playtest.json` will show, and is not something to correct in
  the model.
- **Finding 3 (spoiler check, clean)** — no special mechanic needed or added;
  the tie-break chain (win.text) and ROB/DROP as written already produce
  whatever spoiler dynamics the numbers show.

No disagreement between the engine and review_rules.md was found on any of
the three points.

## `observation(state, seat)` — what was removed or replaced

Added for the second hidden-information hook the contract now requires
alongside `determinize`. Every seat's hidden layer is identical (nobody,
including a pearl's own carrier, knows its grade before landing — same fact
`determinize`'s docstring already relies on), so `observation` ignores its
`seat` argument for the same reason: there is no private per-seat holding to
add back in, only a public/hidden split that is the same for everyone.

Removed from the raw `state`, entirely:

- **`pearl_grades`** (the ground-truth grade of all 16 pearls). Replaced by
  `grades`, a dict containing an entry only for pearl ids in `state["revealed"]`
  — i.e. only pearls that have actually been landed and turned over. Every
  other pearl id that appears elsewhere in the observation (sitting on a pan,
  seated in a socket, mid-carry) has no entry here at all, on purpose: a
  lookup for an unrevealed id should fail loudly rather than quietly return a
  value a real player could not have.
- **`seed_queue`** (the ordered list of pearl ids still waiting to be drawn
  and placed during setup). Replaced by `seed_pending`, a bare count. The
  draw order is a blind shake at a real table; showing the list, even with
  grades stripped, would leak which *specific* future draw comes next, which
  no player at the table can know.
- **`pearl_location`** and **`revealed`** (internal bookkeeping). Dropped
  outright rather than replaced — both are fully reconstructable from
  `pans` + `urchins` + `racks`, which are already in the observation, so
  including them again would just be the same information under a second
  name, not new information to protect or expose.

Kept as-is, because they are already public in the physical game:

- `pans` (pan type and *whether* a pearl stands there, by id — a standing
  pearl is a visible physical object; only its foot is hidden).
- `urchins` (each shell's pan and its six sockets' contents — spine, empty,
  or a pearl id — all visible on the shell from above; again, only a
  pearl's grade is hidden, not its presence or which socket holds it).
- `racks` (pearl ids landed per seat — landing is the one moment a grade
  becomes public for everyone, and `grades` now carries that value for
  every id that appears here).
- `spine_supply`, `phase`, and the various turn/phase pointers — physically
  visible or simply "whose turn is it," not hidden from anyone.

Pearl ids themselves are kept everywhere they appear (pans, sockets, racks)
as an opaque handle so a policy — or a person — can track "this is the same
physical pearl I saw two turns ago" without being told its value. This is
safe rather than a leak: the id-to-grade mapping is reshuffled fresh by
`rng` in every `new_game`, so an id carries no information about a grade on
its own, in this game or across games, until it shows up in `grades`.
