[Verb Help System — Reusable Template for Inform 7 Games]
[Copy this Chapter into your story.ni to reduce guess-the-verb frustration.]
[Each section is independent — include all or cherry-pick what you need.]
[See reference/verb-help.md for customization and extension guidance.]

Chapter - Verb Help System

Section 1 - Enhanced Parser Errors

Rule for printing a parser error when the latest parser error is the not a verb I recognise error:
	say "I don[apostrophe]t know that command. Type VERBS for a list, or try simpler phrasing like VERB NOUN."

Rule for printing a parser error when the latest parser error is the didn't understand error:
	say "I understood some words but not the whole command. Try: VERB NOUN (e.g., TAKE KEY, OPEN DOOR)."

Rule for printing a parser error when the latest parser error is the can't see any such thing error:
	say "You don[apostrophe]t see that here. Try LOOK to see what[apostrophe]s around, or INVENTORY to check what you carry."

Rule for printing a parser error when the latest parser error is the said too little error:
	say "That command needs more detail. Try VERB NOUN (e.g., EXAMINE TABLE, not just EXAMINE)."

Rule for printing a parser error when the latest parser error is the only understood as far as error:
	say "I only understood part of that. Try rephrasing with a simpler command."

Section 2 - Help and Verbs Commands

Requesting the verb list is an action out of world applying to nothing.
Understand "verbs" and "commands" as requesting the verb list.

Carry out requesting the verb list:
	say "Movement:  NORTH (N), SOUTH (S), EAST (E), WEST (W), UP (U), DOWN (D), IN, OUT[line break]";
	say "Looking:   LOOK (L), EXAMINE (X) thing, SEARCH thing, LOOK IN/UNDER thing[line break]";
	say "Taking:    TAKE thing, DROP thing, PUT thing IN/ON thing, GIVE thing TO person[line break]";
	say "Using:     OPEN, CLOSE, LOCK/UNLOCK thing WITH key, PUSH, PULL, TURN ON/OFF[line break]";
	say "Talking:   ASK person ABOUT topic, TELL person ABOUT topic, SAY [quotation mark]text[quotation mark][line break]";
	say "Self:      INVENTORY (I), WAIT (Z), WEAR thing, EAT/DRINK thing[line break]";
	say "Meta:      SAVE, RESTORE, UNDO, SCORE, HELP, VERBS, RESTART, QUIT".

Requesting help is an action out of world applying to nothing.
Understand "help" and "hint" and "hints" as requesting help.

Carry out requesting help:
	say "This is a text adventure. Type commands in plain English.[line break]";
	say "Most puzzles can be solved with simple two-word commands: VERB NOUN.[line break]";
	say "Type VERBS for a full list of available commands.[line break]";
	say "Type LOOK to see your surroundings. Type INVENTORY (or I) to check what you carry."

Section 3 - Common Synonyms

[Examination — standard has: examine, x, look at, read, watch]
Understand the command "inspect" as "examine".
Understand the command "study" as "examine".
Understand the command "view" as "examine".
Understand the command "peruse" as "examine".

[Taking — standard has: take, get, pick up, carry]
Understand the command "grab" as "take".
Understand the command "collect" as "take".
Understand the command "acquire" as "take".
Understand the command "snag" as "take".
Understand the command "fetch" as "take".
Understand the command "obtain" as "take".
Understand the command "steal" as "take".
Understand the command "nab" as "take".
Understand the command "lift" as "take".

[Combat — standard has: attack, hit, fight, punch, kill, smash, break, etc.]
Understand the command "strike" as "attack".
Understand the command "stab" as "attack".
Understand the command "slash" as "attack".
Understand the command "kick" as "attack".

[Looking — standard has: look, l]
Understand the command "peek" as "look".
Understand the command "peer" as "look".
Understand the command "gaze" as "look".

[Going — standard has: go + compass directions]
Understand the command "proceed" as "go".
Understand the command "head" as "go".

[Opening — standard has: open, uncover, unwrap]
Understand the command "pry" as "open".
Understand the command "force" as "open".

[Dropping — standard has: drop, throw, discard]
Understand the command "toss" as "drop".

[Putting — standard has: put, insert]
Understand the command "place" as "put".

[Pushing — standard has: push, move, shift, clear, press]
Understand the command "shove" as "push".
Understand the command "prod" as "push".

[Pulling — standard has: pull, drag]
Understand the command "yank" as "pull".

[Eating — standard has: eat]
Understand the command "consume" as "eat".
Understand the command "devour" as "eat".

[Communication — specific patterns for natural phrasing]
Understand "talk to [someone] about [text]" as asking it about.
Understand "speak to [someone] about [text]" as asking it about.
Understand "chat with [someone] about [text]" as asking it about.
Understand "talk to [someone]" as a mistake ("To talk, try ASK person ABOUT topic or TELL person ABOUT topic.").
Understand "speak to [someone]" as a mistake ("To talk, try ASK person ABOUT topic or TELL person ABOUT topic.").
Understand "chat with [someone]" as a mistake ("To talk, try ASK person ABOUT topic or TELL person ABOUT topic.").

Section 4 - USE Verb Handler

[USE is the most common unrecognized verb in parser IF.]
[Players from point-and-click games instinctively type USE.]

Generically-using is an action applying to one thing.
Understand "use [something]" as generically-using.

Check generically-using:
	say "How do you want to use [the noun]? Try a specific verb: OPEN, PUSH, PULL, TURN, EAT, WEAR, etc." instead.

Generically-using it with is an action applying to two things.
Understand "use [something] on [something]" as generically-using it with.
Understand "use [something] with [something]" as generically-using it with.

Carry out generically-using it with:
	if the second noun is lockable:
		try unlocking the second noun with the noun;
	otherwise:
		say "Try a specific command, such as PUT [the noun] ON [the second noun] or GIVE [the noun] TO [the second noun]."
