# review_playtest — deep-claim

Verdict: FAIL All four players independently reported the second half of every game had no decision in it, and the breaker showed the result is fixed by component arithmetic and seat order before the first puck is placed.

## The run

Five games, all finished by agent players. No `--agent-turns`, no scripted
seats, no handovers: every session file has `handed_over_at: null` and every
recorded move has `"by": "player"`.

| game | seats | seed | seat 0 | seat 1 | seat 2 | seat 3 | decisions | result |
|---|---|---|---|---|---|---|---|---|
| g1 | 4 | 11 | A | B | C | **D (breaker)** | 12 | winners [0, 1], scores 5/5/4/4 |
| g2 | 4 | 23 | **D (breaker)** | A | B | C | 12 | winners [0, 1], scores 5/5/4/4 |
| g3 | 4 | 37 | B | **D (breaker)** | C | A | 12 | winners [0, 1], scores 5/5/4/4 |
| g4 | 2 | 51 | **D (breaker)** | A | — | — | 12 | winners [0, 1], scores 9/9 |
| g5 | 2 | 67 | A | **D (breaker)** | — | — | 12 | winners [0, 1], scores 9/9 |

Four `board-game-player` agents were spawned once, at the start, and carried
through every game by `SendMessage`. A and D played all five; B and C played
the three 4-player games only. The breaker's seat was rotated deliberately so
that it sat in seat 0 once at each player count.

Sessions replay from
`board-game/ideas/deep-claim/playtest/table/g{1..5}.json`.

**The seeds do nothing.** `engine.new_game` takes `rng` and never uses it —
there is no randomness anywhere in this game. g1, g2 and g3 dealt byte-identical
opening positions. The seeds are recorded above for form; a reader replaying
any of these games will get the same board with any seed.

**One contamination, disclosed.** Player D (the breaker) used its `Read` tool
to open `board-game/ideas/deep-claim/playtest.json` before its first move of
game 1. It therefore played all five games and gave both its debriefs knowing
the harness's seat-bias, tie-rate and sensitivity findings. I told it to stop
before game 2 and it made no further reads. Its *play* was indistinguishable
from the uncontaminated players' throughout, and its arithmetic arguments are
checkable and check out, but any place below where D's report echoes a
`playtest.json` finding should be read as an echo, not as independent
corroboration. Where I rely on D, I say so and note whether B, C or A said the
same thing without having read anything.

## Rules questions raised in play

**No player emitted a single `RULES QUESTION` line in 60 decisions.** Two said
so explicitly when asked:

> "Nothing in the rules was ambiguous enough to raise a RULES QUESTION; the
> problem was entirely in how few of my turns had more than one meaningfully
> different option." — Player C, final debrief

> "Nothing broken in the rules text itself" — Player B, final debrief

That matches `playtest/notes.md`, which declares **no `Undefined`** and one
assumption. Nothing new of that kind came out of the table.

One near-question, the only thing a player had to work out rather than read:

> "Nothing genuinely ambiguous; the one thing I had to work out myself rather
> than read off the rules text was whether placing a large puck on a bore whose
> floor is already claimed is a 'free' point (yes — rule 2 only checks the
> shelf's emptiness, not the floor's status), which the rules state clearly
> enough on a close read, just not obviously." — Player A, final debrief,
> concerning `rules:turn[2]`

Reading A went with: yes, it is a free point. This is a legibility complaint
about `rules:turn[2]`, not a gap, and it is **not new** — it is the same
sentence `notes.md` already flags for a different reason.

### What is new: the declared assumption is not a corner case

`notes.md` declares one assumption, `floor_burial` at `rules:turn[2]`, and
`playtest.json` scores it `blocking` with `worst_delta 0.2153` on a runaway
statistic. The table found something the aggregate number does not say.

Every one of the 30 large-puck placements across the five games sealed a shelf
over a floor that was **already claimed**. Not one large puck in 60 decisions
was ever placed over an unclaimed floor, at either player count, by any of the
four players. The burial condition was therefore live on 100% of large
placements, i.e. on exactly half of every game — it is the normal case under
the line every player independently converged on, not an edge case.

Replaying the five recorded sessions with `CHOICES["floor_burial"] =
"alternative"` and no other change:

```
g1 alternative reading -> scores [1.0, 1.0, 2.0, 2.0] winners [2, 3]
g2 alternative reading -> scores [1.0, 1.0, 2.0, 2.0] winners [2, 3]
g3 alternative reading -> scores [1.0, 1.0, 2.0, 2.0] winners [2, 3]
g4 alternative reading -> scores [3.0, 3.0] winners [0, 1]
g5 alternative reading -> scores [3.0, 3.0] winners [0, 1]
```

At four players the reading does not shift the game by 21.5% of anything; it
**inverts the winner set completely**, from the two earliest seats to the two
latest, in all three games. At two players it leaves the draw a draw. Whoever
settles this sentence is not tuning a statistic, they are choosing which pair
of seats wins every 4-player game. That specificity is new; the ambiguity
itself is not.

