# Inform 7: Descriptions, Adaptive Text, and Dynamic Change

Practical reference extracted from the official Inform 7 documentation (Chapters 6, 8, 9, and 14).

---

## Part 1 -- Descriptions and Quantifiers (Chapter 6)

### What Are Descriptions?

A **description** is a phrase that picks out objects (or values) matching certain criteria. Descriptions are the building blocks of conditions, rules, and queries.

Three forms:
- **Noun-only:** `container`, `dead end`, `wine cask`
- **Adjective-only:** `fixed in place`, `open`
- **Combined:** `openable container`, `open door`

Descriptions power counting and listing:
```inform7
number of open doors
say "[the list of things in the basket]"
```

**Pitfall:** Counting over infinite domains fails. `number of odd numbers` produces a problem message -- Inform can only count finite, enumerable sets.

### Adjectives

Descriptions can stack any number of adjectives but only ONE noun:
```inform7
closed              [adjective only]
open wine cask      [adjective + noun]
something portable  [special noun + adjective]
```

Eight special nouns (`something`, `someone`, `anybody`, `everybody`, `somewhere`, `nowhere`, `nothing`, `nobody`) can appear at the front of a description:
```inform7
anybody male
somewhere dark
something portable
```

**Rule:** You cannot have more than one noun in the same description.

### Sources of Adjectives

Adjectives come from two primary sources:

1. **Either/or properties:** `open`/`closed`, `fixed in place`/`portable`
2. **Kinds of value:**
```inform7
Texture is a kind of value. The textures are rough, stubbly and smooth.
Everything has a texture.
```
This creates three new adjectives: `rough`, `stubbly`, `smooth`.

**Pitfall:** The statement `Everything has a texture` is essential. Without it, Inform does not know these adjectives apply to things and they will not work in descriptions.

Built-in special adjectives: `visible`, `touchable`, `adjacent`

### Defining New Adjectives

Use `Definition:` to create custom adjectives with conditions:
```inform7
Definition: A supporter is occupied if something is on it.
```

**Antonym pairing** with `rather than`:
```inform7
Definition: A room is occupied rather than unoccupied if a person is in it.
```

**Named subjects** for clarity:
```inform7
Definition: a direction (called thataway) is viable if the room thataway from the location is a room.
```

**Common pattern -- "another":**
```inform7
Definition: a person is another if it is not the player.
```

**Rules:**
- Always use `it` to refer to the object being defined, regardless of the object's gender
- Definitions cannot be used when creating objects (not enough info at creation time)
- Definitions are primarily useful in conditions and rules

### Defining Adjectives for Values

Adjectives can apply to values (numbers, text, custom kinds), not just objects:
```inform7
Definition: A number is round if the remainder after dividing it by 10 is 0.
Definition: A time is late rather than early if it is at least 8 PM.
```

**Built-in number adjectives:** `positive`, `negative`, `even`, `odd`

**Built-in text adjectives:** `empty`, `non-empty`

Multiple definitions for the same adjective word can coexist for different kinds -- Inform resolves by examining the noun's kind.

### Scale-Based Adjectives (Whereabouts on a Scale)

For sliding-scale properties, use a strict format:
```inform7
Definition: A container is huge if its carrying capacity is 20 or more.
Definition: A container is large if its carrying capacity is 10 or more.
Definition: A container is standard if its carrying capacity is 7.
Definition: A container is small if its carrying capacity is 5 or less.
```

**Format requirements:**
- Single-word adjectives only
- Use `its` (not `it's`) to reference the property
- Conclude with exact value, `or more`, or `or less`

**Context-dependent definitions:**
```inform7
A person has a number called height.
Definition: A man is tall if his height is 72 or more.
Definition: A woman is tall if her height is 68 or more.
```

`In the Shop are a tall man and a tall woman.` creates a 72-inch man and a 68-inch woman.

**Pitfall:** Objects receive "the most moderate values they can have." A `large` container gets capacity 10 (the threshold), not higher.

### Comparatives and Superlatives

Scale-based definitions automatically generate comparative forms:
```inform7
if the basket is larger than the thimble ...
if the thimble is not larger than the basket ...
if Adam is the same height as Eve ...
```

Exactly one of three relationships is always true:
```inform7
if Adam is taller than Eve ...
if Adam is the same height as Eve ...
if Adam is shorter than Eve ...
```

Superlatives are also auto-generated:
```inform7
the largest container
the smallest open container
```

### Quantifiers (All, Each, Every)

Quantifiers test conditions across entire sets of objects or values.

