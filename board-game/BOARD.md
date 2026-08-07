# BOARD — Lessons Learned

This file is the persistent memory of the `/goal` self-improvement loop for
`board-game-ideator`. `board-game-evaluator` appends to it every turn;
`board-game-ideator` reads it every turn and, in revise mode, folds it into
its own standing "Learned Heuristics" section
(`.claude/agents/board-game-ideator.md`).

## Pivot (before Turn 5)

The product category changed: this pipeline used to ideate **3D-printed
accessories for existing games** (organizers, dials, trays), scored on a
Demand/55 + Differentiation/15 + Margin/15 + Producibility/15 rubric.

As of Turn 5 it ideates **complete, original, manufacturable board games**
— each idea must be a whole playable game (concept, full rules, full
component/manufacturing bill), not a part or add-on. Anything that isn't a
complete playable game now scores a flat zero. The rubric is now
**Differentiation/40 + Demand/20 + Fun factor/20 + Producibility/20**
(margin was dropped; producibility no longer scores rulebook production,
only physical CAD-printable components), with a hard rule capping
style-only reskins at 2 per batch of 10 (any beyond that score 0/40 on
differentiation).

Turns 1-4 below are retained for provenance but scored a different product
category under a different rubric — **their numbers are not comparable to
Turn 5 onward**, and `board-game-ideator`'s Learned Heuristics section was
reset accordingly (see the "Pivot note" at the top of its Learned
Heuristics). The Score History table below starts a fresh block for the
new rubric.

## Score History

### Archived — old accessory rubric (Demand/55, Differentiation/15, Margin/15, Producibility/15)

| Turn | Avg Total /100 | Avg Demand /55 | Avg Differentiation /15 | Avg Margin /15 | Avg Producibility /15 |
|------|-----------------|-----------------|---------------------------|------------------|--------------------------|
| 1 | 67.2 | 36.7 | 7.6 | 11.8 | 11.1 |
| 2 | 64.8 | 35.4 | 5.6 | 11.5 | 12.3 |
| 3 | 61.4 | 30.0 | 8.7 | 10.5 | 12.2 |
| 4 | 71.3 | 36.4 | 11.5 | 11.1 | 12.3 |

### Current — complete board game rubric (Differentiation/40, Demand/20, Fun/20, Producibility/20)

| Turn | Avg Total /100 | Avg Differentiation /40 | Avg Demand /20 | Avg Fun /20 | Avg Producibility /20 |
|------|-----------------|----------------------------|------------------|---------------|--------------------------|

## Lessons Learned

_Turns 1-4 below were written for the retired accessory-product pipeline
and are kept for provenance only — `board-game-ideator`'s Learned
Heuristics no longer draw on them (see the Pivot note above). Turn 5
onward reflects the current complete-board-game rubric._

### Turn 1

