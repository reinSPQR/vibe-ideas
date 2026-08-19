Verdict: PASS the rework closes the two structural holes (fixed dawn clock ends the game at 2p, inverted self-paid aperture gives the denial layer real cost), turns are decided not scripted, and 24 turns lands on the claimed 30 minutes at every player count.

# Armillary — rules review (current design)

Judged from `idea.json` as it stands now. The previous `review_rules.md` was a
FAIL against an older design (old mask patterns {0,1,2,3,4,6}/{0,1,2,3,6,7}/
{0,1,3,5,6,8}, a different ending requirement, and a rotation-before-reading
mechanic). That review is not carried forward; its three FAILs are re-checked
below as hypotheses against the current text, and every number that could be
verified over the actual components was.

## Verified numbers (exhaustive over the 100 relative rotation states)

Current solid sets: `mask_disc_a` {0,1,5}, `mask_disc_b` {0,3,6}, `mask_disc_c`
{0,2,4}. Open-well count distribution across all 100 relative rotations:

    2 open wells x 9    3 open wells x 46    4 open wells x 38    5 open wells x 7
    never 0, never 1, never > 5.   Setup state (all witness notches at 0) opens
    exactly Serpent {7,8,9} — matches the setup check "if any other set is open,
    a disc is on the wrong groove."

This claim in `idea.json` is exactly right, and it is load-bearing: the "two"
floor is what keeps the sky from ever being unplayable, and the tight 2-5 band
is what forces the game to be about WHICH wells are open, not how many.

## Old FAIL 1 (no reachable ending at 2 players) — CLOSED

Ending is now a fixed clock: `ADVANCE THE DAWN` moves one peg one socket along
a 24-socket foot flange every single turn, "no matter what anybody did," and the
game ends the instant it leaves the 24th socket. That gives exactly 24 turns and
it is immune to the old retrograde safe-set stall — no alignment pursuit can
hold a well hostage against the clock because the clock runs independent of the
discs and wells. 24 divides evenly by 2, 3 and 4 so everyone takes the same
number of turns. Nothing on the table can delay or advance it, which is
precisely the property the old review demanded ("a clock the discs cannot
veto"). Reaching an ending is guaranteed by construction.

## Old FAIL 2 (aperture-denial layer arithmetically dominated) — CLOSED, now self-paid

The mechanism is genuinely inverted as claimed: you read the sky the predecessor
left you, and `TURN THE SKY` happens at the END of your turn for the successor,
paid in your OWN next-turn reaches (1 groove -> 3 reaches, 2 -> 2, 3 -> 1; a
bust forces exactly 1 groove -> 3).

The key structural verification I ran: the open-well COUNT is nearly invariant
to how far you rotate. From a 3-open state the best sky you can hand a successor
is ~2.80 wells with a 1-groove turn and ~2.72 with a 3-groove turn; even at
g=3 you only get the successor down to 2 open wells in 17/46 states. So denial
here is NOT about shrinking the successor's open-well count (the old design's
failed arithmetic) — it is about WHICH wells (the collar constellations a public
rail shows the successor is short of). Because the count stays put, the whole
"how many" attack is gone, and the only knob left is targeted which-wells denial,
which is exactly the right shape.

Crucially the cost is now symmetric and self-internalised: rotating 3 grooves
starves only the ROTATOR (your own rail, your own next turn), not asymmetrically
crippling you for an opponent's gain the way the old 3-or-4-down-to-1 for 3-down-
to-2 swap did. There is no finger on the scale: your lost reaches and the
successor's denied value are roughly 1:1, so "how hard do I deny the next player,
at the price of my own next turn" is a real per-turn cost-benefit, not a
dominated line. The successor's collar needs, the current sky, how the dawn is
approaching, and your own score lead all move the correct answer. In particular
the dawn clock gives the rotation a clean endgame arc: early, your own reaches
are worth more (rotate gently); as dawn nears, your next-turn reaches are worth
less, so rotating hard to deny the successor's final turns becomes the rational
move. That time-dependence is the opposite of a memorisable script.

## Old FAIL 3 (turn reduces to a greedy procedure) — CLOSED, real decisions per turn

A turn of ~2 reaches now contains three live decisions that are all contingent
on table state and hidden randomness: pull-vs-take and which-well on each reach
(the press-your-luck tension, with the face-up freebie layer giving the "read the
sky" decision the old review called the one good mechanic and which is now the
index of the game), stop-vs-push on the last reach, and groove/disc/direction
for `TURN THE SKY`. None has a single always-correct answer because the correct
choice depends on public score rails, the accumulated face-up tiles, the current
sky, and remaining turns. The BUST feedback loop (bust -> forced gentle rotation
-> recover to 3 reaches, and the busted tiles stay face-up as future safe takes)
keeps the freebie economy feeding itself rather than dead-ending. I could not
find a line of play that is simply correct every time.

## Length — now correctly specified

24 fixed turns. At a modest ~1.25 min per light-medium turn that is ~30 minutes,
right on `playtime_min` 30. Because the count is turn-based (not per-player), it
scales cleanly: 12 turns each at 2p, 8 at 3p, 6 at 4p, always 24 total. The old
order-of-magnitude miscalibration (192 turns) is gone by construction. The bowl
holds 38 + 10 initial wells, comfortably more than the ~48 reach-spends a 24-turn
game can make, and the hard clock ends the game before the pool can thin to
nothing, so there is no late-game stall.

## Player count

At 2p it is directly adversarial, not solitaire: each player sets the other's
sky and immediately has it set back, so the aperture is the two-way interaction
(you aim the sky at your rival's shortest collar, and brace for the return
service). At 4p you set only your successor's sky, but the same which-wells
lever and the public collar-rail targeting keep the table interleaved. Both ends
of `players.min 2 - max 4` work.

## Residual risks for the playtest lens (not rules FAILs)

Two consequences of the verified geometry should be watched once there is an
engine, because they are balance not rules:

1. Groove effect on WELL COUNT is weak (2.7-2.8 regardless of g). The whole
   denial case rests on targeted which-wells closing being reliable enough to
   justify surrendering 1-2 of your own reaches. If in practice a successor's
   needed collar cannot be shut often enough, rotating 1 (max own reaches) could
   begin to crowd the mid-game and push the interaction to only the last few
   turns. The current numbers place real, table-contingent weight on the
   which-wells read, so this is a confirmation the playtest should measure, not
   an argument the shape is wrong.
2. At 4p a game is only 6 turns each. If turns average fewer than ~2 usable
   reaches, scoring could be thin (few complete nights). Tuning a couple of
   turns, or a slightly higher base reach, is a playtest calibration, not a
   structural defect.

## Not judged here

Components, dimensions, art direction, and the object — separate lenses, and
deliberately out of scope for a rules-worthiness read.
