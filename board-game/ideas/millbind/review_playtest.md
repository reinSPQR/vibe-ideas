Verdict: FAIL the published rules never bind-test the one move that relocates the crank, and the resulting jam ends 41-85% of scripted games in a rule that does not exist.
Disposition: rework — `rules:turn[1]` POWER must say whether relocating the crank_gear is subject to `rules:turn[5]` TEST FOR A BIND and what happens when the crank cannot turn, and `rules:turn[7]`/`rules:end[1]` must say how a grind is paid when the granary_bin holds fewer grain_pellet than the round owes. Millbind is already published, so this is not a build decision: it is a correction to a `RULES.md` that is in buyers' hands.

## What actually shipped, and where the correction has to land

There is no `RULES.md` file in the repo or anywhere in its history. `publish.py`
generates it at upload time: `rules_markdown(idea)` (publish.py:177) renders
`idea.json`'s setup/turn/end/win text verbatim into `<slug>/RULES.md` inside the
zip, and `build_zip(..., rules=rules_markdown(idea))` (publish.py:330) is what
went to the CDN. So the published rulebook is character-for-character the text
reviewed below, and it covers neither gap.

Two consequences the owner has to hear, not just the ideator:

1. The correction requires a republish of the files, not just the page.
   `publish.py --page` rewrites the product page's story blocks;
   `--new-version` re-uploads the archive that contains `RULES.md`. Both are
   needed. `published.json` records `history_status: "draft"`,
   `published_at: 2026-08-14T09:41:40Z`, project
   `6a7ede3376c66515a8c43b58/6a7ee2bc3dd218e4ef70de9a`.
2. The product page is worse than the rulebook. Re-running `story_blocks()`
   against the shipped `idea.json` reproduces what went up: 10 blocks, `dropped
   = True`, and the turn walkthrough is cut after `A turn (4)`, which ends at
   PLACE. A reader of the page never reaches TEST FOR A BIND, THE GRIND or
   DIRECTION. The published page describes a gear-placement game with no
   legality test and no scoring step, and hands the rest off to the file in the
   zip. That is the truncation working as designed, but for this particular game
   the three sections that got cut are the game.

## The machine half

`playtest.json`, 300 games per policy per seat count, seed 7, 65s wall clock,
`pass: false`, `verdict: rules_incomplete`, 5 findings, `leaks: []`,
`sensitivity: []`, `moves.never_legal: []`, `moves.never_chosen: []`.

| batch | natural endings | undefined |
|---|---|---|
| 2p random | 133/300 | 167 (56%) |
| 2p competent (greedy) | 177/300 | 123 (41%) |
| 4p random | 45/300 | 255 (85%) |
| 4p competent (greedy) | 52/300 | 248 (83%) |

Every one of the 793 sampled `Undefined` messages is the same one. The threshold
is `MAX_UNDEFINED_SHARE = 0.15`; the worst cell is 85%.

### Finding 1 (blocking): `rules:turn[1]` POWER moves a piece with no legality test, and `rules:turn[7]` assumes the crank always turns

`rules:turn[5]` scopes the bind test to "Immediately after a PLACE or a SHIFT".
POWER is the third move in the game that changes the mesh graph, it happens at
the top of every round, and it is not named. Moving the crank_gear rewrites every
mesh edge incident to its new pin, and once inner pins hold two mutually
adjacent same-tier gears, dropping the full-height crank beside them closes a
triangle. Nothing can then undo it: adding edges cannot make a non-bipartite
graph bipartite, so every PLACE and SHIFT for the rest of the round reverts under
`rules:turn[5]`, and `rules:turn[7]` THE GRIND asks the start player to turn a
crank that physically cannot move. The rules end there.

Three things sharpen this for the rework:

