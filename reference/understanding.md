# Inform 7 Understanding (Parser) Reference

The `Understand` command maps player-typed text to game actions and objects. It controls everything the parser recognizes.

## Basic Syntax

```inform7
Understand "photograph [someone]" as photographing.
Understand "xyzzy" or "say xyzzy" or "cast xyzzy" as casting xyzzy.
```

The first word must always be literal text, not a token.

## Understanding Things (Naming Objects)

### Adding names to objects
```inform7
Understand "dog" as the St Bernard.
Understand "lamp" and "old lamp" as the lantern.
```

Inform auto-generates names from object declarations (e.g., "The St Bernard is an animal" makes both ST BERNARD and SAINT BERNARD parseable). `Understand` adds additional synonyms.

### Plural names for kinds
```inform7
Understand "birds" and "ruddy ducks" as the plural of duck.
Understand "birds" as the plural of the magpie.
```

### Understanding values (non-object data)
```inform7
Understand "eleventy-one" as 111.
Understand "cerulean" or "cerulean blue" as blue.
```

**Pitfall:** Avoid circular definitions like `Understand "[thing] substitute" as the placebo` -- this causes infinite parser recursion.

## Understanding Things by Their Properties

Objects can be understood by dynamic properties, so parser vocabulary updates as game state changes:

```inform7
A flowerpot can be unbroken or broken.
Understand the broken property as describing a flowerpot.
Understand "pristine" as unbroken.
Understand "shattered" or "cracked" as broken.
```

**Key distinction:**
- `describing` -- property name alone can identify the object ("take broken")
- `referring to` -- property works only as adjective before object name ("take broken flowerpot")

Supported property types: boolean, number, text, enumerated values.

## New Commands for Existing Actions

### Adding grammar to existing actions
```inform7
Understand "deposit [something] in [an open container]" as inserting it into.
```

### Reversing noun order
```inform7
Understand "fill [an open container] with [something]" as inserting it into (with nouns reversed).
```

### Command synonyms
```inform7
Understand the command "access" as "open".
Understand the commands "snap" and "picture" as "photograph".
```

This maps all grammar lines of the target command. Check the Actions index first to avoid conflicts.

## Overriding Existing Commands

### Unbinding a command
```inform7
Understand the command "discard" as something new.
Understand "discard [something]" as discarding.
```

**Order matters:** Remove old vocabulary first, define the new action, then assign new grammar.

### Clearing all commands for an action
```inform7
Understand nothing as attacking.
```

## Standard Tokens

| Token | Matches | Notes |
|---|---|---|
| `[something]` | Any single thing in scope | Most common |
| `[someone]` | Any person in scope | Like `[a person]` with better error messages |
| `[something preferably held]` | Thing, preferring carried items | Auto-attempts "take" if needed |
| `[things]` | Multiple things or "all" | Generates one action per matched item |
| `[things preferably held]` | Multiple carried things | Plural version of preferably held |
| `[things inside]` | Things inside a container only | Prevents matching the container itself |
| `[other things]` | Things excluding the second noun | For container interactions |
| `[any things]` | Things anywhere (even out of play) | Use with caution -- "all" matches broadly |
| `[text]` | Arbitrary player text | Stored in `the topic understood` |
| `[a number]` | A whole number | Stored in `the number understood` |
| `[a time]` | A specific time (10:15 AM) | Stored in `the time understood` |
| `[a time period]` | A duration (TWO HOURS) | Stored in `the time understood` |

### The "any" keyword (expanding scope)

Normally the parser only matches things in reach or sight. Prefix descriptions with `any` to match things anywhere:

```inform7
Understand "find [any thing]" as finding.
Understand "go to [any adjacent visited room]" as going by name.
Understand "follow [any person]" as following.
```

**Shortcuts:**
- `[anything]` = `[any thing]`
- `[anybody]` / `[anyone]` = `[any person]`
- `[anywhere]` = `[any room]`

### Topic token and "the topic understood"

```inform7
Understand "help [text]" as getting help about.
Getting help about is an action applying to one topic.

Carry out getting help about:
    if the topic understood matches "combat":
        say "Type ATTACK [something] to fight.";
    otherwise:
        say "No help available on that topic."
```

