# Masked hero: proposed original design (needs your approval)

**Why.** CHARACTERS.md describes a red-and-blue textured suit with black web-pattern
detailing, expressive white mechanical eye lenses, and white lines fired from the wrists.
Together those features identify a specific protected franchise character, and changing the
name doesn't change that (CLAUDE.md says the same). Video services may refuse to generate
it, and the film couldn't be released publicly with it. CLAUDE.md asks for "an original,
distinct masked hero design", so here is one.

## Proposal (used in every prompt in `prompts/`)

| | Original brief | Proposed design |
|---|---|---|
| Suit | red-and-blue, black web pattern | storm-grey and signal-orange weatherproof bodysuit with reflective silver safety-tape chevrons |
| Mask / eyes | white mechanical eye lenses | smooth brass-rimmed diving-style mask-helmet with two round **amber lantern-glass** lenses that narrow and widen expressively |
| Gadget | white synthetic lines from the wrists | brass winch gauntlets that fire **braided orange grapple cables** with small folding hooks |
| "Web" beats | webs a door (024), white rescue line (068), web shield (076) | cable net across the door, orange rescue cable, cable-net canopy |
| Personality / role | athletic acrobat, quippy, mask on in combat, briefly lifted at breakfast | unchanged |

The theme is a storm-rescue rigger: lighthouse brass, signal orange and lantern eyes. It fits
the film's maritime world, it's easy to read in silhouette, and it doesn't share the colour
scheme, pattern, eye shape or gadget look of the franchise character. Every story beat in
`shots.json` still works.

**Name:** none has been given; the prompts say "the masked hero". If you want one for public
release, suggestions are *Rigger*, *Gale* or *Lampwick*.

**What's untouched:** `shots.json` and `CHARACTERS.md` still contain the original wording. The
redesign lives only in `production/continuity.yaml` and the prompts generated from it. If you
approve it, update CHARACTERS.md to match. If you want a different design, edit `hero.look` in
`production/continuity.yaml` and run `python scripts/build_prompts.py`.