- The gap is unique to POWER. I checked the yard-pin subgraph directly: the 18
  yard pins form exactly an 18-cycle, every vertex degree 2, zero triangles. So
  setup (`rules:setup[3]`, which also has no bind test) and any arrangement of
  millstones and crank alone can never bind. The rules get away with an untested
  setup by geometry, not by rule. Whatever `rules:turn[1]` is changed to say,
  the same question should be asked of `rules:setup[3]` and answered explicitly
  rather than left to the lattice.
- Staying put is always safe. `rules:turn[1]` lets the start player leave the
  crank where it is, and the graph was unbound when the last round ended, so a
  player who understands the trap can always avoid it. The 41-85% figure is what
  policies that cannot see the trap do, not a table frequency.
- But a table hits the same gap, just half a second later. The physical object
  tells a player the crank will not turn only after the crank is already on the
  new pin, and `rules:turn[1]` never tells them to test before committing and
  never says whether they may pick it back up. `notes.md` guesses "a human table
  would almost certainly catch this by feel"; what a human catches by feel is
  the jam, not the rule for undoing it.

### Finding 2 (blocking, and currently invisible): `rules:turn[7]`/`rules:end[1]`, a granary that runs short mid-payout

THE GRIND owes one grain_pellet per clockwise millstone, or two if exactly one
turned. `rules:end[1]` ends the game "at the end of the round in which the
granary_bin is emptied", which only covers a payout that exactly exhausts 28
pellets. Nothing covers a round owing 3 with 2 left.

The gate never once reached this in 1200 games, because Finding 1 always fires
first. I ran my own probe (not the gate; scripted random and one-ply greedy over
`playtest/engine.py`, with POWER restricted to non-binding pins to simulate
Finding 1 being closed) and the granary gap becomes live immediately: 1 in 1199
four-player random games and 2 in 398 four-player greedy games, roughly 0.5%,
and zero at two players. So this is not a curiosity that can wait for a later
pass. Fixing only `rules:turn[1]` republishes a rulebook that still runs out,
just at 1 game in 200 instead of 4 in 5, which is exactly the kind of defect that
survives a second gate and reaches a table.

### What the same probe says about the game underneath, which is why this is rework and not kill

With POWER restricted to non-binding pins and nothing else changed:

| | games | ended naturally | median turns | median branching | top score 0 | ties | seat win rates |
|---|---|---|---|---|---|---|---|
| 2p random | 1200 | 1200 | 30 | 49 | 49% | 53% | .503 / .497 |
| 2p greedy | 400 | 400 | 24 | 54 | 8% | 14% | .486 / .514 |
| 4p random | 1200 | 1199 | 50 | 36 | 9% | 25% | .241 / .235 / .272 / .251 |
| 4p greedy | 400 | 398 | 50 | 39 | 2% | 23% | .257 / .250 / .181 / .313 |

The game terminates, the seats are close to fair, the score separates under
one-ply play. One sentence added to `rules:turn[1]` plausibly unlocks the whole
measurement. This is a game with a hole in its rulebook, not a game whose
problem is the game, and the components and turn order are not implicated.

### Findings the gate suppressed, which are not verdicts and should not be treated as any

`playtest.py` voids seat, tie, runaway, depth, length and dead-move checks when
the undefined share is over 15%, so all of these are unmeasured, not measured-ok:

- **Seat order, `rules:setup[3]` + `rules:turn[2]`.** Two independent samples
  point the same way: the gate's 4p/competent run (n=52 decided) gives seat 3
  0.357 and seat 1 0.155, and my probe (n=398) gives seat 3 0.313 and seat 2
  0.181. Both have the last seat best. Mills are placed in seat order in
  `rules:setup[3]`, so the last seat sites its millstone with full information
  and the start player then sites the crank. This is under `MAX_SEAT_EDGE = 0.10`
  in my larger sample and I am not calling it a defect. I am saying it is the
  first thing to look at when the gate can measure again.
