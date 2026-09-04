# Inform 7 Rulebooks & Action Processing Reference

## Action Processing Order (The "Waterfall")

Every player command is reduced to a single action. Actions process through these rulebooks in order:

| Stage | Rulebook | Role | Stops action? |
|-------|----------|------|---------------|
| 1 | **Before** | Pre-action setup, unusual pre-conditions | Only with `stop the action` or `instead` |
| 2 | **Instead** | Block or divert the action | Yes (automatically, marks as **failure**) |
| 3 | **Check** | Verify action is reasonable | Only with `instead` or `stop the action` |
| 4 | **Carry out** | Silently change world state | No output — just state changes |
| 5 | **Report** | Tell the player what happened | Default success message |
| 6 | **After** | Custom success responses | Yes (automatically, marks as **success**) |
| 7 | **Every turn** | Background events, timers | Fires after all action processing |

**Design principle:** Before/Instead/After (orange) handle exceptions. Check/Carry out/Report (blue) contain standard behavior.

## Debugging

Type `ACTIONS` during play to see action logging:
```
[taking the fishbowl]
[taking the fishbowl - failed the can't take what's fixed in place rule]
```

## Instead Rules

Bypass normal action handling entirely. The action ends immediately and counts as **failure**.

```inform7
Instead of eating the napkin:
    say "Why not wait for dinner?"

Instead of taking something which is on the grill:
    say "'Hey, you'll burn yourself,' says Mom."
```

**Pitfall:** Instead marks the action as **failed** — the player's intention was not fulfilled. Use After if you want success.

## Before Rules

Execute before checking. Do **not** automatically stop the action.

```inform7
Before taking the napkin, say "(first unfolding its origami swan)".

Before taking the key:
    say "It seems soldered to the keyhole.";
    stop the action.
```

**Control phrases:**
- `stop the action` — stops the rule, the rulebook, and the action
- `continue the action` — ends the current rule, lets the action continue
- Adding `instead` to any instruction within a Before rule stops the action

**Pitfall:** Before rules fire before basic reasonability tests (light, physical access), so they can trigger even in impossible situations.

## After Rules

Execute when an action has already **succeeded**. Automatically suppress the default Report response.

```inform7
After taking the diamonds:
    say "Taken!";

After taking the diamonds:
    say "(Mr Beebe looks up sharply.) ";
    continue the action.    [lets default Report also fire]
```

**Pitfall:** After rules automatically suppress the Report rule. Use `continue the action` if you want the default report to also print.

## Check, Carry Out, Report

The standard three-stage pipeline for defining new action behavior:

```inform7
Understand "cut [something] with [something]" as cutting it with.
Cutting it with is an action applying to two things.

Check cutting it with:
    if the noun is a person, say "That would hurt." instead;
    if the second noun is not a blade, say "[The second noun] hasn't got enough of a blade." instead.

Carry out cutting it with:
    increment the count of rips of the noun.

Report cutting it with:
    say "You slash [the noun] with [the second noun]."
```

**Rules:**
- **Check** — block with error messages using `instead` or `stop the action`
- **Carry out** — silently change state (no output)
- **Report** — produce player-facing messages

## Try and Try Silently

Trigger actions programmatically:

```inform7
try going up.

Before locking the front door:
    try closing the front door;
    if the front door is open, stop the action.

try silently taking the napkin;

Instead of climbing a staircase:
    try entering the noun.
```

**Notes:**
- The action must name a specific object — `try eating something` is disallowed
- `try silently` suppresses messages only on success; failures still produce messages

## Every Turn Rules

Fire as one of the last things each turn, after all action processing:

```inform7
Every turn:
    if the player is in the Kitchen:
        say "The clock ticks."

Every turn when the lantern is lit:
    decrement the fuel of the lantern;
    if the fuel of the lantern is 0:
        now the lantern is unlit;
        say "Your lantern flickers and dies."
```

## Multiple Actions in One Rule

```inform7
Instead of examining, looking under or searching the desk:
    say "There's no use poking around in that old desk."
```

**Pitfall:** All listed actions must accept the same number of objects. `waiting or searching the desk` is an error.

## Doing Something (Wildcard Matching)

```inform7
Instead of doing something to the cucumber sandwich:
    say "Lady Bracknell stares disapprovingly."

Instead of doing something other than looking, examining or waiting:
    say "You must learn patience."

Instead of doing something other than examining with the dagger:
    say "Don't fool around with that dagger."
```

## Rule Location Restrictions

### In Rooms and Regions

```inform7
Instead of taking something in the Supernatural Void:
    say "In this mist you feel unable to grasp anything."

The Public Area is a region. The Arboretum and Gardens are in the Public Area.

Instead of eating in the Public Area:
    say "The curators are ever among you, eagle-eyed."
```

### In the Presence Of, and When

```inform7
Instead of eating something in the presence of Lady Bracknell:
    say "Lady Bracknell disapproves thoroughly."

Instead of eating something when the radio set is switched on:
    say "The howling static puts you right off luncheon."
```

More specific rules take precedence automatically.

## Going Action — Special Syntax

The going action is unique because it involves two locations:

```inform7
Instead of going nowhere from the Front Stacks:
    say "Bookcases obstruct almost all passages."

Before going to the Catalogue Room:
    say "You emerge back into the Catalogue Room."

Instead of going from Neptune to a room which is not in Neptune:
    say "It's a bad time to leave Neptune."
```

