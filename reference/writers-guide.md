# Fever Dream — Writer's Guide

This is the internal style guide for *Fever Dream*, a parser-based interactive fiction game written in Inform 7. It covers prose voice, room design, object writing, puzzle philosophy, and pacing. It does not cover Inform 7 syntax, compilation, testing, or the build pipeline — those live in `C:\code\i7\CLAUDE.md` and its reference files.

These rules are opinionated and specific to this project. They synthesize ideas from Roger Giner-Sorolla's "Crimes Against Mimesis," Graham Nelson's *DM4*, Emily Short's design writings, and Andrew Plotkin's craft advice, but they are not a textbook. Where established theory conflicts with what this game needs, the game wins.

---

## 1. Tone and Voice

Write in **second person, present tense, active voice**. "You" is the protagonist. The protagonist is the player. Do not split them apart — avoid constructions where the narrator describes the protagonist's thoughts as separate from the player's experience, or where the game mechanic voice interrupts the fiction voice. One person sees, acts, and decides.

**The fever-dream register:** Concrete, sensory, and slightly wrong. The uncanny comes from precision, not from vague atmosphere. A hallway is "tiled in teeth" — that is concrete and wrong. A hallway is "eerie and unsettling" — that is lazy. Describe what is there. Let the wrongness speak for itself.

**Ban list.** These words are almost never the right choice. They tell the player to feel something instead of giving them something to feel:

> eerie, ominous, mysterious, strange, weird, creepy, haunting, foreboding, inexplicable, otherworldly, eldritch, unsettling, uncanny

If you reach for one of these, stop. Describe the specific sensory detail that made you reach for it. Write that instead.

**Show, don't tell.** A room where the walls are damp and the ceiling sags under the weight of something soft tells the player more than a room described as "menacing." Trust the details.

**No meta-commentary.** No fourth-wall breaks. No winking at the player about game mechanics. No "you can't do that in this story" phrasing. The world is real to the protagonist. Responses should stay inside the fiction, even refusals.

---

## 2. Room Descriptions

**Initial description: 2–4 sentences.** This is the text printed when the player first enters a room. It establishes spatial identity — what kind of place is this, what is its dominant sensory quality, and what draws attention. It is not an inventory.

**Maximum 5 interactive objects per room.** This counts everything the player can meaningfully interact with: takeable objects, scenery with custom EXAMINE responses, containers, NPCs. If a room needs more than five, split it into two rooms or demote objects to background flavor mentioned only in the room description with no interaction.

**Maximum 2 takeable objects per room.** Rooms with more than two things to pick up feel like supply closets. If the player needs to gather materials, spread them across the map.

**Few particular details over many generic ones.** A room with a cracked mirror and a chair missing one leg is more vivid than a room with a mirror, a chair, a table, a rug, and a lamp. Each detail you include costs the player's attention. Spend wisely.

**Weave exits into prose.** Do not append "Exits: north, east" to room descriptions. Work directions into the text naturally: "A corridor stretches north. To the east, a door stands slightly open." If an exit is non-obvious, the player should discover it through exploration or puzzle-solving, not by reading a menu.

**Reserve detail for interaction.** The room description is a first impression. The real texture lives in EXAMINE, TOUCH, SMELL, LISTEN. A room description that mentions the wallpaper is peeling is good. A room description that spends a sentence on the wallpaper pattern, another on the paste underneath, and another on what the exposed wall looks like is frontloading — save that for when the player examines the wallpaper.

**Override default listings.** Inform's default "You can see X here" lines break tone. Write custom initial appearance text for objects, or fold their presence into the room description. Every room's first impression should read as a single coherent paragraph, not prose followed by a bulleted grocery list.

**Revisit text.** When the player returns to a room, they see a shorter description. Write one. It should be 1–2 sentences that re-establish the room's identity and note any changes since the first visit.

---

## 3. Object Writing

**Every object gets a custom EXAMINE.** No object should ever produce "You see nothing special about the [noun]." If it is in the game, it matters enough to describe.

**EXAMINE text: 1–2 sentences.** It should add information not present in the room description. The room description says there is a mirror on the wall. EXAMINE says the glass is dark and your reflection is a half-second behind. New information, same economy.

**Sensory descriptions over functional labels.** Prefer "a heavy brass key, warm to the touch" over "a key for the basement door." The first is a description; the second is a spoiler.

