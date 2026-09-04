# Inform 7 Syntax Guide

## Source File Structure

```inform7
"Title" by "Author Name"

The story headline is "A Subtitle".
The story genre is "Fiction".
The release number is 1.
The story creation year is 2026.
The story description is "A brief description."

Part 1 - Setup

Chapter 1 - The World

[... source code ...]
```

### Banner Convention

The compiler auto-generates a startup banner from bibliographic fields. To add custom attribution lines after the banner, use `After printing the banner text` — never `When play begins: say "..."` (creates a double header). See CLAUDE.md "IF Banner Convention" for full details.

## World Model

### Rooms
```inform7
The Kitchen is a room. "You stand in a bright kitchen with checkered tiles."
```
Rooms are places. The quoted text after the room definition is its description (what the player sees on `look`).

### Things
```inform7
The red apple is a thing in the Kitchen. "A red apple sits on the counter."
The description of the red apple is "Crisp and shiny."
```

### Kinds (Custom Types)
```inform7
A weapon is a kind of thing.
A weapon has text called the damage-type.
A weapon has a number called the power.
```
Kind properties use `has` + type + `called the` + property-name.

Available property types: `text`, `number`, `truth state` (boolean)

### Containers and Supporters
```inform7
The wooden box is a container in the Kitchen.
The table is a supporter in the Kitchen.
The vase is on the table.
```

### Scenery
```inform7
The old painting is scenery in the Kitchen. "A faded landscape."
```
Scenery cannot be picked up and is not listed in room descriptions.

### People
```inform7
Bob is a man in the Kitchen. "Bob leans against the counter."
```

## Properties

### Built-in Properties
```inform7
The wooden box is open.          [containers can be open/closed]
The wooden box is openable.      [player can open/close it]
The red apple is edible.         [player can eat it]
The red apple is fixed in place. [cannot be picked up]
```

### Custom Properties
```inform7
A thing has a number called the weight.
The weight of the red apple is 3.

A room has text called the mood.
The mood of the Kitchen is "cheerful".

A person has a truth state called the is-friendly.
Bob is is-friendly.
```

## Understand (Parser Vocabulary)

```inform7
Understand "apple" and "fruit" as the red apple.
Understand "read [something]" as examining.
Understand "help" as requesting help.
Understand "use [something] on [something]" as using it on.
```

## Actions

### Instead Rules (Override Default Behavior)
```inform7
Instead of taking the old painting:
    say "It's bolted to the wall."

Instead of pushing a weapon (called W):
    say "You shove [the W] aside."
```

### Before / After Rules
```inform7
Before taking the red apple:
    say "You reach for the apple."

After taking the red apple:
    say "You pocket the apple. It feels heavy."
```

### Custom Actions
```inform7
[Action applying to nothing — no noun needed]
Requesting help is an action out of world applying to nothing.
Understand "help" as requesting help.
Carry out requesting help:
    say "Try: look, examine, take, inventory."

[Action applying to one thing]
Licking is an action applying to one thing.
Understand "lick [something]" as licking.
Carry out licking:
    say "You lick [the noun]. Weird."

[Action applying to two things]
Using it on is an action applying to two things.
Understand "use [something] on [something]" as using it on.
Carry out using it on:
    say "You try using [the noun] on [the second noun]."
```

### Action Variables
- `the noun` — first thing the action applies to
- `the second noun` — second thing (for two-noun actions)
- `the player` — the player character
- `the location` — current room

## Conditions and Logic

```inform7
if the player carries the red apple:
    say "You have the apple.";
otherwise:
    say "No apple for you."

if the wooden box is open and the wooden box contains the red apple:
    say "The apple is in the open box."

unless the player is in the Kitchen:
    say "You're not in the kitchen."
```

### Comparisons
```inform7
if the power of the sword is greater than 5:
if the weight of the red apple is at least 3:
if the mood of the Kitchen is "cheerful":
```

## Repeated Actions / Every Turn

```inform7
Every turn:
    if the player is in the Kitchen:
        say "The clock ticks."
```

## When Play Begins

```inform7
When play begins:
    say "Welcome to the game.[paragraph break]Type HELP for instructions."
```

## Listing and Iteration

```inform7
repeat with item running through things carried by the player:
    say "[item]: [description of item][line break]";
```

## Relations

```inform7
Friendship relates various people to various people.
The verb to befriend means the friendship relation.

Bob befriends the player.

if Bob befriends the player:
    say "Bob waves warmly."
```

## Tables

```inform7
Table of Clues
clue-text              found
"The butler did it"    false
"Check the garden"     false

To show clues:
    repeat through the Table of Clues:
        if found entry is true:
            say "[clue-text entry][line break]";
```

## Scenes

```inform7
Confrontation is a scene.
Confrontation begins when the player is in the Throne Room.
Confrontation ends when the dragon is dead.

When Confrontation begins:
    say "The dragon roars!"
```

## Releasing for Web (Quixe)

To produce a web-playable version:
1. Compile to Glulx (.ulx) in the Inform 7 IDE
2. Convert .ulx to Base64 JS using `ulx-to-js` tooling
3. Host with Quixe (glkote.min.js, quixe.min.js, jquery)
4. Reference the .ulx.js file in the HTML interpreter page
