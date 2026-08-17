Verdict: FAIL at 2 players the game has no reachable ending, the aperture-denial layer the concept is built on is arithmetically dominated, and the whole turn collapses to a memorisable greedy procedure.

# Armillary — rules-worth-playing review

Judged from `idea.json` alone. Every number below was computed over the actual
mask patterns (`mask_disc_a` {0,1,2,3,4,6}, `mask_disc_b` {0,1,2,3,6,7},
`mask_disc_c` {0,1,3,5,6,8}) on the full 1000-state rotation space, not
estimated. Scripts were exhaustive searches, not samples, except where a
sample size is stated.

This idea reached `rules_ok` twice before `board-game-lens-rules` existed, so
this is its first independent rules judgement. It is currently `blocked` after
two exhausted repair budgets on the CAD. The findings below are why further
geometry repair is wasted: none of them is a geometry defect.

## First, the one claim in the idea that is TRUE

`mask_disc_c`'s description asserts that across all 100 relative rotations the
number of fully aligned wells is never 0 and never more than 4. Verified
exhaustively:

    1 open well  x14 states
    2 open wells x58
    3 open wells x26
    4 open wells x 2

So the patterns are correctly chosen. The problem is that this distribution
never reaches the table, for the reason in finding 2.

## FAIL 1 — at 2 players the game cannot end

`end` requires the reserve empty **and** no well holding a knob-up tile. A
specific well opens only when all three discs are simultaneously right for it,
and a turn rotates exactly one disc by 1-3 grooves. So the last knob-up tile
sits behind a three-disc alignment that the mover has to complete on their own
turn, with an opponent moving in between.

Retrograde analysis of that pursuit game over all 1000 states, for every one of
the ten wells, gives the identical answer:

| | |
|---|---|
| states where the mover can open well `w` in one move | 648 / 1000 |
| states the defender can hold forever, never letting that happen | **352 / 1000** |
| states from which the defender enters the safe set in one move | **784 / 1000** |

The safe set is non-empty for every well and is reachable from 78% of
positions. A trailing player at 2p therefore has a proven, permanent stall:
spend every turn breaking whichever disc the leader just set, and the game
never reaches its end condition. There is no clock, no forced reveal and no
pass limit to overrule it. CLEAR does not help — it is legal only when no open
well holds any takeable tile, and a knob-up tile IS takeable, so the one rule
that removes a blockage is unavailable in exactly the position that needs it.

At 3 and 4 players the same analysis returns a safe set of **0 / 1000**: one
defender cannot hold the line against two attackers moving between its turns.
This is a two-player-only hole, but 2 is inside the declared `players.min`.

## FAIL 2 — the denial layer, which is the entire pitch, is dominated

`concept` says "the disc you leave badly turned is the sky the next player has
to work with". `novelty` says "rotating a disc sets both your own reach ceiling
for a press-your-luck run and the next player's, so denying the table is an
attack". Neither survives contact with the numbers.

Because the rotation is compulsory and happens *before* you read, the mover
always self-selects. Distribution of open wells at the moment a player actually
reaches, over all 100 relative states:

    2 open wells  x 2      3 open wells x66      4 open wells x32

Never 1. The "typically 2" the mask patterns were tuned for is never what
anybody plays against.

Now the attack. If I take the move that is best for me, my opponent still gets
3 open wells in 96 of 100 states and 4 in the other 4. I cannot cost them
anything by playing well. If I deliberately sacrifice my own turn to hurt them:

- it works in only 32 of 100 states,
- it moves them from 3 open wells down to 2,
- and it costs me **my own count dropping from 3 or 4 to exactly 1**.

Every state where denial is possible has that same shape: I give up two or
three pulls to take away one of theirs. There is no state anywhere in the space
where denial is worth playing. The interactive half of this game does not
exist; what is left is four players taking parallel turns at a shared random
pool.

## FAIL 3 — the turn is a procedure, and it is the Deep Claim failure again

With denial dead, the whole turn reduces to a rule a player learns once:

1. Rotate to whichever of the 18 reachable states maximises reachable value.
2. Pull from plain wells before zenith wells.
3. Keep pulling while your catch is below the threshold: with the full pool
   (12 star / 10 moon / 8 void) that is **4.25 points**, rising to 5.20 once
   the pool thins to 9/8/5 and 5.67 at 6/5/3. One number, memorisable.
4. Take face-up freebies **last**, never first — a bust returns everything in
   the catch, so hoovering the free tiles early puts them at risk for nothing.

Steps 2 and 4 are gotchas rather than decisions: there is exactly one right
answer and it never changes. Step 3 binds only on the last pull of a 3- or
4-well turn. `TASTE.md` records the owner killing Deep Claim for "an optimal
strategy ... that can be easily figured out". This is the same object with more
variance painted on it.

The one genuine decision in the game arrives late and by accident: once busts
have left face-up star/moon tiles in wells, the rotation becomes a real
comparison between guaranteed freebie points and unknown pull EV. That is a
good mechanism and it is the only thing here worth keeping.

## Length — mis-specified by roughly an order of magnitude

`playtime_min` is 30. My own greedy simulation put a game at 180-210 turns.
`playtest.py --quick` (20 games per seat count, independent engine, written by
`board-game-rules-engineer` from the same `idea.json`) reports:

    2p  20/20 finished, 192 turns, 4.0 moves/turn (16% forced), best seat 55% vs 50% fair
    4p  20/20 finished, 186 turns, 4.0 moves/turn (15% forced), best seat 30% vs 25% fair

192 turns at 2p is 96 turns per player, each of them a disc rotation plus one
to three pulls. The lens brief names this exact failure: "A game claiming 30
minutes that needs 200 turns is mis-specified."

The same run returns `PLAYTEST FAIL rules_ambiguous`, on `rules:turn[5]`:
whether a stuck player may CLEAR more than one face-up `void_tile` in the same
turn. Playing it the other way moves the numbers by 22%, so that sentence is
not a detail, it is a rule the game does not currently contain.

Its ladder rungs are all n=8 and the tool itself discards them from the depth
check, so they are recorded here without weight: `greedy vs random` 12%,
`lookahead vs greedy` 50%, `lookahead vs random` 31% against a 25% fair share.

## What a rework has to change, in priority order

1. **Give the ending a clock the discs cannot veto.** Anything that terminates
   independently of alignment — the reserve running dry ending the game on its
   own, a fixed number of rounds, or an open well counting as cleared. As
   written, "no well holds a knob-up tile" is a condition one player can deny
   forever, and no amount of rewording the aperture fixes that.
2. **Either make denial pay or stop claiming it.** The compulsory rotation
   cannot both maximise the mover's own reach and constrain the next player's,
   because the next player rotates again before reading. Splitting those — the
   mover sets the sky for the *next* player and reads the one they were left,
   is the obvious shape and it inverts the whole game — would make the pitch
   true. Half-measures will not: the current numbers say the attack is 3-or-4
   down to 1, for 3 down to 2.
3. **Cut the run length by roughly 6x.** 192 turns for a claimed 30 minutes.
4. **Answer the CLEAR question in the rules text**, one way or the other.
5. **Keep the freebie layer.** Face-up tiles in wells are the one place where
   reading the sky is a real read. Build the game around that instead of around
   the alignment count.

A caution for whoever reworks this: findings 1 and 2 are both consequences of
component arithmetic — three 6-of-10 masks moved one disc at a time by 1-3
grooves — not of how the rules are worded. A rework that keeps that mechanism
and rewrites the prose will come back here with the same numbers.

## Not judged here

Components, dimensions, the two exhausted CAD repair rounds, art direction.