**Multi-purpose objects over single-use.** An object the player uses once and discards teaches them that every object is a disposable puzzle token. An object with multiple uses — or one that is useful in a puzzle *and* interesting to examine, carry, and experiment with — feels like part of a world.

**Include atmospheric objects.** Not every interactable thing should be a puzzle piece. If the player learns that every object they can pick up is needed for a puzzle, they stop exploring and start optimizing. Include objects that exist only for atmosphere, worldbuilding, or characterization. These train the player to engage with the world rather than strip-mine it.

**Objects must belong to their context.** A first-aid kit in a bathroom makes sense. A rubber duck in a furnace room does not — unless the game has established why it is there. This is Giner-Sorolla's Crime #1: objects that exist only because the designer needed a puzzle component, with no fictional justification. Every object should have a reason to be where it is, independent of any puzzle it serves.

**Sharp name differentiation.** If two objects could be confused by the parser — two keys, two bottles, two doors — give them names that are immediately distinct in their first word. "The brass key" and "the iron key" are fine. "The small key" and "the small rusted key" will cause disambiguation pain. Test every noun phrase against the parser before shipping.

---

## 4. Puzzle Design

### Fairness

A puzzle is fair if a first-time player can solve it without using save/restore as a crutch. This means:

- The player has all the information they need before they encounter the lock.
- The solution uses objects and verbs the game has already established.
- Failure does not produce an unrecoverable state.

**Clue before lock — always.** The player should encounter the hint, the tool, or the knowledge before they encounter the obstacle it solves. If the player finds a locked door, they should have already seen or picked up something that points toward the solution — even if they didn't recognize it as a clue at the time. A lock the player has no context for is not a puzzle; it is a wall.

### Breaking the Pattern

Parser games train players to think "one object, one puzzle." Fight this:

- **Multi-object solutions.** A puzzle that requires combining two objects, or using an object in conjunction with a room feature, resists the one-to-one mapping.
- **Multi-purpose objects.** An object that solves one puzzle and also has a use elsewhere.
- **Alternative solutions.** Where plausible, accept more than one approach. Even if one solution is "intended," a creative alternative that works within the world model should not be blocked for no reason.
- **Atmospheric red herrings.** Objects that exist for atmosphere (see Section 3) naturally break the assumption that everything is a puzzle piece.

### Spatial Distribution

**No room contains both a puzzle and its complete solution.** If the locked door and the key are in the same room, the puzzle is just a chore. Spread puzzles across the map. The clue, the tool, and the obstacle should occupy different rooms.

**Clue within 3–4 rooms of its puzzle.** Spatial distribution does not mean scattering things at random across twenty rooms. The player should be able to connect clue to puzzle through local exploration, not by exhaustively re-searching the entire map. A clue placed 3–4 rooms from its puzzle is far enough to require thought, close enough to be discoverable.

### Rewards

**Reward with new areas or scenes**, not just a score increment. The best reward for solving a puzzle is a door that opens onto somewhere new — new rooms, a new NPC interaction, a change in the world state that opens further exploration. Points are bookkeeping. New content is a reward.

**Partial progress must be visible.** If a puzzle has multiple steps, each step should produce observable feedback. The player tries something and the world visibly changes, even if the puzzle is not yet solved. This confirms they are on the right track and sustains momentum.

### Difficulty Curve

**Alternate hard and easy puzzles.** A string of hard puzzles exhausts; a string of easy ones bores. After a difficult puzzle, give the player something straightforward or a stretch of pure exploration. Let them catch their breath.

### Verb Synonyms

**Support synonyms.** Verb-guessing is not a puzzle. If the solution is to "push the lever," also accept PULL, MOVE, PUSH, FLIP, THROW, TOGGLE, and any other verb a reasonable player might try. Parsing should be generous. Test by listing every verb you would try if you were the player, then implementing all of them.

### Transcript-First Design

**Write a sample transcript before coding.** Before implementing a puzzle, write out the ideal player interaction as a transcript: what the player types, what the game prints. This catches pacing problems, missing responses, and unfair leaps before they are baked into code.

### Puzzle Documentation Template

When designing a new puzzle, fill out this template before writing any Inform 7 source:

```
Puzzle name:
Location (room):
Obstacle (what blocks the player):
Solution (step by step):
Required objects:
Clue locations (room + what the clue is):
Wrong-attempt responses (at least 3):
Reward (what opens up):
Transcript draft (ideal solve path):
```