**Universal quantifiers (all must be true):**
```inform7
if each door is open ...
if every room is smoky ...
if anyone is carrying all of the animals ...
if everybody is in the Dining Room ...
```

**Existential quantifier (at least one true):**
```inform7
if some of the doors are open ...
```

**Majority quantifiers:**
```inform7
if most of the doors are open ...        [> 50%]
if almost all of the doors are open ...   [>= 80%]
```

**Negative quantifiers:**
```inform7
if no door is open ...
if none of the doors is open ...
```

**Pitfall:** Inform cannot process quantifiers over infinite domains. `if every number is positive` fails because the set is unbounded.

### Counting While Comparing

Quantified conditions can require specific numbers:
```inform7
if two women are carrying animals ...
if at most three doors are open ...
if fewer than 10 portable containers are closed ...
if all but two of the devices are switched on ...
if there are more than six locked doors ...
```

**Critical distinction:** `if two doors are open` is true even if THREE doors are open -- it means "at least two." Use `exactly` for precise counts:
```inform7
if exactly two doors are open ...
```

**`all but` is exact:** `if all but two doors are open` is FALSE if all doors are open.

**Syntactic requirement:** The article `the` is mandatory in `two of the doors`. Without it, the phrase may not parse as a quantified condition.

### Which and Who (Restrictive Clauses)

Filter descriptions with relative clauses:
```inform7
a random visible thing which is not the mirror
a random thing in the location
```
```inform7
Instead of searching the mirror:
    say "You see [a random visible thing which is not the mirror] reflected back at you."
```

### Existence Testing

```inform7
if there is a woman in the Summerhouse ...
if there is a woman ...               [checks entire world]
if there are women in the Summerhouse ...
if there is more than one woman in the Summerhouse ...
if there is nobody in the Summerhouse ...
if there is nothing on the mantelpiece ...
```

### Visibility and Touchability

Built-in adjectives for sensory reach:
```inform7
if Helen can see Agamemnon ...
something which can be seen by Helen ...
```

**Pitfall:** The actor must be explicit. `something which can be seen` (no actor) is not valid. Use `something visible` instead.

```inform7
Every turn:
    if the sinister gentleman can touch something valuable
    (called the treasure) which is not carried by a person:
        try the gentleman taking the treasure.
```

### The Word "nothing"

Two distinct meanings:
1. **Absence:** `if the box contains nothing` (no items present)
2. **Null value:** `if its matching key is nothing` (property not set)

Inform decides based on the relationship: `is` triggers meaning 2 (value comparison); containment verbs like `is in` trigger meaning 1.

### The Word "in"

Two meanings depending on context:
1. **Direct containment:** `The ball is in the box` -- only immediate container
2. **Regional containment:** `The Terrace is in the Garden Area` -- when Y is a region

**Pitfall:** `if the croquet ball is in the Summerhouse` is FALSE if the ball is inside a box that is in the Summerhouse. For region-based containment with variables, use: `if the croquet box is regionally in the mystery value`

---

## Part 2 -- Adaptive Text (Chapter 14)

### Tense and Story Viewpoint

**Defaults:** Second person singular, present tense ("You can see a grey cat.").

**Story viewpoint options:** first/second/third person, singular/plural (6 values)
**Story tense options:** past, present, future, perfect, past perfect (5 values)

Change dynamically:
```inform7
now the story viewpoint is first person plural;
now the story tense is past tense.
```

**Critical limitation:** Viewpoint and tense settings only affect system-generated responses (built-in action reports). Your own `say` text must be manually written to match. As the docs state: "the only way for all of our own text to have a particular tense or narrative viewpoint is to write it that way."

**Convenience substitutions:**
- `[here]` -- produces "here" (present) or "there" (other tenses)
- `[now]` -- produces "now" (present) or "then" (other tenses)

### How Inform Reads Adaptive Text

Verb substitutions in square brackets adapt automatically:
```inform7
[are], [have], [carry], [wear], [can], [can see], [can touch]
[are not], [cannot touch]
```

**The key rule:** The verb adapts to the most recently printed object name. This means the verb conjugation depends on what was printed just before it.

```inform7
say "[The noun] [are] pinned down by Dr Zarkov's force field."
```

**Pitfall -- substitution dependency:** Verb adaptation ONLY works when preceded by a text substitution. This works:
```inform7
"[The condensers] [are] working."
```
This does NOT work:
```inform7
"The condensers [are] working."
```
Raw text outside `[` and `]` is not parsed -- Inform does not recognize "The condensers" as an object name when it appears as plain text.

