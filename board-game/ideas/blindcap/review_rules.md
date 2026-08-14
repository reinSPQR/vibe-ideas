Verdict: PASS

# Blindcap — rules-worth-playing review

Judged from `idea.json` alone. No brief, no CAD, no component/dimension judgement.

## The turn economy is the strongest thing here

Every player gets exactly 7 turns: 6 rounds of mandatory plant + one free action, then
one closing action. Three of those 7 actions must be crowns if you want all three crowns
on the board, leaving at most 4 probes. At 4 players that is 4 x 4 = 16 probes against a
16-pin supply — exactly sufficient, so the pin heap only bites when someone deliberately
skips a crown to over-probe. That is a tight, deliberate economy and it makes the central
tension real: information costs the same resource as commitment, and you can never have
both on the same turn.

## Dominant strategy: none found

Walked openings for both 2p and 4p.

- **Spread out and stay unreadable.** Plant all six stools non-adjacent. Every stool is a
  grove of 1, worth 1 (2 if scarce). Three crowns yield 3-6 points. Self-defeating, so
  concealment alone is not a strategy — you are forced into adjacency to score.
- **Build your own pair.** Each player owns at most 2 of any species (2/2/1/1). So a
  player acting alone can build a grove of at most 2 — worth 4 uncontested. Every grove of
  size 3 or more *necessarily* mixes stools from two or more players. This is the
  structural fact that makes the game work: you cannot score big without depending on
  material whose identity you must buy, and buying it publicly.
- **Chase the biggest n.** Deadhead is the most common species (4 on board at 2p, 8 at 4p)
  so it has the highest theoretical n, and the x2 for scarce species does not compensate
  (8 deadheads = 64 vs 4 inkcaps = 32). But an 8-deadhead orthogonal grove requires all
  four players' deadheads to connect and only one player to crown it — unreachable in
  practice. Realistic groves are 2-4, where the scarce x2 is competitive (an inkcap pair
  is 8, equal to a common 3-grove's 9). The scoring curve is not degenerate at achievable
  n.
- **Hoard crowns to contest last.** Cannot be executed: only one action in the closing
  round, so at most one crown can be held to the end. The other two must land in rounds
  5-6 at the latest. The natural arc is probe-probe-probe-probe / crown / crown / crown,
  and the last six actions of a 2p game are an alternating crown exchange A,B,A,B,A,B.

## Contest pressure: real counterplay, watch it in playtest

Contesting is cheap — a second player's crown in a grove of n drops the owner from n^2 to
n and pays the contester n. Against a grove of 4 that is 4 points earned to deny 12. So
any grove a rival can *identify* will be contested. Two defences exist and both are
genuine decisions, not fake ones:

1. **Crown what nobody probed.** Probes are public and permanent, so you know exactly what
   each rival can and cannot resolve. Crowning an unprobed stool forces a rival to gamble
   a crown on a guess (roughly 3/11 that a given neighbour matches at 2p).
2. **Double-crown to lock.** Spending two of your three crowns on a closed 2-grove makes
   it uncontestable (a contester needs an uncrowned same-species stool). 4 guaranteed
   points for two crowns, or 8 for a locked scarce pair. Insurance versus a single crown
   on a 3-grove for 9-at-risk is a real risk/reward choice.

Watch item for playtest, not a failure: if defence (1) proves weak in practice, scores
compress into the 4-12 band and the game is decided by one surviving grove. That is a
legitimate, if low-scoring, shape — but it should be measured.

## Fake decisions

Real decisions per turn: which of your remaining stools to plant (up to 4 distinct
species, and holding your scarce stool back to place it next to a rival's is a genuine
timing play), which socket (placement both builds and denies — 18 sockets for 12 stools at
2p, so blocking matters), and which action against which target band. That is three real
choices a turn.

One soft finding: **PASS is close to dominated at 2 players.** Because you always probe a
*rival's* stool, and a 2p rival already knows their own stool's species, probing leaks
nothing to the only opponent. Probing is therefore near-free at 2p and passing is almost
never right, so the 2p turn reduces to plant + (probe early / crown late). At 3-4p pass
earns its place, since a probe on B's stool informs C and D as well, and the player who
probes hands first use of the result to the next seat. This asymmetry is a feature at 3-4p
and a mild dead option at 2p.

## Reaching an ending

Fixed length, cannot stall: plant is mandatory while stools remain, six stools means six
rounds, then one closing round, then harvest. No resource can run out in a way that
prevents termination — an empty pin heap only removes the probe action, and crowning and
passing remain legal. Scoring is total-order (highest sum, tiebreak by larger single
uncontested grove, then later seat). Ending is guaranteed and reachable.

## Length

2p: 14 turns. 3p: 21. 4p: 28. Plus a harvest that means laying out 12-24 stools and
resolving connected same-species groups, which is a real 3-5 minute step at 4p. At roughly
45-75 seconds per turn once deduction starts, 2p lands near 20 minutes and 4p near 35-40
including harvest. `playtime_min: 30` is a fair nominal, slightly optimistic at 4p. Not
mis-specified.

## Player count

Works at both ends, and 2p is arguably the *sharpest* configuration rather than the
degenerate one — the usual failure mode for this genre. At 2p you know your own six
exactly and the rival's composition is public, so the entire unknown is one player's
assignment of {D,D,B,B,I,H} to six known positions (180 arrangements), cut down by 4
public probes plus supply deduction. That is a clean, closed deduction puzzle. At 4p the
puzzle is looser but the probe-leak public-goods tension replaces it.

Two count-dependent notes:
- The pin supply (16) is not scarce at 2p (max 8 probes) or 3p (max 12). The "first come
  first served, never refilled" rule is only live at 4p.
- **Last-seat advantage.** The closing round hands the final seat the last word on the
  final crown exchange, *and* the tiebreak also favours the later seat. That is two
  compensations for one disadvantage (last pick of an empty 18-36 socket field, which is
  worth little when only two thirds of sockets are used). At 2p this means seat B responds
  to every one of A's three crowns. A's counterplay is genuine — crown stools B has not
  probed, and crown early so your own later plants can grow the grove — but the tiebreak
  going to the later seat on top of the last action should be re-examined during playtest.
  Flagged, not failed.

## Not judged here

Component geometry, the pin sink/proud legibility, socket pitch and the clearance
contract, tray sightlines. Those are the object lens and belong to a later review.