### Listing Available Exits

```inform7
Definition: a direction (called thataway) is viable if the room thataway from the location is a room.

Instead of going nowhere:
    let count of exits be the number of viable directions;
    if the count of exits is 0, say "You appear to be trapped." instead;
    if the count of exits is 1, say "The only way out is [list of viable directions].";
    otherwise say "The viable exits are [list of viable directions]."
```

### Go Back

```inform7
The former location is a room that varies.

First carry out going rule:
    now the former location is the location.

Understand "go back" as retreating.
Retreating is an action applying to nothing.

Carry out retreating:
    let way be the best route from the location to the former location, using doors;
    if way is a direction, try going way;
    otherwise say "You can't see an open way back."
```

### Going Through Doors / With Vehicles / Pushing

```inform7
Instead of going nowhere by the trolley:
    say "Don't crash the trolley into walls."

Before going through the green baize door:
    say "Through you go..."

After going a direction (called way-pushed) with something (called the thing-pushed):
    say "You push [the thing-pushed] [way-pushed] to [the location].";
    continue the action.
```

## Kinds of Action

Define custom action categories:

```inform7
Kissing Mr Carr is unmaidenly behaviour.
Doing something to the painting is unmaidenly behaviour.

Instead of unmaidenly behaviour in the Inn:
    say "How unmaidenly!"

Asking someone about something is speech.
Telling someone about something is speech.
Answering someone that something is speech.

Before speech in the presence of an ungreeted person:
    try waving hands.
```

**Pitfall:** `Asking someone to try doing something` (persuasion commands) CANNOT be made into a kind of action.

## Repeated Actions

```inform7
Instead of examining the tapestry for the third time:
    say "All right, so it's a masterpiece..."

Instead of examining the urn at least twice:
    say "It's an urn. What do you want from me?"

Instead of going nowhere for the 20th time:
    say "Do stop walking into walls..."
```

The count tracks **attempts**, not successes.

### Actions on Consecutive Turns

`doing it` means "repeating the same action":

```inform7
Instead of examining the Daily for the first time:
    say "The best article is about swimsuit colours."

Instead of doing it for the second time:
    say "You now know about a weather forecaster's week."

Instead of doing it more than three times:
    say "Nope, you've drained it."
```

## Persuasion Rules

Control whether NPCs consent to player commands. By default, NPCs refuse.

```inform7
Persuasion rule for asking a hypnotized person to try doing something:
    persuasion succeeds.

Persuasion rule for asking the policeman to try doing something:
    persuasion fails.
```

After persuasion succeeds, the NPC's action is still subject to all normal rules (Check/Carry out/Report). Use `Instead of someone trying...` to intercept NPC actions after persuasion. The `person asked` variable references the NPC being commanded.

## Reaching Inside and Outside

Reaching rules determine physical interaction accessibility:

```inform7
Rule for reaching inside a room:
    say "You can only look from this distance.";
    deny access.
```

**Outcomes:** `allow access` or `deny access`

Objects can be visible (in scope) but not touchable (not reachable).

## Out of World Actions

Do not affect the fictional world or advance the turn counter:

```inform7
Requesting the room tally is an action out of world.

Report requesting the room tally:
    say "You have visited [number of visited rooms] out of [number of rooms] room[s]."

Understand "rooms" as requesting the room tally.
```

Out-of-world actions bypass Before/Instead/After rules entirely.

## Stored Actions

Actions can be stored as values, compared, and triggered later:

```inform7
The best idea yet is an action that varies.

A person has an action called death knell.
The death knell of Luckless Luke is pulling the cactus.

if the current action is the death knell of the person asked: ...
```

**Extracting components:**
- `action name part of` — the action name
- `noun part of` — the primary object
- `second noun part of` — the secondary object
- `actor part of` — who is performing the action
- `the current action` — captures the ongoing action

## Conversation Patterns

### Topic-Based Conversation

```inform7
Instead of asking the Sybil about "persians", say "She nods gravely."

Instead of asking the Sybil about "Darius/king", say "Her smile unnerves you."
```

The slash `/` means "or" in topic strings.

### Topic Tokens for Grouping

```inform7
Understand "Athenians/Spartans/Greeks" or "hoplite army/forces" as "[Greeks]".
Instead of asking the Sybil about "[Greeks]", say "She looks encouraging."
```

### Table-Based Conversation

```inform7
Instead of consulting a book about a topic listed in the contents of the noun:
    say "[reply entry][paragraph break]".

Report consulting a book about:
    say "You flip through [the noun], but find no reference to [the topic understood]." instead.
```

## The Other Four Senses

```inform7
A thing has some text called sound. The sound of a thing is usually "silence".
Definition: a thing is audible if the sound of it is not "silence".

Carry out listening to something:
    say "From [the noun] you hear [the sound of the noun]."

Instead of listening to a room:
    if an audible thing can be touched by the player,
        say "You hear [the list of audible things which can be touched by the player].";
    otherwise say "Nothing of note."
```

## Custom Rulebook Stages

You can insert entirely new stages into the action-processing pipeline:

```inform7
The sanity-check rules are a rulebook.

This is the sanity-check stage rule:
    abide by the sanity-check rules.

The sanity-check stage rule is listed after the before stage rule in the action-processing rules.

Sanity-check eating an inedible thing:
    say "Your digestion is so delicate -- [the noun] wouldn't agree with you." instead.
```
