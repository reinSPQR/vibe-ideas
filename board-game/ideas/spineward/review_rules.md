Verdict: PASS

# Spineward - rules-worth-playing review

Judged from `idea.json` alone. Board geometry was checked on cube coordinates:
37 pans, 19 at radius <= 2 (the seed pans), each of the 6 corner landing
shelves touches exactly one seed pan (the ring-2 corner), and the corner-to-
corner diagonal runs shelf, r2, r1, centre, r1, r2, shelf. Every claim below
uses those numbers.

## Dominant strategy: contested, not broken

The strongest-looking opening is the straight traverse. Setup lets you place
your two spines freely, so you aim one at the corner shelf next to your
starting pan and one down the long diagonal that runs from that corner through
the centre to the opposite corner. Turn 1: CREEP onto the shelf, SHED the now-
useless spine. You are left with a single spine pointing inward and five empty
sockets. Turns 2-6: TAKE the pearl in front, CREEP into the pan it vacated -
two actions, one pearl, one pan, every turn. Turn 7: CREEP onto the far shelf
and LAND all five. Five pearls (about 8.4 points at the 1.69 mean) in seven
turns, using one spine for the whole trip, never turning, never reversing.

That line is not dominant, for two reasons that are both structural rather than
lucky.

First, the reef-empty trigger punishes it. Four traversers each lift roughly
one pearl per turn from turn 2 on; 4 x 4 = 16 takes by the end of round 5, and
the reef is bare before anyone reaches turn 7. The game stops, and pearls in
sockets score zero. The counter-line is available from turn 1: CREEP onto the
shelf and TAKE the ring-2 corner pearl, LAND it on turn 2. One point banked
before the fifth turn of anyone's deep dive. So the deep traverse loses to the
shallow shuttle whenever the table is racing, and the shallow shuttle loses to
the traverse whenever it is not. That is the actual game, and "how deep do I go
before I turn back" is a genuine read of the other three players.

Second, the traverse build is maximally robbable. One forward spine covers one
of six sides, and once the fifth pearl is aboard there is no empty socket, so
GROW - the only way to raise a shield - is illegal. The loaded urchin must
SHED then GROW (a full turn, and it loses its travel direction) or spend three
TURNs to face backwards. A chaser sitting behind it is never facing a spine and
robs for one action a turn. Robbing nets about 1.69 points per action, the best
rate in the game, but the robber still has to walk its haul to a corner, which
puts the whole loop at roughly 0.5 pearls per turn against the collector's 0.71.
Robbing is worth doing when the opportunity comes to you and is not worth
building around. That is the right shape.

The centre pan sits on all three diagonals and is a real chokepoint - whoever
reaches it first (about turn 4) blocks the other two lines and forces a GROW
plus a detour. With four players over three diagonals a collision is forced by
pigeonhole, so the traverse is contested every game at full count.

## Real decisions per turn

At least three live ones, and all eight actions have a use. Socket allocation
(each spine is a cargo slot you gave up, each pearl is a direction you gave up)
is a decision every single turn, not a build chosen once. TURN costs one action
to re-aim the whole rosette against SHED+GROW's two, so it is strictly better
for 60-degree changes and strictly worse for 180 - a real choice, not a wash.
DROP is the only way to shed cargo away from a shelf, and dropping a pearl into
the pan behind you walls off a chaser, since a standing pearl blocks CREEP.
"Which pearl to rob" is deliberately blind and is the one fake decision, which
is the point of the hidden foot.

## Ending, length, player count

The ending is reachable and in fact arrives briskly. Two triggers plus the
quiet-round clause; the reef-empty one will fire in most games. No deadlock is
possible: a player always holds at least one spine (see below), SHED always
frees a socket, GROW only needs an empty socket, and the tray cannot be empty
while that player holds none. Nobody can lock themselves out of the game.

Length: in the shallow-shuttle equilibrium roughly one action in four is a
TAKE, so about two pearls leave the reef per round and 16 pearls take about
eight rounds - 32 to 40 player-turns of two simple actions each. That lands on
the stated 40 minutes. At two players the rack cap of six ends it sooner, near
20 to 25 turns and 25 to 30 minutes, a little short of the claim.

Player count works at both ends but is not equally good. At four, six spines
per seat and three diagonals guarantee contact. At two, 37 pans for two urchins
means contact is optional and the game leans toward a parallel race decided by
the random pearl draw. Robbing and the end-trigger race keep it from being pure
solitaire, but two is the weakest seat count and the shuttle-versus-chaser
duel is the only thing holding it together.

## Findings that do not block, but should be fixed in the brief

1. The six-pearl paralysis is unreachable. TAKE, DROP and ROB all require a
   spine, so cargo can never exceed five - the maximum load is five pearls plus
   one spine, which still creeps in one direction and lands. The turn-section
   line "an urchin with six pearls cannot move, cannot reach, cannot defend
   itself and cannot even shed" describes a state the rules forbid, and the
   novelty claim that "a fully-laden one cannot move or defend itself" is
   overstated by exactly one socket. Good for the game (no self-elimination),
   wrong as written.

2. The spine supply never binds. Maximum simultaneous demand is six per seat
   and no winning build runs more than about three, so 24 spines is never
   short. Setup's "spines can genuinely run short" and GROW's "if the tray is
   empty you cannot grow" are both dead letters at every player count. The real
   constraint is the six sockets, and the text should say so.

3. Spoiler check, clean: a player who empties the reef while holding five
   scores zero themselves and cannot win on the spine tiebreak unless every
   opponent is also on zero, which cannot happen after round two. Denial is
   available, kingmaking by self-destruction is not.