**Differentiation is the systemic weak point, not demand.** Average differentiation
landed at 7.6/15 — the lowest-scoring category by a wide margin, and 6 of the 10
ideas scored 6/15 or lower there. In almost every one of those cases, a direct
targeted search (not just a category search) turned up an existing product doing
essentially the same thing: a "Pro" no-cube player board for Terraforming Mars, a
BGHQ token upgrade set for Root, magnetic modular MTG deck boxes already sold on
Etsy, magnet-ready miniature bases as a saturated Etsy category, lazy-Susan poker
chip caddies as an established (if usually non-printed) product, and multiple
existing "catapult" dice towers. Pattern: verifying *demand* for a named game/trend
is not the same as verifying that *this specific mechanism* is unclaimed — before
finalizing an idea, search for the mechanism/feature itself (e.g. "magnetic
modular deck box," "catapult dice tower," "Root token upgrade"), not just the
game name plus "accessory" or "organizer." A demand search proves people buy in
this category; a differentiation search has to independently prove nobody's
already selling this exact angle.

**Rationale claims need to survive a direct search, not just sound plausible.**
Idea 4's core demand claim (a TikTok/Instagram-driven cribbage resurgence) and
idea 6's core demand claim (Root's cardboard tokens are a "frequently cited
complaint") both failed verification — in idea 6's case, the search evidence
actively contradicted the claim (reviews described Root's components as good
quality). Per the rubric, unverifiable trend claims cap demand at 25/55, and both
ideas landed in the bottom three as a result. Going forward: if a rationale cites
a "trend" or "frequently cited complaint" as its main demand evidence, that's
the single highest-value thing to pre-verify before finalizing the idea, because
it's an all-or-nothing gate on the biggest scoring category.

**What the top scorers did right, worth repeating:** Ideas 1 (Catan dial tray, 80)
and 2 (Wingspan birdhouse sorter, 75) both anchored demand in a specific,
independently-verifiable fact (an active, named Etsy search category / a
documented aftermarket-upgrade fanbase for that exact title) rather than a general
"this genre is popular" claim, and both proposed a genuinely narrow, checkable
feature gap (rotating bonus-card dials; a closable birdhouse roof) rather than
reinventing an entire product category. Idea 5 (accessibility card holder, 74)
had the cleanest producibility profile in the set — one part, no assembly, exactly
one dimension flagged as critical — which is the template for producibility
scoring: fewer parts and an explicit, narrow tolerance call-out beats an elaborate
multi-part mechanism every time on this axis.

**Producibility risk to watch: printed-only mechanisms replacing hardware.** Idea
3's printed-flexure "torsion spring" catapult (no metal spring) and idea 9's
220mm rotating disc on a printed friction pivot (no bearing) both took on real
reliability risk to avoid a hardware part. When a mechanism's function depends on
a single thin, fatigue-prone printed feature or a bare plastic-on-plastic bearing
surface at a large diameter, either spec a hardware insert (spring, bearing,
elastic band) or size the risky feature with a wide safety margin and say why —
don't just declare a critical dimension and move on.

### Turn 2

**Differentiation got worse, not better (7.6 → 5.6/15), despite Turn 1's explicit
warning to search the mechanism, not just the game/category.** This is the most
important regression to fix. Six of ten ideas this turn made a confident,
specific differentiation claim ("Search confirms every existing X requires Y" /
"no existing design combines A and B") that a direct search *directly
contradicted* — not just found adjacent competitors, but found the near-exact
product already shipping free:
- Idea 1 claimed existing Everdell prints are storage-only; MakerWorld's free
  "Everdell - resource holders" set already includes a literal tree-trunk resource
  holder, and Printables' card holders are already in-play browsing aids.
- Idea 3 claimed all folding dice towers require glued-in magnets; multiple
  existing print-in-place towers ship with zero magnets and zero hardware already
  ("Collapsible Dice Tower" literally advertises "no magnets, no clips").
- Idea 6 claimed no card holder combines two racks with a privacy divider;
  MakerWorld's "Playing card holder (divideable)" is already described as exactly
  that ("curved... so other players cannot see your cards").
- Idea 7 claimed every dungeon-tile system needs user-installed magnets/pins;
  OpenLOCK's clip system is an established, actively-used magnet-free connector
  standard in that exact hobby.
- Idea 10 claimed existing deck-box systems are fixed-capacity, not expandable;
  MakerWorld's "Stack Box Infinite" uses nearly identical marketing language
  ("combine with any number of others — as tall, as wide, and as colorful as you
  want") to what the idea itself proposes as its innovation.
Pattern: these searches were confidently *asserted* in the rationale text but
evidently either not run against the specific mechanism/wording, or run and their
top hits not read closely enough to notice the near-exact match. Going forward:
before writing "search confirms no existing design does X," the search actually
has to be for that specific claim in a form that would surface the counterexample
(e.g. "dice tower no magnets", "modular deck box expandable", "dungeon tile clip
no magnet") — and if a close match turns up, either drop the idea or reframe the
differentiation around the narrower thing that's genuinely still missing (see
idea 2 below for how to do this correctly).

**Unverifiable trend claims are still slipping through as the primary demand
hook.** Idea 8's rationale leaned on "2026 cozy/filler-game coverage repeatedly
highlighting" a growth segment for small-box filler games — a search for that
specific claim turned up nothing supporting it, and it became the lowest score
of the turn (55) as a direct result. This is the same failure mode flagged in
Turn 1 (idea 4's cribbage TikTok claim, idea 6's Root complaint claim): a
plausible-sounding trend citation is not evidence. If a genre-wide "coverage
highlights this" claim can't be traced to an actual named article/list, cut it
and lean on a narrower, independently-checkable fact instead (an active Etsy
search category, a documented fanbase, confirmed publisher revenue) the way
idea 2 did with the cozy-game trend.

**What the top scorer (idea 2, Cozy Games Nesting Hex Canister Set, 72) did
right: it scoped differentiation narrowly enough to survive contact with
search.** Its claim wasn't "no hex token storage exists" (false — HexNest and
hex stacking bowls already exist) but implicitly the more specific "closed-lid,
graduated-size, nest-to-one-volume travel format" — a real, narrower gap that
search did not contradict. The lesson from Turn 1 ("verify the mechanism, not
just the category") needs a companion rule: **the narrower and more specific
the differentiation claim, the more likely it survives a search** — broad
absolute claims ("every existing design requires...", "no existing product
combines...") are the ones getting falsified. Idea 9 (turn-order carousel, 67)
also avoided contradiction by claiming differentiation on a specific *combination*
of features (fold-away arm count + dual current/next indicator) rather than
the whole product category, and its claim held up under search.

**Producibility watch-item this turn: idea count of independent risky joints,
not just presence of one.** Idea 9's 6 separate print-in-place hinge-and-detent
joints on a single build (vs. idea 3's 4 hinges or idea 1's single friction-fit)
is a materially higher-risk mechanism than anything flagged in Turn 1, and the
producibility_notes didn't call out the compounding risk of needing all 6 to
print cleanly. When a design has N repeated risky joints, the failure
probability compounds — call out N explicitly and consider whether a
lower-joint-count alternative gets 90% of the value.

### Turn 3

**Differentiation improved on average (5.6 → 8.7/15) but two ideas still made
absolute "nobody does this" claims that a single direct search falsified —
both landed in the bottom three as a result.** Idea 4 claimed no turn-order
tracker lets a buyer add/remove player-count segments on a shared hub; Etsy's
"Modular D&D Initiative Tracker" already does exactly that (snap-together
segments, described by the seller as scaling from solo to 8-player). Idea 10
claimed existing con-badge attachments are fabric/paper ribbons only, not rigid
3D printed charms; Etsy already sells a "3D Printed Meeple Lanyard Name Badge
... Personalised" explicitly marketed for "gaming shows and conventions," plus
D20 dice charms and meeple lanyard charms in the same space. Both failures
follow the exact Turn 2 pattern: a confident absolute claim ("no result
offered...", "existing badge ribbons are... not rigid 3D printed charms")
that a search *for that specific product type* (not the game/genre name)
immediately contradicts. The fix from Turn 2 — narrow the claim to a specific
sub-feature, and if a close match turns up, either drop the idea or reframe
around the genuinely-missing sliver — is being applied inconsistently: 8 of
10 ideas this turn did scope narrowly and survived search (see idea 1's
clip-retrofit vs. full-deck-replacement framing, or idea 9's institutional-
audit framing vs. hobbyist organizers), but the 2 that didn't scope narrowly
still slipped through to the prompt-writing stage instead of being caught
before finalizing.

**A verified true fact is not the same as a verified demand link — check the
argument, not just the citation.** Idea 4's rationale cited a real, checkable
fact (Rebirth won Kennerspiel des Jahres 2026, confirmed via ICv2/BGG/
wericmartin.com) but used it to support an unrelated claim (that a cyclical-
theme award winner creates demand for a generic turn-order-wheel accessory).
The fact-check passed; the argument it was supposed to support didn't follow
from it. Going forward, when citing a trend/award/fact as demand evidence,
the question to ask isn't just "is this fact true" but "does a person who
knows this fact actually become more likely to buy this specific product" —
if the link is inferential rather than direct (award-winner's mechanic vs.
a generic accessory, rather than e.g. a documented fanbase for that
accessory type), treat it as weak evidence even though it's a true citation.

**Margin declined this turn (11.5 → 10.5/15), concentrated in three
institutional/epic ideas with long print times relative to price: idea 7
(140g/5hr for $27), idea 9 (180g/6hr for $32), and idea 5 (90g+hardware/4hr
for $24).** None of these ideas' margin_case sections did the arithmetic of
print-hours-to-price the rubric asks for explicitly — idea 7 justified its
price against the *base game's* $80-100 price point rather than against its
own 5-hour print cost, and idea 9 assumed a $32/unit institutional price
without accounting for the bulk-discount expectations of institutional
buyers. Pattern: when a margin_case cites the buyer's general willingness to
pay (for the base game, for the category) instead of a print-time-vs-price
ratio for *this specific object*, that's a sign the price hasn't actually
been stress-tested against the object's own cost — flag it explicitly when
print time exceeds ~3 hours.

**What the top scorers did right, worth repeating:** Idea 1 (Tactile Suit-
Rank Corner Clips, 66) scoped its differentiation claim to one narrow
mechanism (a detachable per-corner retrofit clip, not accessible card
products broadly) and it survived multiple direct searches intact — the
model for how to phrase a differentiation claim so it's falsifiable and
still true. Idea 9's institutional-audit framing (library/game-cafe piece-
count verification, not permanent home-storage optimization) similarly
carved out real unclaimed territory in an otherwise saturated organizer-
insert space by picking a different buyer and use case, not just a different
shape. On producibility, ideas 1, 6, and 8 continue the pattern from Turns
1-2: many small identical parts or a single flex joint, with one explicit
critical tolerance called out per part type, consistently scores 12-13/15 —
this is now a proven, repeatable template and should stay the default shape
for new ideas rather than an occasional choice.

### Turn 4

**Demand jumped sharply (30.0 → 36.4/55) because this batch mostly cited
independently-checkable, hard numbers instead of trend language — but two
ideas still slipped back into the exact failure modes Turns 1-3 warned
about.** Eight of ten ideas grounded demand in a verifiable fact that
search actually confirmed: Catan's 32-45M copies sold (NPR/publisher),
Monopoly's 275M-copy Guinness record, Terraforming Mars's BGG top-10 rank,
Splendor's 2014 SdJ nomination, Ticket to Ride's 2004 SdJ win, Root's
active expansion line, and Dominion's real 2023-24 Rising Sun expansion
all checked out exactly as claimed. This is a real, measurable improvement
in citation discipline and should be reinforced as the default. But idea 6
(Pandemic) cited "well over 8 million units sold" when the only verifiable
figure (Z-Man's own 2021 release) is 5 million — a specific, checkable
number that was simply inflated, the same failure class as Turn 1-3's
trend claims, just with a fabricated statistic instead of a fabricated
trend. And idea 10 (playmat wind clips) built its demand case on a search
engine's own hedge ("may still be a niche product opportunity") — treating
an admission of inconclusive evidence as if it were supporting evidence,
rather than applying the cap the rubric calls for when a search is
inconclusive. Rule to add: before citing a specific number (sales figures,
unit counts, membership counts) as demand evidence, that number itself
needs a direct search hit, not just the game/publisher name — a real
publisher and a real game don't guarantee the specific figure attached to
them is real.

**A verified fact can still support the wrong kind of demand link — watch
for indirect-audience mismatches, not just false facts.** Idea 4 (chess
capture tray) cited real, current, well-sourced numbers (Chess.com's 200M+
registered users, the confirmed Queen's Gambit signup spike), but those
numbers describe *online* chess growth being used to justify demand for a
*physical, over-the-board* accessory — the same "true fact, weak argument"
gap flagged in Turn 3 with the Rebirth/turn-order-wheel case. Going
forward, when a demand citation is about digital/online engagement, treat
it as only partial evidence for a physical-accessory product unless the
rationale also cites physical-accessory buying behavior specifically (as
idea 4 separately did with the $15-200 chess-set market, which is why it
wasn't scored down further).

**Margin regressed to its lowest point yet (11.5 → 11.1/15), and the cause
is now a clearly repeating pattern across three separate ideas rather than
an isolated case.** Ideas 7 (Root, 5hr/$28 four-pack), 8 (Monopoly, 5hr/
$26), and 9 (Dominion randomizer, 5hr/$27) all have print times over 3
hours and all justify their price exclusively by citing the buyer
segment's general willingness to pay for the *category* (Etsy upgrade
accessories, banker-tray accessories, organizer boxes) rather than doing
the print-time-to-price arithmetic for *this specific object* that Turn 3
explicitly asked for. This is the single most important miss this turn:
Turn 3's lesson named this exact pattern and it was not applied in the
following turn's revise pass. Standing heuristic to make non-optional
going forward: any idea with a print time over 3 hours must state its
per-hour revenue (price ÷ print hours) explicitly in the margin_case and
argue why that rate is acceptable, not just cite what similar accessories
sell for.

**Producibility's one low score (idea 9, Dominion randomizer, 9/15) is the
same unmitigated printed-mechanism risk flagged in Turn 1 and still
unresolved three turns later.** A 150mm drum rotating on a bare printed
axle-in-housing bearing (no hardware insert) plus a 1mm spring pawl
expected to survive repeated engagement against 40 notches is exactly the
"printed-only mechanism replacing hardware" pattern Turn 1 said needs
either a hardware insert or an explicit wide-safety-margin justification —
neither was provided here. This should be treated as a hard rule now, not
a repeated observation: any drum/wheel over ~100mm diameter on a printed
bearing surface either specs a hardware insert or is downgraded.

**What the top scorers did right, worth repeating:** Idea 8 (Monopoly
carousel, 82) and idea 2 (Catan tray, 82) both paired a top-tier,
independently-confirmed mass-market demand fact with a differentiation
claim narrow enough to survive search intact (search explicitly reported
"no rotating carousel found" for idea 8), continuing the Turn 3 lesson
that specificity is what makes a claim falsifiable-and-true rather than
falsifiable-and-false. Idea 3 (Splendor privacy shield, 75) and idea 4
(chess tray, 70) both kept producibility near-ideal with 1-2 jointless or
single-hinge parts and one explicit critical tolerance — this remains the
most reliable path to a high producibility score and should stay the
default shape rather than something only some ideas reach for.
