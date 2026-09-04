# Inform 7 Advanced World Model Reference

Covers advanced kinds, properties, rooms/regions/backdrops, and relations. For basic syntax see `syntax-guide.md`; for text formatting see `text-formatting.md`.

---

## Part 1 -- Kinds

### The Kind Hierarchy

Every value in Inform 7 has a **kind**. Kinds form a tree rooted at `object`:

```
object
  +-- room
  +-- thing
  |     +-- container
  |     +-- supporter
  |     +-- person
  |     |     +-- man
  |     |     +-- woman
  |     |     +-- animal
  |     +-- device
  |     +-- vehicle
  |     +-- backdrop
  +-- direction
  +-- region
```

Inform infers kinds from context: if something is "in" another thing, the outer thing must be a room or container; if something is "on" another thing, the outer thing is a supporter.

### Creating New Kinds

```inform7
A weapon is a kind of thing.
A dead end is a kind of room.
A Bengal tiger is a kind of animal.
A staircase is a kind of door.
```

Kinds can be chained:
```inform7
A mammal is a kind of animal.
A Bengal tiger is a kind of mammal.
```

Kinds with default properties:
```inform7
A dead end is a kind of room with printed name "Dead End"
    and description "This is a dead end. You'll have to go back the way you came."
```

Creating instances:
```inform7
The Undertomb is a dark room.
East is a dead end.
South is a dead end with printed name "Collapsed Dead End".
Northwest is a dead end called the Tortuous Alcove.
Growler is a Bengal tiger in the Savannah.
```

**Pitfall -- Declaration Order:** The kind must be declared before it is used. This works:
```inform7
A coffer is a kind of container.
In the Crypt is an open coffer.
```
This fails (Inform treats "open coffer" as a single object name):
```inform7
In the Crypt is an open coffer.  [BUG: coffer kind not yet defined]
```

### Plural Assertions

Create multiple objects in one sentence:
```inform7
Bucket and basket are kinds of container.
The high shelf and the skylight window are high-up fixtures in the Lumber Room.
```

Custom plural forms:
```inform7
A brother in law is a kind of man.
The plural of brother in law is brothers in law.
```

Inform handles standard English plurals automatically (oxen, geese, sheep, phenomena, etc.).

### Kinds of Value (Non-Object Kinds)

Values are abstract concepts that are not physical objects.

#### Qualitative (Enumerated) Kinds
```inform7
Brightness is a kind of value. The brightnesses are guttering, weak, radiant and blazing.
```
Use: `The lantern has a brightness. The brightness of the lantern is radiant.`

#### Quantitative (Unit) Kinds
```inform7
Weight is a kind of value. 1kg specifies a weight.
```
Use: `The anvil has a weight called the heft. The heft of the anvil is 26kg.`

---

## Part 2 -- Properties

### Two Types of Properties

1. **Either/or** -- binary toggle (open/closed, lit/unlit, edible/inedible)
2. **Value** -- holds data of a specific kind (text, number, custom kind)

### Either/Or Properties

Declaration:
```inform7
A dead end is either secret or ordinary.
```

Single-state shorthand (opposite is automatically "not secret"):
```inform7
A dead end can be secret.
```

Applying to built-in kinds:
```inform7
A room is either indoors or outdoors.
A person is either awake or asleep. A person is usually awake.
```

Applying to a single object:
```inform7
The umbrella can be open.
```

**Pitfall -- Do not assign either/or properties to a specific object instance when the identity can change.** This is wrong:
```inform7
The player is either asleep or awake.   [BUG: player identity can change]
```
Instead, attach to the kind:
```inform7
A person is either awake or asleep.
```

Full example:
```inform7
A person is either awake or asleep. A person is usually awake.

Instead of sleeping:
    now the player is asleep;
    say "You drop off."

Instead of doing something other than waking up, waiting or sleeping
    when the player is asleep:
    say "Ssh! You're sleeping!"

Instead of waking up when the player is asleep:
    now the player is awake;
    say "You come to suddenly, wiping drool from your lips."
```

### Value Properties

Declaration:
```inform7
A dead end has some text called the river sound.
A thing has a number called the weight.
A person has text called the backstory.
```

Setting values:
```inform7
The river sound of the Tortuous Alcove is "a burbling noise".
The weight of the red apple is 3.
```

Default values:
```inform7
The river sound of a dead end is usually "a quiet trickle".
```

**Checking if a property exists on an object** (safe for mixed kinds):
```inform7
if the noun provides the property river sound:
    say "[the river sound of the noun]";
otherwise:
    say "You hear nothing special."
```

**Checking for empty text values:**
```inform7
if the movement sound of the cart is not "":
    say "[the movement sound of the cart]".
```

### Degrees of Certainty

Four modifiers control how firmly a property is set:

