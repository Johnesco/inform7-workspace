# Inform 7 Activities & Phrases Reference

## Part 1: Activities

### What Are Activities

Activities are *engine-level tasks* — what the Inform program does internally (printing text, describing objects, processing output). Do not confuse them with actions, which are what characters do in the game world.

Every activity has three rulebooks:
1. **Before** rules — run first
2. **For** rules — the most specific applicable rule runs (performs the actual work)
3. **After** rules — run last

### Creating Custom Activities

```inform7
Assaying is an activity.                          [applies to nothing]
Analysing something is an activity.               [applies to objects]
Announcing something is an activity on numbers.   [applies to a specific kind]
```

**Executing activities:**
```inform7
carry out the assaying activity.
carry out the analysing activity with the pitchblende.
```

### Activity Variables

```inform7
Analysing something is an activity.
The analysing activity has a text called the first impression.
```

Typical workflow: set a default in "before", calculate in "for", use the result in "after".

### Activity Nesting

Activities can run inside other activities but must nest strictly — if B starts during A, B must finish during A.

```inform7
if the printing the name activity is going on, ...
```

Conditional rules with provisos:
```inform7
Rule for printing the name of the lemon sherbet while listing contents:
    say "curious sort of lemon sherbet sweet".
```

### Manual Activity Control

```inform7
begin the analysing activity with the pitchblende;
if handling the analysing activity with the pitchblende:
    [... do something ...];
end the analysing activity with the pitchblende;
```

**Abandonment** (forces immediate termination):
```inform7
abandon the analysing activity with the pitchblende;
```

### Key Built-in Activities

#### Printing the Name of Something

Triggered whenever an object's name appears in text:

```inform7
Rule for printing the name of the watch while taking inventory:
    say "watch (currently showing [time of day])".

Before printing the name of a novel:
    say "[italic type]".
After printing the name of a novel:
    say "[roman type]".
```

Suppress container contents in listings:
```inform7
Rule for printing the name of the bottle:
    if the bottle contains sand:
        say "bottle of sand";
        omit contents in listing;
    otherwise:
        say "empty bottle".
```

#### Printing a Number of Something

Governs grouped identical items. `listing group size` contains the count:

```inform7
Rule for printing a number of blocks when the listing group size is 3:
    say "all three blocks".

Rule for printing a number of ants:
    say "altogether [listing group size in words] ants".
```

#### Listing Contents of Something

Three grouping modes:
```inform7
Before listing contents: group utensils together.
Before listing contents: group utensils together giving articles.
Before listing contents: group utensils together as "utensils".
```

#### Grouping Together Something

Fires during content listing for grouped items:

```inform7
Before listing contents: group Scrabble pieces together.

Before grouping together Scrabble pieces:
    say "the tiles ".
After grouping together Scrabble pieces:
    say " from a Scrabble set".
```

Completely custom:
```inform7
Rule for grouping together utensils: say "the usual utensils".
```

#### Printing Room Description Details

Adds bracketed info in room descriptions (e.g., "a cage (empty)"):

```inform7
Rule for printing room description details: stop.    [remove all addenda]

Rule for printing room description details of a person:
    say " (at last, someone to talk to)" instead.
```

#### Printing Inventory Details

```inform7
Rule for printing inventory details: stop.    [remove all addenda]

Rule for printing inventory details of something edible:
    say " (yummy!)[run paragraph on]".
```

#### Deciding the Concealed Possessions

Determines whether items carried/worn by someone are visible:

```inform7
Rule for deciding the concealed possessions of the furtive ghost: yes.

Rule for deciding the concealed possessions of Clark:
    if the particular possession is the thong and Clark is wearing the suit, yes;
    otherwise no.
```

**Pitfall:** Always explicitly decide yes or no — don't rely on fall-through.

#### Darkness and Light

```inform7
Rule for printing a refusal to act in the dark:
    if we are examining something,
        say "It's too dim for close-up examination." instead.

Rule for printing the announcement of darkness:
    say "Ooh-er! It's very nearly pitch dark in here." instead.

Rule for printing the announcement of light in the Dazzling Temple:
    say "You are almost blinded by white light." instead.
```

---

## Part 2: Phrases

### Defining Phrases

```inform7
To spring the trap:
    say "'Sproing!' go the hinges!";
    end the story.

Instead of entering the cage:
    spring the trap.
```

### Pattern Matching (Typed Parameters)

```inform7
To admire (item - an object):
    say "You take a long look at [item]."
```

Format: `(name - kind)`. Type enforcement is strict.

**Specificity priority** — more specific definitions win:
```inform7
To grant (bonus - a number) points:
    increase the score by the bonus.

To grant (bonus - 7) points:
    say "You shiver uncontrollably."
```

**Alternative wordings:**
```inform7
To grant (bonus - a number) point/points: ...
To grant (bonus - a number) point/points/--: ...
```

The `--` makes a word optional.

**Pitfall:** Bracketed parameters must always be separated by text words — two consecutive parameters with nothing between them is an error.

