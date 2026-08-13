# Armillary — build brief

Nine parts, one tile each, nothing tiled: the largest single part (a tier
disc with its grip tab) is 206 x 190 x 10mm, well inside the 246 x 246 x
251mm bed. Composed almost entirely from `blocks.py`: `shared_positions` for
the one 8-position ring every layer must agree on, `cut_wells` for the eight
plinth sockets, `seated_pair`/`peg_for` for the axle-post-in-bore fit,
`add_piece_family` for the four peg families.

## Parts

**plinth_axle** (qty 1, `board`, 190 x 190 x 62mm) — the fixed base. A
190mm-diameter, 22mm-tall drum topped by a 40mm-tall, 12.2mm-diameter axle
post standing on its center. Eight 14mm-diameter, 10mm-deep sockets are sunk
around a 75mm-radius ring on the top face (12mm of material remains below
each socket floor). The rim carries eight 1mm-deep index grooves at the same
8 angular positions as the sockets; the top face between sockets carries a
0.8mm relief constellation-dot motif. Build the socket ring, the groove ring,
and every disc's window ring from **one** shared 8-position, 75mm-radius
point list — never restate the angles per part.

**tier_disc_a / tier_disc_b / tier_disc_c** (qty 1 each, `loose_piece`, each
206 x 190 x 10mm) — three identical-diameter, identical-thickness (190mm x
10mm) discs that stack directly on the axle post, in that order (a on the
plinth, b on a, c on top). Each has a 13mm center bore (axle post is 12.2mm,
a 0.4mm-per-side free-spin clearance so it turns without binding) and three
9mm windows pierced at three of the eight shared ring positions — a
different fixed pattern per disc, which is the entire game mechanism. Told
apart by touch alone by grip-tab shape, not by any dimension:
tier_disc_a is a rounded paddle, tier_disc_b a pointed triangular fin,
tier_disc_c a notched double-prong; all three tabs are 18mm wide and project
16mm past the rim (only tier_disc_a's width was given in the idea — b and c
are set to match it so no disc is harder to grip than another). Each disc
carries its own shallow 1mm witness notch on its rim to read its position
against the plinth's index grooves by touch. Setup rotates each disc to a
fixed starting offset counted in grooves: tier_disc_a 2, tier_disc_b 4,
tier_disc_c 6.

**marker_peg_tri / _square / _penta / _hex** (qty 4 each, `loose_piece`,
each ~11 x 11 x 20mm) — four peg families, told apart purely by prism
cross-section (triangular / square / pentagonal / hexagonal), each with a
domed grip top. Each drops into any empty plinth socket (14mm opening around
an 11mm base — 1.5mm clearance per side, well past the 0.4mm minimum) and
stands 10mm proud of the socket rim once seated, which is what makes a
planted peg both obviously claimed and easy to pull back out if the rules
ever require it.

**probe_pin** (qty 1, `loose_piece`, 16 x 16 x 46mm) — the shared
verification tool, unmistakable by being the only long slender part with a
flared head. 6mm-diameter, 40mm-long shaft under a 16mm-diameter, 6mm-thick
flared head. The 40mm shaft length is not a free choice — it is exactly the
distance from tier_disc_c's top face down to a plinth socket floor (3 x 10mm
disc thickness + 10mm socket depth), so a fully open shaft seats the head's
underside flush against tier_disc_c's top face, and any tier that blocks it
leaves the head sitting visibly proud instead. Get this length wrong by even
a millimetre and the game's core tactile verdict (flush = claim, proud =
blocked) stops working — this is the one dimension in the whole brief that
must not be nudged in the build without redoing the arithmetic above.

## Print plan

- Min wall: 1.6mm.
- `plinth_axle` prints drum-face down, axle post rising straight up, sockets
  open upward — no supports.
- Each tier disc prints flat, thickest face down; windows are plain
  through-cuts — no supports.
- All four peg families print base down, domed top up — no supports.
- `probe_pin` prints head down (the 16mm flared disc flat on the bed), shaft
  rising straight up — no supports.
- Nothing is tiled; the largest single part is 206 x 190 x 62mm.

## Interfaces

- **seats** — each of the four marker peg families into `plinth_axle`'s
  sockets: 14mm opening around an 11mm peg base, 1.5mm clearance per side.
  Any empty socket accepts any peg family; a game only ever fills at most 8
  of the 16 pegs manufactured (4 families x 4 pegs) into the 8 sockets.
- **joins** — `plinth_axle`'s 12.2mm axle post through each tier disc's
  13mm center bore, engaged over the disc's full 10mm bore height, 0.4mm
  clearance per side (a free/loose fit, since discs must free-spin under
  hand rotation every turn, not just seat once).
- **stacks** — `tier_disc_a`, `tier_disc_b`, `tier_disc_c` stack on
  `plinth_axle`'s axle post in that fixed order; all three stand without
  toppling because the axle post runs through all three bores at once, not
  because any one disc is wide relative to its height.
- **spans** — `probe_pin` bridges the 40mm gap from `tier_disc_c`'s top face
  to a `plinth_axle` socket floor. This is the load-bearing interface in the
  whole design: get the 40mm span wrong and the flush/proud read that the
  entire win condition depends on breaks silently.

## Unstated in spec

See `brief.json`'s `unstated_in_spec` array for the full text of each; in
short: the axle post's "40mm" figure had to be read as a height, not a
diameter (a 40mm-diameter post cannot fit through a 13mm bore); the axle
post's actual diameter (12.2mm) was derived from the bore, not stated;
`probe_pin`'s stated "62mm" total length contradicts the depth the idea's own
other numbers demand (40mm) — the 40mm calibration was honored because the
win condition depends on it; the probe pin's head thickness (6mm), the two
un-stated tier-disc tab widths (set to match tier_disc_a's 18mm), the
plinth's exact diameter (pinned to 190mm to match the discs), the exact
angular layout of the shared 8-position ring, and the four peg families'
shared 11mm footprint were all filled in as the minimum needed to make the
idea buildable. The art direction's "sunburst finial cap" was left out
entirely — it appears nowhere in idea.json's component list, and inventing a
part for it would be design, not translation.