**List handling:**
```inform7
"[The list of things on the bench] [are] smashed by Voltan's birdmen."
```
Correctly produces "The condensers and the V-ray are smashed..." (plural agreement).

**Pitfall -- manual conjunctions break agreement:**
```inform7
"[The condensers] and [the V-ray] [are]"
```
Produces "...is" because `[are]` looks at the most recent substitution (`[the V-ray]`, singular). Use `[The list of...]` instead.

### Adaptive Text Substitutions

**Defining verbs for adaptive use:**
```inform7
To retrofit is a verb.
```
Then use in text:
```inform7
"[The actor] [retrofit] the Mecha-Mole."
```
This auto-conjugates: "You retrofit..." or "General Lee retrofits..."

**Verb participle forms:**
- `infinitive of` -- base form
- `past participle of` -- "retrofitted"
- `present participle of` -- "retrofitting"

**Relating verbs to actions:**
```inform7
Describing relates various verbs to various action names.
The verb to describe means the describing relation.
To look around is a verb.
The verb look around describes the looking action.
```

### Adaptive Text About the Player

Five substitution forms for the player character, using "we/us" convention (treated as plural for verb agreement):

| Substitution | Grammatical role |
|---|---|
| `[We]` / `[we]` | Subject ("I" / "You" / "He" / "We" etc.) |
| `[Us]` / `[us]` | Object ("me" / "you" / "him" / "us" etc.) |
| `[Our]` / `[our]` | Possessive determiner ("my" / "your" / "his" etc.) |
| `[Ours]` / `[ours]` | Possessive pronoun ("mine" / "yours" / "his" etc.) |
| `[Ourselves]` / `[ourselves]` | Reflexive ("myself" / "yourself" / "himself" etc.) |

```inform7
"[We] [carry] the Queen's warrant."
"The birds drop pebbles on [us]. Right on [our] heads!"
"[Ours] are the burdens of office, which [we] take on [ourselves]."
```

**Rule:** Use plural verb forms with these substitutions (`[carry]` not `[carries]`).

### Adaptive Text About Other Things

Third-person pronoun substitutions:

| Substitution | Role |
|---|---|
| `[They]` / `[they]` | Subject |
| `[Them]` / `[them]` | Object |
| `[Their]` / `[their]` | Possessive determiner |
| `[Theirs]` / `[theirs]` | Possessive pronoun |
| `[Themselves]` / `[themselves]` | Reflexive |

Impersonal forms: `[It]`/`[it]`, `[There]`/`[there]`, `[It's]`/`[it's]`, `[There's]`/`[there's]`

**Subject tracking with `[regarding]`:**
```inform7
Instead of examining in the Netherworld:
    say "[regarding the noun][They] [have] no clear outline in this misty netherworld."
```

`[regarding the noun]` prints nothing but tells Inform the subject has changed, so subsequent pronouns agree with the noun.

**Pitfall:** Omitting `[regarding X]` when no prior subject has been printed risks pronouns referring to the wrong object.

**Numerical agreement:**
```inform7
"[regarding the dud count][They] [are] defective."
```
Establishes a number as the subject for singular/plural agreement.

### Adapting Contractions

**Negative contractions:**

| Substitution | Example output |
|---|---|
| `[aren't]` | "aren't" / "isn't" / "wasn't" etc. |
| `[don't]` | "don't" / "doesn't" / "didn't" etc. |
| `[haven't]` | "haven't" / "hasn't" / "hadn't" etc. |
| `[won't]` | "won't" / "wouldn't" etc. |
| `[can't]` | "can't" / "couldn't" |
| `[mustn't]` | "mustn't" |
| `[shouldn't]` | "shouldn't" |
| `[wouldn't]` | "wouldn't" |

**Verb contractions:**
- `['re]` -- contracted "to be" ("I'm", "you're", "he's", "we're")
- `['ve]` -- contracted "to have" ("I've", "you've", "he's", "we've")

```inform7
"[We]['ve] got rhythm. [We]['re] cool."
```
Might produce: "I've got rhythm. I'm cool." or "He's got rhythm. He's cool."

**Special form:** `[They're]` is a convenience substitution equivalent to `[Those]['re]` but produces idiomatic output.

**Full contraction example:**
```inform7
Instead of taking something:
    say "[The noun] [are] pinned down by Dr Zarkov's force field.
    [They] [aren't] free to move. [They] [can't] move. [They] [won't]
    move. [They] [haven't] a chance to move. Anyhow, [they] [don't] move."
```