- **Two players under weak play is degenerate.** The gate's 2p/random tie rate is
  0.68 with a mean margin of 0.81. My jam-free probe: 49% of 2p random games end
  with every score at zero, and 53% are ties. `rules:win`'s tiebreak resolves a
  zero-zero game by "whose millstone turned clockwise on the final grind", which
  in a game where nothing ever ground is empty too, so the rules correctly land
  on "they share the win", and half of those games are draws where no grain was
  ever milled. Under greedy the same numbers are 8% and 14%. The honest reading
  is that the payout condition in `rules:turn[7]`/`rules:turn[8]` (an odd chain
  to a crank that relocates every round) is hard enough that the difference
  between a table that sees it and a table that does not is the difference
  between a game and a coin flip, and nothing in this run can say which side a
  real pair of players falls on.
- **The skill ladder produced nothing, for a mechanical reason.** `MIN_LADDER_GAMES`
  is 20; the rungs completed 11, 5, 0 and 0 games out of 60 requested. Both
  lookahead rungs completed zero. This is not "lookahead does not help": in
  `play_one` (playtest.py:344-370) an `Undefined` raised inside a policy's own
  speculative `apply_move` is caught by the same handler as one raised by the real
  move, so a greedy or Monte Carlo seat marks the game undefined the moment any
  *considered* move would reach the gap. Flat MC rolls out to the end of the game
  from every candidate, and random rollouts hit Finding 1 in 56-85% of games, so
  practically every MC turn aborts its own game. The greedy rung's 0.15 win rate
  against random over 5 games is noise from the same mechanism. Millbind currently
  has no skill measurement at all, at any rung, and it will not have one until
  Finding 1 is closed. This is worth a note to whoever owns `playtest.py`
  separately from the game: any engine with a reachable `Undefined` silently
  loses its entire ladder.

### Engine and declared-gap cross-check

`notes.md` declares two `Undefined` raises and `ASSUMPTIONS = []`. Both raises are
real gaps in the shipped text, correctly attributed, and both are reproduced
above; the engine does not guess at either. `CHOICES = {}` and `sensitivity: []`
are consistent with each other: no declared ambiguity means the flip-the-reading
machinery had nothing to run, and the four readings `notes.md` resolves in prose
(PLACE may use yard pins, the bind test covers every cluster, PASS is freely
chosen, a binding move is attempted-then-reverted) each survive inspection
against `idea.json` as single plain readings. `HIDDEN_INFO = False` matches a game
where the yard, the supply and every spindle are open. `leaks: []`.

`seed_blind` is **True** at both 2 and 4 players: `new_game` never touches the rng,
and every game of Millbind begins from the identical empty board. That is
legitimate (chess does it) but it constrains any future table run: three sessions
at one seat count are one opening played three times, and whoever writes that
report may not call them three deals.

## The table half: there is none, and the reason is the finding

No `playtest/table/` directory exists for this slug. Four attempts were made and
none produced a session file, so there are zero player quotes in this report,
zero `rules_questions`, zero `arbitrary_by_seat` series, and no answer to "did
this game get smaller as you learned it". For an already-published game that last
silence is the expensive one, and it is still silent.

**The failure is structural, not unlucky.** Measured over 400 random games per
seat count on the shipped engine: the median position offers 57 legal moves at
two players and 52 at four, the 90th percentile is 112 and 103, the maximum
observed is 118 and 110, and **400 of 400 games at both seat counts contain at
least one position over 100 moves**. At two players a quarter of all turns are
over 100. The first action of the game is the worst one: 37 pins less two
millstones and a crank leaves 34 empty pins times 3 gear types, plus 15 shift
targets, plus pass, which is 118 at two players and 110 at four. The reported
run "stopped at the first position over about a hundred moves" because that
position is turn one of every game. There is no seed, seat count or truncation of
the game length that avoids it.

