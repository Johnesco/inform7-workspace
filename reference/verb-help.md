# Verb Help System — Authoring Guide

A reusable Inform 7 source template that reduces guess-the-verb frustration. Pure in-game solution — works in every interpreter (web, native, testing).

## Quick Start

1. Open `tools/verb-help-template.ni`
2. Copy the entire `Chapter - Verb Help System` into your `story.ni`
3. Compile and test

The template is a single self-contained Chapter with four independent sections. Include all of them or cherry-pick individual sections.

## What It Provides

### Section 1: Enhanced Parser Errors

Replaces Inform 7's cryptic default parser errors with actionable messages that guide the player:

| Parser Error | Default | Replacement |
|---|---|---|
| Not a verb I recognise | "That's not a verb I recognise." | Points to VERBS command and suggests simpler phrasing |
| Didn't understand | "I didn't understand that sentence." | Suggests VERB NOUN pattern with examples |
| Can't see any such thing | "You can't see any such thing." | Suggests LOOK and INVENTORY |
| Said too little | "You seem to have said too little." | Asks for more detail with examples |
| Only understood as far as | "I only understood you as far as..." | Suggests rephrasing |

### Section 2: HELP and VERBS Commands

Two out-of-world actions:
- **VERBS** (also: COMMANDS) — categorized list of available verbs
- **HELP** (also: HINT, HINTS) — brief orientation for parser IF newcomers

### Section 3: Common Synonyms

~40 verb synonym mappings covering the most frequent guess-the-verb failures. Only adds genuinely missing synonyms — does not duplicate what Inform 7 already handles.

| Category | Standard (already works) | Added by template |
|---|---|---|
| Examination | examine, x, look at, read, watch, check | inspect, study, view, peruse |
| Taking | take, get, pick up, carry | grab, collect, acquire, snag, fetch, obtain, steal, nab, lift |
| Combat | attack, hit, fight, punch, kill, smash | strike, stab, slash, kick |
| Looking | look, l | peek, peer, gaze |
| Going | go + directions, walk, run | proceed, head |
| Opening | open, uncover, unwrap | pry, force |
| Dropping | drop, throw, discard | toss |
| Putting | put, insert | place |
| Pushing | push, move, shift, press | shove, prod |
| Pulling | pull, drag | yank |
| Eating | eat | consume, devour |
| Communication | ask, tell, say | talk to, speak to, chat with (with topic patterns) |

### Section 4: USE Verb Handler

Dedicated handler for the most common unrecognized verb in parser IF:
- **USE thing** — redirects with specific verb suggestions
- **USE thing ON/WITH thing** — attempts unlock if target is lockable, otherwise suggests specific commands

## Customization

### Adding Game-Specific Synonyms

Add a new section after the template's Section 4:

```inform7
Section 5 - Game-Specific Synonyms

[Zork I examples:]
Understand "dig [something] with [something]" as digging it with.
Understand "inflate [something] with [something]" as inflating it with.
Understand the command "tie" as "attach".
```

### Customizing the VERBS Output

To add game-specific verb categories, replace the `Carry out requesting the verb list` rule:

```inform7
Carry out requesting the verb list:
	say "Movement:  NORTH (N), SOUTH (S), EAST (E), WEST (W), UP (U), DOWN (D)[line break]";
	say "Looking:   LOOK (L), EXAMINE (X) thing, SEARCH thing[line break]";
	say "Taking:    TAKE thing, DROP thing, PUT thing IN/ON thing[line break]";
	say "Using:     OPEN, CLOSE, LOCK/UNLOCK, PUSH, PULL, TURN ON/OFF[line break]";
	say "Combat:    ATTACK thing, DIG thing WITH thing[line break]";
	say "Meta:      SAVE, RESTORE, UNDO, SCORE, HELP, VERBS, QUIT".
```

### Customizing HELP Per Game

Replace the `Carry out requesting help` rule to add game-specific guidance:

```inform7
Carry out requesting help:
	say "Welcome to Zork I. Type commands in plain English.[line break]";
	say "Most puzzles need two-word commands: VERB NOUN.[line break]";
	say "The thief is dangerous — save often! Type VERBS for commands."
```

### Overriding Parser Errors Per Game

Add more specific rules that fire before the template's generic ones:

```inform7
Rule for printing a parser error when the latest parser error is the can't see any such thing error and the player is in a dark room:
	say "It[apostrophe]s too dark to see anything. Try finding a light source."
```

Inform 7's rule specificity system ensures more specific rules fire first.

## Testing

### RegTest Patterns

Test verb help features with these patterns in your `.regtest` file:

```regtest
* verb-help-verbs
> verbs
/Movement/
/Looking/
/Taking/
/Meta/

* verb-help-help
> help
/text adventure/
/VERB NOUN/

* verb-help-parser-error
> flurble
/don't know that command/
/VERBS/

* verb-help-synonym
> inspect [any visible object in your game]
/[expected description text]/

* verb-help-use
> use [any takeable object]
/How do you want to use/
```

### Walkthrough Compatibility

The template adds no new rooms, objects, or scoring. Existing walkthroughs continue to pass without modification.

### Template Isolation Test

Remove the Chapter from `story.ni` and verify the game still compiles. The template introduces no dependencies that leak into other code.

## Clarification Messages

When a custom action redirects to a conceptually different standard action (ring→push, climb stairs→go up), add a parenthesized clarification message so the player learns what the parser actually did. This matches I7's built-in "(first taking X)" convention.

### Pattern

```inform7
Instead of climbing the narrow staircase:
	say "(going up)[command clarification break]";
	try going up.
```

Output:
```
>climb stairs
(going up)
Attic
A cramped attic under sloping eaves...
```

### When to Use

| Redirect type | Example | Add message? |
|---|---|---|
| Custom action → different standard action | ring→push, climb→go up, look behind→push | **Yes** |
| Implicit noun resolution | bare `dig` → `dig flower bed` | **Yes** |
| Target redirection | `burn matchbook` → `burn fireplace` | **Yes** |
| Template synonyms | grab→take, inspect→examine | **No** |
| Near-synonyms | kindle→burn, rummage→search | **No** |
| Internal simplification | wind X with Y → wind X | **No** |

### Formatting Rules

- Use lowercase, parenthesized, action-oriented phrasing: `(pressing the doorbell)`
- Do NOT expose parser internals: ~~(understood as: pushing the brass doorbell)~~
- Always use `[command clarification break]` — it produces the standard line break that I7 uses for "(first taking X)"
- For noun references, use `[the noun]` to get the article: `(pressing [the noun])`

### Tested In

Piloted on `projects/guess_the_verb/` with 7 redirect points. See `FINDINGS.md` for the full analysis.

## Design Decisions

**Why a source template, not an Extension?** Extensions require installation into the Extensions directory and have specific formatting requirements. A source template pasted into `story.ni` is simpler, visible in the source browser, and avoids Windows extension-path issues.

**Why no fuzzy/Levenshtein matching?** Inform 7's parser uses fixed grammar tables at the I6 level. Explicit synonym mappings achieve most of the benefit with zero engine hacking.

**Why handle USE specifically?** Players from point-and-click adventure games instinctively type USE. A dedicated handler that redirects to specific verbs teaches parser literacy.

**Why not override "move" → "go"?** The standard library maps "move" to pushing (PUSH). Redirecting it to "go" would break `MOVE TABLE`.