---

## Part 3 -- Dynamic Change (Chapter 8)

### Changing Values with "now"

The `now` statement modifies variable values at runtime:
```inform7
The prevailing wind is a direction that varies. The prevailing wind is northwest.

Instead of waiting when the prevailing wind is northwest:
    say "A fresh gust of wind bowls you over.";
    now the prevailing wind is east.
```

**Type checking:** `now` validates that the new value matches the declared type.
- `now the prevailing wind is 25` -- FAILS (number, not direction)
- `now the prevailing wind is the Heath` -- FAILS (room, not direction)

**Constants cannot change:** Only variables declared with `that varies` can be modified.
```inform7
Colour is a kind of value. The colours are blue, red and mauve.
now blue is mauve.   [ERROR -- like writing "now 1 is 2"]
```

### Changing the Command Prompt

The command prompt (default `">"`) is a modifiable variable:
```inform7
When play begins: now the command prompt is "What now? ".
```

Dynamic prompts with embedded values:
```inform7
When play begins: now the command prompt is "[time of day] >".
```

The prompt can be changed at any point during gameplay and persists until changed again.

### Changing the Status Line

The status bar has two customizable halves:
```inform7
now the left hand status line is "[the player's surroundings] / [turn count] / [score]";
now the right hand status line is "Time: [time of day]".
```

**Constraint:** Right hand status line should not exceed 14 characters.

For advanced layouts:
```inform7
Include Basic Screen Effects by Emily Short.

Rule for constructing the status line:
    center "[location]" at row 1;
    rule succeeds.
```

### Changing Either/Or Properties

Toggle boolean properties:
```inform7
now the oaken door is open.
```

**Safety:** Inform prevents invalid assignments:
- `now the oaken door is unvisited` -- REJECTED (doors cannot be unvisited)
- Runtime checks catch dynamic errors too

**Permission pattern -- `can be`:**
```inform7
The smart window can be transparent. The smart window is transparent.
Carry out switching off the window: now the window is transparent.
Carry out switching on the window: now the window is opaque.
```

The `can be` declaration is required before assigning non-standard properties.

### Changing Properties with Values

```inform7
now the printed name of the Closet is "Suddenly Spooky Closet".
```

**Three validation checks:**
1. Value type must match (no `now the printed name of the Closet is 7`)
2. Object must be eligible for the property
3. Object must actually possess the property

### Altering Map Connections

```inform7
change the east exit of the Closet to the Tsar's Imperial Dining Salon.
change the west exit of the Closet to nowhere.
```

**Note:** The docs recommend writing rules to control movement rather than directly altering the map when possible.

### Every Turn Rules

Every turn rules execute at the END of each turn, after the player's command is processed:
```inform7
Every turn:
    say "The summer breeze shakes the apple-blossom."
```

**Conditional every turn rules:**
```inform7
Every turn when the location is the Orchard:
    say "The summer breeze shakes the apple-blossom."

Every turn when the player can see the rotting fish:
    say "Your nose twitches involuntarily."
```

**Timing:** Text is said at the end of every turn, NOT at the beginning, and NOT before the player's first command.

**Complex example -- battery system:**
```inform7
Every turn:
    repeat with hollow running through battery compartments:
        if the hollow is part of a switched on device (called the machine):
            if a battery (called cell) is in the hollow:
                decrement the charge of the cell;
                carry out the warning about failure activity with the machine;
                if the cell is discharged:
                    carry out the putting out activity with the machine;
            otherwise:
                carry out the putting out activity with the machine.
```

---

## Quick Reference: Common Pitfalls

| Pitfall | Fix |
|---|---|
| `"The condensers [are] working."` -- verb does not adapt | Use `"[The condensers] [are] working."` -- object name must be in substitution brackets |
| `"[The X] and [the Y] [are]"` -- wrong agreement | Use `"[The list of...]"` for correct plural handling |
| `if every number is positive` -- fails | Quantifiers require finite, enumerable sets |
| `if two doors are open` means "at least 2" | Use `if exactly two doors are open` for precise count |
| `Everything has a texture.` omitted | Required for value-kind adjectives to apply to things |
| `now blue is mauve.` -- constant error | Only `that varies` variables can be changed |
| `[regarding X]` omitted before pronouns | Pronouns refer to wrong object without subject reset |
| `now the door is unvisited` -- property error | Objects can only receive properties they are permitted to have |
| Plain text "in" means direct containment only | Use `regionally in` for region-based containment checks |