| Modifier | Meaning | Negation |
|---|---|---|
| `always` | Absolute rule, no exceptions | `never` |
| `usually` | Default, can be overridden per-instance | `seldom` |
| `seldom` | Rare default, can be overridden | `usually` |
| `never` | Absolute prohibition | `always` |

```inform7
A dead end is usually dark.
A staircase is never openable.
A staircase is usually open.
```

More specific instructions override less specific ones:
```inform7
A dead end is usually dark.
The Tortuous Alcove is lighted.   [overrides the "usually dark" default]
```

Default descriptions for entire kinds:
```inform7
The description of a thing is usually "You give [the noun] a glance,
    but it is plainly beneath your attention."
The infant is a man in the basket. The description of the infant is
    "So strong and fat that you wonder..."   [overrides the default]
```

---

## Part 3 -- Rooms, Doors, Regions, and Backdrops

### Rooms and the Map

Basic room creation:
```inform7
The Cobble Crawl is a room. "You are crawling over cobbles in a low passage."
```

Connecting rooms (bidirectional by default):
```inform7
The Debris Room is west of the Crawl.
Above the Debris Room is the Sloping Canyon.
West of the Canyon is the Orange River Chamber.
```

Player starting location (defaults to first room created):
```inform7
The player is in the Cobble Crawl.
```

#### One-Way and Bent Connections

By default, `The Debris Room is west of the Crawl` implies the Crawl is east of the Debris Room.

Bent routes (path does not retrace):
```inform7
West of the Garden is south of the Meadow.
```

Dead ends (direction leads nowhere):
```inform7
East of the Debris Room is nowhere.
```

**Pitfall -- Complex sentences suppress bidirectional assumption:**
```inform7
The Attic is above the Parlour.        [creates two-way connection]
The Attic is a dark room above the Parlour.  [creates one-way connection only!]
```

#### Room Description Options

Brief mode (description shown only on first visit):
```inform7
Use brief room descriptions.
```

Conditional first-visit text:
```inform7
"[if unvisited]Welcome to the garden for the first time![end if]Flowers bloom everywhere."
```

Checking all objects have descriptions (debugging):
```inform7
When play begins:
    repeat with item running through things:
        if description of the item is "":
            say "[item] has no description."
```

### Kinds of Room

```inform7
A dead end is a kind of room with printed name "Dead End"
    and description "This is a dead end."
A dead end is usually dark.
```

All instances inherit the kind's properties:
```inform7
East is a dead end.
South is a dead end with printed name "Collapsed Dead End".
```

### Doors

Doors connect exactly two rooms and are visible from both sides.

```inform7
The magician's booth is a door.
The magician's booth is inside from Center Ring and outside from Starry Void.
```

Conditional descriptions based on location:
```inform7
The magician's booth is a door. "[if the player is in Center Ring]A booth
    stands in the corner, painted dark blue with gold stars.[otherwise if the
    magician's booth is closed]A crack of light indicates the way out.[otherwise]The
    door stands open to the outside.[end if]".
```

Auto-open before entry:
```inform7
Before going through the closed magician's booth:
    say "(first opening the door of the booth)[command clarification break]";
    silently try opening the booth.
```

Staircase pattern (always-open, non-openable door):
```inform7
A staircase is a kind of door. A staircase is usually open.
A staircase is seldom openable.
The ladder is a staircase. It is above the Woodshed and below the Scary Loft.
```

### Regions

Regions group rooms into larger areas for applying rules or properties.

```inform7
The Public Area is a region.
The Arboretum and Gardens are in the Public Area.
```

Nested regions (one must be entirely inside the other; no partial overlap):
```inform7
The University Parks is a region.
The Public Area is in the University Parks.
```

Non-contiguous regions are allowed:
```inform7
Military Holdings is a region.
Fort Carlisle and Fort James are in Military Holdings.
```

Regions are useful for:
- Applying rules to whole areas (`Instead of listening in the Public Area: ...`)
- Color-coding rooms on the World Index map
- Placing backdrops across multiple rooms

### Backdrops

Backdrops are things that exist in multiple locations simultaneously. They are always fixed in place and treated as scenery by default.

Basic creation:
```inform7
The stream is a backdrop. It is in the Upper Cave and the Rock Pool.
```

Placed in a region (appears in every room in that region):
```inform7
The Outdoors Area is a region.
The Moon is a backdrop. The Moon is in the Outdoors Area.
```

Everywhere:
```inform7
The sky is a backdrop. The sky is everywhere.
```

Combined region + specific rooms:
```inform7
The Moon is a backdrop. The Moon is in the Outdoors Area. The Moon is in the Skylight Room.
```

With description:
```inform7
The view of the glacier is a backdrop. It is everywhere.
The description is "The Malaspina glacier covers much of the nearby slope."
```