(Player D also named this ambiguity, in its game-1 debrief — but it had read
`playtest.json`, so that mention is worth nothing. The 30-out-of-30 count and
the winner inversion above come from the session files, not from a player.)

## Turns with no decision in them

`ARBITRARY yes` rate, self-reported, per player:

| player | arbitrary | turns | rate |
|---|---|---|---|
| A | 10 | 21 | 48% |
| B | 8 | 9 | 89% |
| C | 6 | 9 | 67% |
| D (breaker) | 17 | 21 | 81% |
| **table** | **41** | **60** | **68%** |

The distribution is not scattered. In **all five games** the final six of the
twelve decisions — turns 6 through 11, every seat, without exception — were
flagged arbitrary by whoever was sitting there:

```
g1  0A.  1B*  2C.  3D.  4A.  5B.  6C*  7D*  8A*  9B* 10C* 11D*
g2  0D.  1A.  2B*  3C.  4D*  5A.  6B*  7C*  8D*  9A* 10B* 11C*
g3  0B*  1D*  2C.  3A.  4B*  5D.  6C*  7A*  8B*  9D* 10C* 11A*
g4  0D*  1A.  2D*  3A.  4D*  5A.  6D*  7A*  8D*  9A* 10D* 11A*
g5  0A.  1D*  2A.  3D*  4A.  5D.  6A*  7D*  8A*  9D* 10A* 11D*
                                   ^-- from here, every turn, every game
```

The point at which it flips is the same in every game: the turn after the
sixth and last floor is claimed. From there the board is six bores with
claimed floors and open shelves, every remaining move is worth exactly +1, and
the number of remaining shelves equals the number of remaining turns, so every
player's final score is already fixed. Nobody has to be told this; all four
players worked it out separately and said so in their WHY lines.

One, from game 1 turn 8, Player A:

> "exactly four turns remain for exactly four open shelf slots (everyone still
> has large pucks to spend), so each of us is guaranteed +1 regardless of which
> specific bore we pick — the choice among these four is interchangeable in raw
> score"

The last turn of every game had exactly one legal move.

The first six turns are not much better. They are all "take a 2-point floor
rather than a 1-point shelf", with the only variation being *which* symmetric
empty bore, which several players also flagged arbitrary. Player C, who never
read anything, put its whole game at one decision:

> "Only ever turn 2 of each game ...: the choice to grab an open floor with a
> small puck before rivals did. Every later turn in all three games had zero or
> one legal move, all equal-value."

## What the breaker found

Player D never found a winning line, and after five games said plainly that
none exists. Its account, which I have checked against the sessions:

> "Neither a forced win nor a coincidence — a forced draw-among-the-favored-
> share by pure arithmetic. At 4p, 6 bores mod 4 players leaves a remainder of
> 2, and turn order hands that remainder to the two seats that act first in
> rotation (seats 0 and 1 here, every game), so they tie at 5 and the other two
> tie at 4, regardless of any decision either pair makes. At 2p, 6 floors and 6
> shelves both divide evenly by 2 players, so greedy play mechanically splits
> 3-3 and 3-3 for a 9-9 draw no matter who moves first."

It ran exactly one probe against the draw, by hand, in game 4: spend a large
puck early to seal a bore whose floor nobody had claimed yet — the denial play
the concept text advertises. It reported the probe strictly losing, and did not
play it:

> "it burns scarce large-puck ammunition for 1 point and leaves you short in
> the endgame shelf race."

I traced that line independently on the game-4 position at turn 4 and it is
right: sealing bore 5 there gives 7-9 to the opponent instead of 9-9, because
the denier ends the game holding an unplayable small puck while the opponent
places all three larges. Player A, in seat 0 of game 5 and with no knowledge of
D's reasoning, ran its own hand-simulation of the same family of gambits and
reached the same conclusion at game 5 turn 4:

> "I tried working through a few sealing deviations by hand (seal now vs. seal
> later vs. bank an early shelf) and each one still canceled out to an exact
> tie against a mirroring opponent"

So: nothing to defend against, because there was nothing to attack with.
Putting the breaker in seat 0 (g2, g4) changed nothing — the score line was
identical. The breaker never won a game outright and never made another player
respond to it. Its own summary:

> "No, I never deviated from greedy after that one probe, because I could show
> the probe losing by hand ... The other side never had to respond to me; both
> of us were just executing the same forced allocation."

The denial mechanic named in the concept — "whether your last broad puck is
worth spending to deny a rival's future floor claim" — was never once correct
to play in 60 decisions, at either player count. Three of the four players
raised this unprompted as the thing they wanted and could not have. B and C
both reached it without reading anything.

## Whether anybody wanted a second game

Asked after game 1, before anyone knew the pattern would repeat, three of four
said yes with a caveat and one said yes outright. Asked at the end, after
seeing it repeat:

> "Two players: no — I proved by hand that with matched pucks-to-slots supply,
> mirrored greedy play is a structural draw, and every deviation I tried also
> drew; there's no game left to find there. Four players: mildly yes, but only
> if the design fixes the fact that the last several turns per game were
> mathematically forced +1-for-everyone sequences with zero decision content."
> — Player A