### Phrase Options

Allow a single phrase to be called in several ways:

```inform7
To go hiking, into the woods or up the mountain:
    if up the mountain, say "You head uphill.";
    otherwise say "You set off."

go hiking;
go hiking, into the woods;
go hiking, up the mountain;
```

### Let and Temporary Variables

```inform7
let outer bull be 25;
let the current appearance be "reddish brown";
```

Inform deduces the kind from the assigned value. Once declared, the kind cannot change.

### If, Unless, Otherwise

```inform7
if the red door is open, say "You could try going east?"

if the red door is open:
    say "You could try going east?";
    say "It looks inviting."

unless the red door is closed, say "You could try going east?"
```

**Switch-style syntax:**
```inform7
if the dangerous item is:
    -- the electric hairbrush:
        say "Mind your head.";
    -- the silver spoon:
        say "Steer clear of the cutlery drawer.";
    -- otherwise:
        say "It seems harmless enough."
```

### While and Repeat

```inform7
while someone (called the victim) is in the Crypt:
    say "A bolt of lightning strikes [the victim]!";
    now the victim is in the Afterlife.

repeat with counter running from 1 to 10:
    say "[counter] ".

repeat with item running through open containers:
    say "[The item] is open."
```

**Pitfall:** Never modify qualifying items mid-iteration with `repeat running through`. Use `while` instead:
```inform7
while there is an open container (called the box):
    now the box is closed.
```

### Next and Break

```inform7
repeat with X running from 1 to 10:
    if X is 4, next;       [skip to next iteration — NOT "continue"]
    say "[X] ".

repeat with X running from 1 to 10:
    if X is 7, break;      [exit loop entirely]
    say "[X] ".
```

**Pitfall:** Inform rejects the word `continue` — use `next`.

### Stop

Terminates the current rule or phrase immediately:

```inform7
To judge the score:
    if the score is 0, stop;
    say "The score is [score in words]."
```

In action rules, `stop the action` is preferred for clarity.

### To Decide Whether (Custom Conditions)

```inform7
To decide whether danger lurks:
    if in darkness, decide yes;
    if the Control Room has been visited, decide no;
    decide yes.
```

Usage: `if danger lurks, ...`

- `decide yes` / `yes` — makes the condition true
- `decide no` / `no` — makes the condition false

### To Decide Which (Value-Returning Phrases)

```inform7
To decide which number is the threat level:
    if in darkness, decide on 5;
    if the monster is in the location, decide on 3;
    decide on 1.
```

**Pitfall:** Must have `decide on` on every code path.

### Custom Adjectives

Simple format:
```inform7
Definition: a supporter is occupied if it is described and something is on it.
```

Extended format:
```inform7
Definition: a supporter is occupied:
    if it is undescribed, decide no;
    if something is on it, decide yes;
    decide no.
```

### The Showme Phrase (Debugging)

```inform7
When play begins: showme 11.          [outputs "number: 11"]
Every turn: showme the score.
```

Has no effect in released story files — safe to leave in during development.

### Listing Options

The `list the contents of` phrase supports many options:

```inform7
list the contents of Marley Wood, as a sentence, with newlines and including all contents.
```

| Option | Effect |
|--------|--------|
| `with newlines` | Line breaks before each item |
| `indented` | Indents nested container contents |
| `giving inventory information` | Appends tags like "(closed)" or "(worn)" |
| `as a sentence` | Comma-separated with "and" before last |
| `including contents` | Lists open/transparent container contents |
| `including all contents` | Lists all container contents regardless of opacity |
| `tersely` | Wraps nested items in parentheses |
| `giving brief inventory information` | Minimal tags |
| `using the definite article` | Prefixes items with "the" |
| `listing marked items only` | Filters to pre-marked objects |
| `prefacing with is/are` | Grammar agreement |
| `not listing concealed items` | Omits scenery |

### Value Navigation

For enumerated kinds:
```inform7
first value of colour
last value of colour
colour after orange       [returns yellow]
colour before blue        [returns green]
```

---

## Common Pitfalls Summary

1. **Activities vs. Actions** — Activities are engine-level (printing, listing); actions are game-world (taking, opening)
2. **Activity nesting** — If B starts during A, B must finish during A
3. **`omit contents in listing`** must be called during printing-the-name to take effect
4. **Consecutive bracketed parameters** must be separated by text words
5. **`next` not `continue`** — Inform rejects the word "continue" in loops
6. **`stop` vs. `stop the action`** — Use `stop` in phrases, `stop the action` in action rules
7. **Loop mutation** — Modifying items mid-`repeat running through` is unpredictable; use `while`
8. **Z-machine numeric limit** — Ranges capped at -32768 to 32767
9. **Type consistency** — `let` variables cannot change kinds after creation
10. **`decide on` coverage** — Value-deciding phrases must have `decide on` on every code path
11. **Concealment rules** should explicitly decide yes or no
12. **Switch-style `if ... is:`** cannot use begin/end blocks or `unless`