**Pitfall:** `[text]` matches almost anything, which can prevent other grammar lines from being recognized. Place more specific rules first.

## Number and Time Tokens

```inform7
Understand "adjust [something] to [a number]" as adjusting it to.
Adjusting it to is an action applying to one thing and one number.

Check adjusting it to:
    if the number understood is less than 1, say "Too low." instead.

Carry out adjusting it to:
    say "You set [the noun] to [the number understood].";
```

**Constraint:** The token kind must match the action's declared kind. `Understand "adjust [something] to [something]"` fails when the action expects a number.

## Custom Kinds as Tokens

When you define a kind of value, Inform automatically creates a matching token:

```inform7
Limb is a kind of value. The limbs are left leg, left arm, right leg, right arm.
Understand "photograph [limb] of [a person]" as detailing.
Detailing is an action applying to one limb and one visible thing.

Carry out detailing:
    say "You photograph the [limb understood] of [the noun].";
```

The parsed value is available as `[kind-name] understood` (e.g., `limb understood`, `number understood`, `time understood`).

## Understand as a Mistake

Intercept specific commands and print a custom error instead of executing any action:

```inform7
Understand "take [text]" or "get [text]" or "drop [text]" as a mistake
    ("Here, you only draw and discard. Nothing else matters at the moment.").
```

Use cases:
- Contextual restrictions (disabling actions in specific scenes)
- Player guidance for unsupported commands
- Genre-specific mechanics (card games, puzzles, etc.)

## Context-Dependent Understanding

Add conditions to Understand lines:

```inform7
Understand "enter" as going inside when the location is the Garden.
Understand "push [something]" as pushing when the player carries nothing.
```

## Verbless Commands (Noun-Only Input)

Allow players to type bare nouns to trigger actions:

```inform7
Understand "[something]" as examining.
Understand "[any room]" as going by name.
Understand "[door]" as entering.
```

**Limitations:**
- Only works for direct player input, not orders to NPCs ("SVEN, BALL" becomes conversation)
- Use sparingly -- can confuse players if not carefully explained

## Slash Shorthand and Alternatives

### Slash for single-word alternatives
```inform7
Understand "reach underneath/under/beneath [something]" as looking under.
```
Expands to three separate grammar rules, one per preposition.

### Optional words with double-dash
```inform7
Understand "reach underneath/under/beneath/-- [something]" as looking under.
```
`--` means "no word at all," making that position optional. Can only appear once, at the end of alternatives.

### "Or" for complex alternatives
```inform7
Understand "scarlet" or "crimson" as red.
```

Rule of thumb: use slashes for single-word preposition variants; use `or` for anything more complex.

## New Tokens (Reusable Grammar Patterns)

Define named tokens to avoid repeating complex grammar:

```inform7
Understand "beneath/under/by/near/beside/alongside/against" or "next to" as "[beside]".
Understand "on/in/inside" or "on top of" as "[within]".

Understand "lie down [within] [something]" as entering.
Understand "lie [beside] [something]" as lying near.
```

### Tokens that produce values
```inform7
Colour is a kind of value. The colours are red, green and blue.
Understand "colour [a colour]" or "[a colour] shade" as "[tint]".
```

**Constraint:** Tokens cannot produce more than one value, and all patterns for the same token must produce compatible types.

## Understanding Through Relations

Reference objects via their current relations:

```inform7
Understand "box of [something related by containment]" as a box.
Understand "box in [something related by reversed containment]" as a box.
Understand "[something related by direction-relevance] door" as a door.
Understand "of [something related by reversed appearance]" as a photograph.
```

This enables dynamic naming: a "box of crayons" only parses when crayons are actually inside the box.

## Common Pitfalls

1. **First word must be literal** -- `Understand "[something]" as examining` works only for verbless commands; normal commands need a verb word first
2. **Token/action kind mismatch** -- the token type must match what the action declares it applies to
3. **`[text]` is greedy** -- it matches almost anything and can shadow other grammar lines
4. **Circular understand definitions** -- `Understand "[thing] substitute" as X` causes infinite recursion
5. **Forgetting "something new"** -- when repurposing an existing command word, unbind it first with `Understand the command "word" as something new`
6. **Noun count mismatch** -- supplying zero or two objects when the action expects exactly one causes parser failure