**Key facts:**
- Backdrops are always fixed in place (cannot be taken)
- Backdrops are scenery by default (not listed in room descriptions unless examined)
- Backdrops can be moved dynamically at runtime (see the Moving Backdrops section in the full documentation)

---

## Part 4 -- Relations

### What Are Relations?

Relations are yes/no questions about pairs of things. They are the semantic foundation that verbs express. Multiple verb phrasings can express the same relation:

```
"The coin is in the purse."         -- containment relation
"The purse contains the coin."      -- same relation, different verb
"The coin is contained by the purse." -- same relation, passive voice
```

### Built-in Relations

| Relation | Example | Verb |
|---|---|---|
| Containment | The coin is in the purse | to contain |
| Support | The coin is on the table | to support |
| Incorporation | The handle is part of the door | to incorporate / to be part of |
| Carrying | The coin is carried by Peter | to carry |
| Wearing | The jacket is worn by Peter | to wear |
| Possession | if Mr Darcy has a rapier | to have (carrying or wearing) |
| Adjacency | The Study is east of the Hallway | to be adjacent to |
| Visibility | if Darcy can see Elizabeth | to be able to see |
| Touchability | if Darcy can touch Elizabeth | to be able to touch |
| Concealment | if Darcy conceals a fob watch | (testable only, not declarable) |

The five physical relations (containment, support, incorporation, carrying, wearing) are **mutually exclusive** -- an object can satisfy only one at a time.

### Built-in Assertion Verbs and Their Relations

| Verb | Relation |
|---|---|
| to be | equality relation |
| to have | possession relation |
| to contain | containment relation |
| to support | support relation |
| to carry | carrying relation |
| to wear | wearing relation |
| to incorporate | incorporation relation |
| to be part of | reversed incorporation relation |
| to be adjacent to | adjacency relation |
| to mean | meaning relation |
| to provide | provision relation |

### Creating New Relations

Syntax:
```inform7
[Name] relates [quantity] [kind] to [quantity] [kind].
```

#### Relation Cardinalities

| Cardinality | Syntax | Meaning |
|---|---|---|
| One-to-one | `relates one person to one person` | Each side has at most one partner |
| One-to-various | `relates one person to various people` | Left side maps to many on right |
| Various-to-one | `relates various people to one person` | Many on left map to one on right |
| Various-to-various | `relates various people to various people` | Many-to-many |
| Symmetric | `relates people to each other` | If A relates to B, B relates to A |
| Groups | `relates people to each other in groups` | Transitive symmetric grouping |

Examples:
```inform7
Loving relates one person to one person.
Impressing relates one person to various people.
Suspicion relates various people to one person.
Fancying relates various people to various people.
Acquaintance relates people to each other.
Alliance relates people to each other in groups.
```

#### Named Roles

One side of a relation can be given a name for reference:
```inform7
Pet-ownership relates various animals to one person (called the owner).
```
Now `the owner of Loulou` works as a phrase.

**Pitfall:** You cannot name the "various" side because the result would be ambiguous (which pet of Flaubert?).

```inform7
Marriage relates one person to another (called the spouse).
```
Now `the spouse of John` returns Yoko.

### Defining Verbs for Relations

Syntax:
```inform7
The verb to [verb] means the [relation name] relation.
```

Examples:
```inform7
Loving relates one person to one person.
The verb to love means the loving relation.

Suspicion relates various people to one person.
The verb to suspect means the suspicion relation.
The verb to be suspicious of means the suspicion relation.
```

Both forms are then equivalent:
```inform7
Hercule Poirot suspects Colonel Hotchkiss.
Hercule Poirot is suspicious of Colonel Hotchkiss.
```

Inform auto-conjugates: "he loves", "they love", "he loved", "it is loved", "he is loving", "he had loved".

#### Reversed Verbs

Swap subject/object with `reversed`:
```inform7
The verb to grace means the reversed wearing relation.
```
Now `A Tory rosette graces Mr Wickham` means Mr Wickham wears the rosette.

#### Multi-Word Verbs

Up to 29 characters:
```inform7
The verb to cover oneself with means the wearing relation.
Peter is covering himself with a tent-like raincoat.
```

#### Auxiliary Verbs

```inform7
The verb to be able to approach means the approachability relation.
```

### Using Relations

#### In Assertions (Setting Initial State)
```inform7
Bob loves Alice.
Hercule Poirot suspects Colonel Hotchkiss.
```

#### In Conditions (Testing)
```inform7
if Bob loves Alice: ...
if Hercule Poirot suspects someone: ...
if the player is suspicious of the Colonel: ...
```

#### At Runtime (Changing with "now")
```inform7
now the player loves the second noun.
now the player does not love anyone.
now the noun suspects the second noun.
now every person does not fancy the noun.
now the player helps the blessed one.
now the player does not help the vilified one.
```