**On the transport.** Eight interleaved attempts at one held-fixed 110-move
position: four buffered, all HTTP 504 at the endpoint's 60s ceiling; four
streamed, all empty body at 53-78s. Zero completions. What varied across the
eight was the transport mode; what was held constant was the position, the
endpoint and the model. The cause therefore does not live in the buffering mode,
and the 504-at-exactly-60s story does not survive the streamed arm dying at 53s.
Two further facts point away from the wire: the same transport had already
returned completions for the six setup and power turns of that game, which offer
14 to 18 moves, and 110 enumerated moves is only a few hundred tokens more prompt
than 18, so a size-triggered transport fault is implausible while a time-triggered
one requires the generation itself to be slow. I would bet on the seat, not the
wire. I would not report it as established, because the endpoint and the provider
were never varied either, and a provider-side gateway that kills long generations
is consistent with all eight data points. The experiment that settles it is one
run of the same 110-move position against a different model or provider plus the
usage numbers for the failed calls, and it has not been run. Until it is, "the
model spends its whole budget weighing the options and never emits a line" is a
hypothesis with 8/8 supporting attempts and no discriminating test behind it.

**On not truncating the move list: I agree with the call, and more strongly than
the general argument requires.** The general argument (a seat choosing from a
shortened list is playing a different game) is correct. Millbind makes it worse
than usual, because its 110 moves differ from one another only in which pin and
which tooth tier, and the entire game is the parity of the graph those two
coordinates build. A random subsample deletes exactly the structure being tested,
and a curated subsample requires an evaluation function, which is the harness
playing the game and the seat rubber-stamping it. Either way the run would have
produced a number that looked like a table result and was not one. Reporting
eight clean failures is the better outcome.

That said, the option set and its presentation are different things, and the
constraint is only on the first. Whether 110 legal moves have to reach the seat as
110 enumerated lines, or can reach it as the board plus "any empty pin, any of
three gear types", is a `table_run.py` question with no effect on what the seat is
allowed to do. I am not prescribing it. I am recording that this lens cannot
produce evidence for Millbind, or for any game with three-digit branching, until
someone answers it, and that Millbind is the second calibration case to show it.

## Where the halves disagree

There is no table to disagree with the machine here, so the disagreement is
inside the machine half, and it is worth naming because the rework will be
measured against it.

The gate says the rules run out in 4 of every 5 four-player games. The physical
object says a jammed crank is the most obvious thing that can happen on a table:
you turn the knob and it does not move. Both are true and they measure different
things. The scripted policies measure how often a player who cannot see the trap
walks into it; the object measures how quickly a player finds out they did. What
neither measures, and what `rules:turn[1]` has to answer, is what that player is
allowed to do next. The 85% is not a prediction about a table and should not be
quoted as one; the missing sentence is real regardless of the rate.

Second disagreement, same half: 2p/random has a 68% tie rate and 49% all-zero
games, while 2p/greedy has 14% and 8%. One ply of lookahead changes Millbind from
a draw machine into a game. Nothing in this run can tell you which of those two a
bought copy on a real table behaves like, and that is precisely the question the
table lens exists to answer and could not.

## Cost

- **Machine half.** 1200 batch games plus 16 completed ladder games out of 240
  requested; 10,843 recorded decisions (10,288 in batches, 555 in the ladder);
  65.0s wall clock, deadline 400s, not hit; seed 7, `--games 300 --ladder-games 60
  --mc-budget 40`. Local CPU only: 0 tokens, $0.00.
- **My own probes** (granary reachability, jam-free counterfactual, branching
  distribution, yard-ring triangle check): ~7,700 further games, local CPU, about
  5 minutes, 0 tokens, $0.00. Labelled as mine everywhere they appear; they are
  not gate output and no verdict rests on them alone.
- **Table half.** 0 games, 0 completed turns, 0 session files. 8 measured
  attempts at one position, roughly 500s of wall clock in the measured pair of
  arms alone, plus four aborted run attempts before it. Model at every attempted
  seat: `minimax/minimax-m3`. Token and dollar cost of the failed calls is
  **unknown**: a 504 and an empty stream both bill for reasoning tokens that were
  never delivered, and nothing in this pipeline captured the usage figures. That
  is a gap in the accounting worth closing before the next attempt, because the
  cheapest possible reading of eight failed calls is "free", and it is not.
