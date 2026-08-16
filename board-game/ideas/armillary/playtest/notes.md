# armillary — engine notes

## Undefined left in the engine

None. The only `raise Undefined` in `engine.py` is a defensive guard on an
unrecognised move kind, which the engine's own `legal_moves` never produces —
it exists only to fail loudly if that ever stops being true. Unlike Millbind's
crank-jam, Armillary's rules are closed: every position the turn structure can
reach (TURN, READ, REACH, BUST, BANK, CLEAR, REFILL, END) has a rule that says
what happens next, including the "stuck with nothing to take and nothing to
clear" case, which the rules leave you to resolve by simply ending your turn
with an empty catch — that is not a gap, it is the natural, only reading of
"you may take tiles" and "you may instead lift one void_tile" both being
optional.

## Assumptions declared

**`clear_repeat`** (`rules:turn[5]`, the CLEAR step). CLEAR is written as a
single substitute action — "you may **instead** lift **one** face-up
void_tile ... That well counts as empty" — offered only when the reach step
would otherwise do nothing at all. It is genuinely ambiguous whether that one
lift ends the reach step for the turn (the same way stopping or running out
would), or whether a still-stuck player may keep lifting further face-up
void_tiles, one at a time, until none remain or they choose to stop.

- `chosen`: one CLEAR ends the reach step (bank nothing caught so far,
  refill, pass to the next player) — the reading closest to "instead of"
  reaching, treated as a one-shot substitute for the whole step, matching how
  BANK and the "run out" case also end the step in one action.
- `alternative`: CLEAR is repeatable within the same stuck turn; after each
  lift the engine re-offers `clear` for the remaining face-up void targets
  plus `stop`, and the player decides when to end the turn.

`--quick`'s sensitivity pass (`board-game/ideas/armillary/playtest.json` from
the run above) reported this **cosmetic** (worst delta 5%, on an 8-20 game
sample size that is barely more than noise). It is wired — flipping
`CHOICES["clear_repeat"]` genuinely changes which wells get emptied and how
fast, so it is not a case of an unwired/inert assumption — it just did not
move the headline numbers at `--quick` volume. The full gate, run at proper
sample sizes, should be the one to say whether it stays cosmetic.

## Approximations and how they cost

- **Rotation direction collapses to net offset mod 10.** "One, two or three
  index grooves, in either direction" only ever matters through its final
  effect on which grooves a disc covers, which is a pure function of the net
  displacement mod 10. Turning a disc +3 then -1 is indistinguishable on the
  board from turning it +2 once. The engine tracks each disc's net rotation
  offset only (0-9) rather than a rotation history, which costs nothing
  observable — it is a straight simplification, not a modelling gap.
- **Reserve draw order is an arbitrary pop from an already-shuffled list.**
  Setup shuffles all 30 tiles once and deals 10 to the wells; the remaining
  20 are the reserve stack in shuffle order. Since the shuffle is uniform,
  which physical end of the reserve_column is "the top" cannot matter
  statistically, so the engine just pops from the end of the list. This is a
  proxy for "draw the top tile blind," not the tile identity itself, which
  is preserved exactly (shuffled once at setup, never reshuffled again except
  inside `determinize`'s hidden-information resampling for the lookahead
  policy).
- **`scores()` is the literal win-condition formula** (2/star, 1/moon, +1 for
  the zenith slot) applied to each player's banked tiles at any point in the
  game, not a proxy — the rules define a running score, so no approximation
  was needed there.

## Design choices that are readings, not assumptions

Two places where I judged the prose to have one clearly dominant reading, so
I did not add them to `ASSUMPTIONS` (adding a fork I am confident about would
just dilute the ones that are real):

- **A player may stop with an empty catch, even when a takeable well is
  open.** REACH says "you may now take tiles ... and after each one you
  choose to push on or stop." "May take" is permissive; nothing in the text
  requires taking at least one tile whenever one is available. `legal_moves`
  always offers `("stop",)` alongside any `("take", w)` options, including
  before the first take of a reach step.
- **BANK's "run out of open wells holding a takeable tile" is not a further
  choice.** It is handled identically to a voluntary `stop` — both just bank
  whatever is in the catch. There is no daylight in the rules between "I
  choose to stop" and "there is nothing left to take," so the engine does not
  force a spurious single-option move to represent the second case; it is
  simply the only option left, which the branching/forced-fraction stats will
  already show honestly.

## Things that turned out unreachable while writing

Nothing structural. Every declared `MOVE_KINDS` entry (`turn`, `take`,
`stop`, `clear`, `forfeit`) is reachable in principle: `clear` needs a
face-up void_tile to exist and a stuck reach step, which only arises after at
least one bust; `forfeit` needs a bust from one of the three zenith wells
(0, 4, 7) while the busting player's rail is non-empty. Both are rarer than
`turn`/`take`/`stop`, so a low-volume `--quick` run may show them chosen only
a handful of times or not at all — that is a sample-size artifact of `--quick`
(20 games), not evidence the move is dead; the full gate's larger sample is
the one that can actually say whether `clear` or `forfeit` are dead moves.

## `observation(state, seat)` — patch, fields removed or replaced

No seat holds a private hand in this game — the only concealed thing is the
shared board's face-down layer — so `observation` is identical for every
seat: everything public, and nothing else. Removed or replaced from the raw
state:

- **`wells[i]["tile"]`, for every well whose `face` is `"down"`** — replaced
  with `None`; the entry keeps `{"tile": None, "face": "down"}` so the seat
  can see *that* a well holds an unrevealed tile without seeing *what* it
  is. This is the field the whole game depends on staying hidden: any leak
  here is a cheat, not a shortcut.
- **`reserve`** (the ordered list of the 20 tiles still in the
  reserve_column, face-down) — dropped entirely and replaced with
  `reserve_count`, an integer. A player at the table can see the stack's
  height (the reserve_column's read slot is described as "a game clock
  readable across the table") but not the order or identity of what is in
  it, so a count is the honest ceiling on what that slot actually discloses.

Kept as-is, because the rules make all of it public: `rotation` (every
rotation is compulsory and public), `open_wells` (derived from `rotation`,
computable by any seat, so exposing the derived value is not a leak, just a
convenience), `wells[i]` for every face-up cell (revealed voids and returned
star/moon tiles all sit face-up on the board), `catch` (a tile joins the
catch already "turned face-up in the middle of the table for everyone to
see"), `banks` (score_rails stand in the open), `scores` (computed purely
from `banks`), and `phase`/`current`/`n_players` (turn-structure bookkeeping,
not board content).

No rule, assumption, `legal_moves`, `apply_move`, or `scores` logic changed
for this patch; `observation` is a read-only projection added alongside
`determinize`.