---

## 5. Failure Messages

**Every failure is a writing opportunity.** When the player tries something that does not work, the response is a chance to build atmosphere, reveal character, or nudge them toward the right approach. "You can't do that" is wasted space.

**Tiered responses.** On the first wrong attempt, describe what happens. On the second, vary the text — perhaps the protagonist notices something new, or the failure manifests differently. On the third, consider a gentle nudge. Repeated identical failure text is a signal that the author stopped caring.

**Override default library messages.** For every prominent object — anything the player is likely to interact with — replace the default Inform library responses with custom text. "That's not something you can open" becomes "You press your fingers into the seam, but the edges are fused. Whatever sealed this did not intend for it to be opened again."

**Never mock the player.** Failure messages should not be sarcastic, condescending, or punishing. The player tried something. Respect the attempt. Redirect with grace.

**Length: 1 sentence.** Occasionally 2 if the response reveals important information. Failure messages fire frequently; they must not slow the game's rhythm.

---

## 6. NPC Writing

**NPCs are not puzzle dispensers.** Every NPC should have at least one behavior, response, or characteristic that exists independently of any puzzle they are involved in. The player should be able to interact with them in ways that are interesting even if no puzzle is advanced. An NPC who only exists to give a hint and then goes silent is furniture.

**Minimum 3 conversation responses:**

1. **Relevant topic.** Something the NPC would naturally talk about or react to.
2. **Irrelevant topic.** Something the player might bring up that the NPC deflects, ignores, or responds to in character.
3. **Default.** A response for unrecognized topics that characterizes the NPC rather than producing a generic "they don't seem interested."

**Characterize through objects and behavior.** What an NPC carries, wears, fidgets with, or stands near tells the player more than a paragraph of exposition. An NPC who keeps adjusting a ring on their finger is more memorable than an NPC described as "nervous-looking."

**NPCs acknowledge world changes.** If the player has done something significant — solved a puzzle, opened a new area, changed the environment — NPCs in the vicinity should react, even if the reaction is minor. A world where NPCs are oblivious to change is a world that feels like a diorama.

---

## 7. Pacing and Flow

**After 3+ sentences of uninterrupted text, the player should be able to act.** Long text dumps break the core loop of parser IF: read, think, type, read. If a scene requires extended narration, break it into beats separated by player input — even if that input is as simple as pressing a key to continue or walking into the next room.

**2–4 meaningful actions per room.** A "meaningful action" is one with a custom response — not a default library message. If a room only supports EXAMINE on its objects and nothing else, it is underdeveloped. Can the player LISTEN and hear something? TOUCH a surface and feel something? PUSH something and have it react? Each room should offer a small vocabulary of rewarding interactions.

**For every puzzle room, 1–2 atmosphere rooms.** Not every room should block the player with a challenge. Intersperse puzzle rooms with rooms that exist for exploration, mood, and worldbuilding. These rooms give the player breathing space, build the world's texture, and prevent the game from feeling like a sequence of locked doors.

**Puzzles gate clusters, not single rooms.** A puzzle should not unlock one room. It should unlock a cluster of 2–4 rooms — a new wing, a new floor, a new area to explore. This makes the reward proportional to the effort and gives the player a burst of exploration after a moment of constraint.

**EXAMINE nesting: 2 layers maximum.** The player can EXAMINE an object, and examining it may mention a sub-detail they can also examine. But do not go deeper than two layers. EXAMINE DESK reveals a drawer. EXAMINE DRAWER reveals its contents. There is no third layer. Deep nesting turns exploration into a pixel hunt.

**Scene transitions need framing text.** When the game shifts modes — entering a new region, triggering a timed sequence, starting a conversation — print a line or two that signals the shift. The player should never feel disoriented by a sudden mechanical change without narrative context.

---

## 8. World Consistency

**Single genre: surreal horror.** Dreamlike, unsettling, reality-bending. Things are concrete but wrong — a staircase whose steps are one inch too tall, a window that looks out onto a room you are standing in, a clock with thirteen hours that keeps time. The horror is not gore or jump scares. It is the slow recognition that the world is not working as it should.

Do not break genre. No comedy relief rooms. No sudden science fiction. No fantasy elements that do not fit the dream logic. The surreal register established in the opening must hold throughout.

**Inventory realism.** Puzzle design must respect what the player is carrying. Do not assume infinite inventory or weightless objects. If an object is heavy, the game should acknowledge it. If a puzzle requires three objects used simultaneously, the player must be able to carry all three.