> "Two players: yes, once, out of curiosity whether a non-greedy or error-prone
> opponent breaks the draw — but expect a draw against any competent opponent.
> Four players: no. The outcome is fixed by seat order before anyone picks up a
> puck, and I've now seen it land on the identical score line three times
> running." — Player D (breaker)

> "I would not choose to play it again at four players. All three games at 4p
> flattened into 'race the six floors turns 0-5, then place arbitrary large
> pucks turns 6-12' with zero contested decisions in the second half." —
> Player B

> "I would not choose to play this again at four players. The whole game
> compresses into one real decision (turn 2's floor race) followed by 4-5 turns
> of forced or interchangeable large-puck placement." — Player C

Nobody wanted a second game at four players. Two players said "once more, out
of curiosity", both meaning curiosity about whether an opponent would blunder.

The unflattering ones, in full:

> "Twelve components, twelve slots (2p) or six bores split unevenly across four
> seats (4p) is math, not play; nothing I chose in the second half of any of
> these five games mattered." — Player D

> "with four players and six bores, turn order alone decided the outcome all
> three games (seats 0 and 1 won every time, seats 2 and 3 lost every time,
> identical 5-5-4-4 scoreline each game) — that's a strong signal the four-
> player mode is structurally unfair to later turn order, not a playtesting
> fluke." — Player C

> "I lost by 1 point purely because I was seat 2, further from first pick, so I
> got fewer floor turns. That is a seating-order effect, not a decision I failed
> to make." — Player B

## Where the numbers and the table disagree

Mostly they agree, and the agreement is damning rather than reassuring:
`playtest.json` reports `tie_rate 1.0` at both counts under competent play and
per-seat win rates of `[0.5, 0.5, 0.0, 0.0]` at 4p; the table produced 5 ties
in 5 games and seats 0 and 1 sharing all three 4-player games. Three real
disagreements:

1. **The ladder looks like depth; the table found none.** `playtest.json` has
   `lookahead` at 63% against a random field versus `greedy` at 59%, which
   reads as "looking ahead helps a little". At the table, four players
   converged on the identical one-ply heuristic by their second or third turn
   and never found a reason to deviate, and the two who tried search (A and D,
   independently, by hand) both reported every deviation converging back to the
   same tie. The ladder's own `lookahead vs greedy` row already says this —
   25.0% against a fair share of 25% — and the table is the confirmation that
   the 63% number is only measuring "beats a player who moves at random".

2. **Twelve decisions, six of which exist.** The `length` finding reasons about
   "12 decisions at 4 players ... 2 to 5 minutes". The table says the last six
   of those twelve are not decisions at any seat in any game. Whatever this
   game is, it is a six-decision game with a six-turn scoring ritual attached,
   against a claimed `playtime_min` of 20.

3. **The sensitivity delta understates the ambiguity.** `worst_delta 0.2153` on
   `runaway` sounds like a tuning knob. Replayed on the actual games, the
   alternative reading of `floor_burial` inverts the 4-player winner set from
   seats [0, 1] to seats [2, 3] in all three games. Same rule, same games,
   opposite winners. I am not picking a reading — that is exactly what this
   stage must not do — but the harness's summary number does not convey that
   this sentence chooses the winner.

   *Acted on, 2026-08-16.* The cause was that every measure the sensitivity
   check compared reads the game in aggregate, and `seat_edge` reads only the
   best seat, so swapping which seat wins moved none of them: it scored the
   flip at 2.5%. `run_sensitivity` now also compares the whole win-share
   vector, and on the same 300 games the same flip scores 55.3%, which is what
   `worst_delta` reports. The number in the paragraph above is the one the
   harness gave on the day, and it is left standing because it is the reason
   the harness changed.

One place where I will not resolve a contradiction: `playtest.json` records
`dead_move:pass` — the rules define a pass that was never legal in any of 600
scripted games. It was never legal in any of our 60 player decisions either,
including the 2-player games where `notes.md` predicted it was most reachable.
The players never noticed the rule existed, because the engine never offered
it. Whether that is a rules defect or a components-arithmetic defect is not a
question the table can settle.

## Why FAIL

Not for being quiet. For three things the table found that a brief should not
be written on top of:

- **Every player, independently, reported there was nothing to decide.** 68%
  self-declared arbitrary across the run, and the final six turns of all five
  games arbitrary at every seat without exception. Two players who read nothing
  and had no contact with each other said "one real decision per game" in almost
  the same words.
- **The outcome is determined before play.** Three 4-player games produced the
  identical score line 5/5/4/4 with the identical winner set, across three
  different seatings of four different players; two 2-player games produced
  9/9. The breaker's arithmetic accounts for all five and was independently
  reproduced by a second player.
- **The advertised decision is unreachable.** "Whether your last broad puck is
  worth spending to deny a rival's future floor claim" was never correct to
  play in 60 decisions, and three players named its absence unprompted.

None of that is a rules gap that made a game unplayable, and there is no line
that wins every game — there is no line that wins any game. The FAIL is on the
third ground in the brief: every player independently reporting there was
nothing to decide.