For symmetric relations, setting one direction automatically updates the reverse:
```inform7
now the noun is married to the second noun.
[automatically: now the second noun is married to the noun]
```

#### In Descriptions
```inform7
the list of people loved by the noun
something which underlies the noun
things which are in the teapot
people who can see the mouse
```

### Symmetric and Group Relations

**Symmetric** (each-other): If A knows B, then B automatically knows A.
```inform7
Meeting relates people to each other.
The verb to know means the meeting relation.
```

**Groups** (each-other in groups): Transitive grouping. If A helps B and B helps C, then A helps C.
```inform7
Alliance relates people to each other in groups.
The verb to help means the alliance relation.
```

Transmutation example (grouping objects):
```inform7
Transmutation relates things to each other in groups.
The verb to become means the transmutation relation.
The bag of gunpowder becomes the bag of jelly beans.
```
Now both items are in the same transmutation group.

### Relation Route-Finding

Find paths through chains of relations (useful for puzzles, layered clothing, etc.):

```inform7
next step via the overlooking relation from the Folly to the Chinese Lake
```
Returns the next object in the shortest path, or `nothing` if no path exists.

```inform7
number of steps via the overlooking relation from the Folly to the Chinese Lake
```
Returns the path length (0 if same object, -1 if no route).

For performance on large relation graphs:
```inform7
Overlying relates various garments to various garments with fast route-finding.
```
Uses more memory but enables faster lookups. Only applies to various-to-various relations.

### Derived Definitions from Relations

```inform7
Definition: a room is sloping if it overlooks a room.
Definition: a thing is uppermost if it is not under something.
```

### Debugging Relations

The `RELATIONS` testing command prints the current state of all custom relations:
```
> RELATIONS
Loving relation:
  Bob >=> Alice
  Alice >=> nobody
Alliance relation:
  {Bob, Charlie, Dave}
```

The phrase `show relation` can also be used in code:
```inform7
show relation the loving relation.
```

### Practical Patterns

#### Clothing Layers (Various-to-Various with Route-Finding)
```inform7
Overlying relates various things to various things.
The verb to be over means the overlying relation.
Underlying relates various things to various things.
The verb to underlie means the underlying relation.

Carry out wearing:
    if the noun covers something (called the hidden item) worn by the player,
        now the hidden item underlies the noun.

Before taking off something which underlies something
    (called the impediment) which is worn by the player:
    silently try taking off the impediment;
    if the noun underlies something which is worn by the player,
        stop the action.
```

#### Telephone Connection (One-to-One Reciprocal)
```inform7
Connection relates one thing to another (called the other party).
The verb to reach means the connection relation.

Carry out calling it on:
    now the player reaches the listener.

Carry out hanging up:
    now the player does not reach anyone.
```
Because `connection` is one-to-one reciprocal, calling a new person automatically disconnects the previous call.

#### Puzzle Dependencies
```inform7
Explaining relates one thing to various things.
The verb to explain means the explaining relation.

Requiring relates one thing to various things.
The verb to require means the requiring relation.
```

#### Concealment System
```inform7
Rule for deciding the concealed possessions of something:
    if the particular possession is secret, yes;
    otherwise no.
```

#### Enclosure-Aware Dropping
```inform7
Before dropping something:
    if the player does not carry the noun and the player encloses the noun:
        say "(first taking [the noun] from [the holder of the noun])[command clarification break]";
        silently try taking the noun;
        if the player does not carry the noun, stop the action.
```

---

## Quick Reference Card

### Kind Declaration
```
[Name] is a kind of [parent kind].
```

### Either/Or Property
```
A [kind] is either [state1] or [state2].
A [kind] can be [state].              [opposite is "not state"]
A [kind] is usually [state].          [sets default]
```

### Value Property
```
A [kind] has [value-kind] called the [name].
The [name] of a [kind] is usually [default].
```

### Certainty Modifiers
```
always / usually / seldom / never
```

### New Relation
```
[Name] relates [one/various] [kind] to [one/various] [kind].
[Name] relates [kind] to each other.           [symmetric]
[Name] relates [kind] to each other in groups.  [transitive symmetric]
```

### New Verb
```
The verb to [verb] means the [name] relation.
The verb to [verb] means the reversed [name] relation.
The verb to be [adjective phrase] means the [name] relation.
```

### Runtime Relation Changes
```
now [A] [verb] [B].
now [A] does not [verb] [B].
now [A] does not [verb] anyone/anything.
```

### Backdrop
```
[Name] is a backdrop. It is in [room/region].
[Name] is a backdrop. It is everywhere.
```

### Region
```
[Name] is a region.
[Room] is in [region].
[Region] is in [parent region].
```