**Puzzles arise from the world.** A puzzle should feel like a natural consequence of the environment. A door is locked because doors lock. A passage is blocked by rubble because something collapsed. A machine requires a missing component because machines break. Do not place arbitrary obstacles — combination locks in medieval castles, colored gem puzzles in office buildings — that exist outside the world's internal logic.

**Consistent object behavior.** If one door in the game responds to OPEN, every door responds to OPEN — even if the response is "It won't budge." If one container can be searched, every container can be searched. The player builds a mental model of what verbs work on what kinds of things. Inconsistency punishes them for learning.

**Protagonist identity.** The protagonist has a consistent identity that surfaces in refusal messages and reactions. When the player tries something the protagonist would not do, the refusal should feel like characterization: "You reach for it, then stop. You don't want to know what it feels like." This is not the narrator lecturing the player — it is the protagonist expressing a consistent self.

---

## 9. Pre-Writing Checklists

### Before Writing a Room

- [ ] **Spatial identity.** Can you describe this room's function or character in one phrase? ("the flooded kitchen," "the hallway of doors," "the room with no ceiling")
- [ ] **Detail count.** Have you chosen 2–3 specific details rather than 5–6 generic ones?
- [ ] **Object count.** Are there 5 or fewer interactive objects? 2 or fewer takeable?
- [ ] **Action count.** Are there 2–4 custom responses beyond EXAMINE?
- [ ] **Exits.** Are exits woven into the prose?
- [ ] **Revisit text.** Have you written a shorter return description?

### Before Writing a Puzzle

- [ ] **Fairness.** Can a first-time player solve this without save/restore?
- [ ] **Clue before lock.** Does the player encounter the clue before the obstacle?
- [ ] **Clue proximity.** Is the clue within 3–4 rooms of the puzzle?
- [ ] **Spatial separation.** Are the puzzle and its complete solution in different rooms?
- [ ] **Transcript draft.** Have you written a sample interaction?
- [ ] **Wrong attempts.** Have you written at least 3 distinct failure responses?
- [ ] **Verb synonyms.** Have you listed and implemented every reasonable verb?
- [ ] **Reward.** Does solving this open new content (rooms, scenes, NPC reactions)?

### After Completing a Section

- [ ] **Read aloud.** Read every room description and EXAMINE text aloud. Cut anything that sounds like filler.
- [ ] **Object audit.** Check every object in the section: does it have a custom EXAMINE? Does it belong in its room? Could it be confused with another object?
- [ ] **Default message check.** Try every common verb on every prominent object. Replace any default library responses that break tone.
- [ ] **Ban list scan.** Search the section's text for words on the ban list (Section 1). Replace them.

---

## 10. Quick Reference Card

| Guideline | Target |
|---|---|
| Room description (initial) | 2–4 sentences |
| Room description (revisit) | 1–2 sentences |
| Interactive objects per room | max 5 |
| Takeable objects per room | max 2 |
| EXAMINE text | 1–2 sentences |
| Failure message | 1 sentence (rarely 2) |
| Meaningful actions per room | 2–4 |
| EXAMINE nesting depth | max 2 layers |
| Puzzle clue proximity | within 3–4 rooms |
| Puzzle gate size | 2–4 rooms unlocked |
| Atmosphere-to-puzzle room ratio | 1–2 atmosphere rooms per puzzle room |
| NPC conversation responses | min 3 (relevant, irrelevant, default) |
| NPC non-puzzle behaviors | min 1 |
| Uninterrupted text before player input | max 3 sentences |

---

## 11. Bibliography

- **Roger Giner-Sorolla**, "Crimes Against Mimesis." Foundational essay on immersion-breaking design in IF. The primary source for our rules on object context, world consistency, and avoiding the narrator/protagonist/player split.
- **Graham Nelson**, *The Inform Designer's Manual* (DM4), particularly §50 ("The Design of Puzzles"). Covers fairness, difficulty curves, and the relationship between puzzle design and narrative.
- **Andrew Plotkin**, various essays on IF craft. Influential on our approach to verb synonyms, parser generosity, and the principle that a puzzle should teach the player how to solve it.
- **Emily Short**, collected writings on IF design. Influential on our NPC design philosophy, conversation systems, pacing, and the principle that every interaction is a characterization opportunity.
