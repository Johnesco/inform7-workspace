# Inform 7 Text Formatting Reference

All formatting in Inform 7 is done via substitutions inside `say` statements using square brackets.

## Paragraph and Line Control

| Substitution | Effect |
|---|---|
| `[paragraph break]` | Blank line between paragraphs (like pressing Enter twice) |
| `[line break]` | Newline without blank line (like pressing Enter once) |
| `[run paragraph on]` | Suppress the paragraph break that normally follows |
| `[conditional paragraph break]` | Paragraph break only if text has been printed |

## Text Style

| Substitution | Effect |
|---|---|
| `[bold type]` | Start bold text |
| `[italic type]` | Start italic text |
| `[roman type]` | Return to normal (end bold or italic) |
| `[fixed letter spacing]` | Switch to monospace/typewriter font |
| `[variable letter spacing]` | Return to proportional font |

**Important:** Bold/italic/fixed are toggles. Always close them with `[roman type]` or `[variable letter spacing]`.

Example:
```inform7
say "[bold type]WARNING[roman type]: Do not touch the [italic type]red[roman type] wire."
say "[fixed letter spacing]  code_here();[variable letter spacing]"
```

## Special Characters

| Substitution | Character |
|---|---|
| `[apostrophe]` | ' (single quote / apostrophe) |
| `[quotation mark]` | " (double quote) |
| `[bracket]` | [ (open square bracket) |
| `[close bracket]` | ] (close square bracket) |

**Critical:** You MUST use these substitutions inside `say` strings. Literal `'` may work in some contexts but `[apostrophe]` is always safe. Literal `"` will NEVER work inside a string — always use `[quotation mark]`.

## Printing Values

| Substitution | Effect |
|---|---|
| `[the noun]` | Print the noun with article ("the apple") |
| `[The noun]` | Print with capitalized article ("The apple") |
| `[a noun]` | Print with indefinite article ("an apple") |
| `[noun]` | Print without article ("apple") |
| `[number of things carried by the player]` | Print a computed number |
| `[list of things in the Kitchen]` | Print a formatted list |
| `[time of day]` | Print current game time |

## Custom Text Substitutions (Say Phrases)

Define reusable text blocks:
```inform7
To say danger-warning:
    say "[bold type]DANGER[roman type][line break]";
    say "Proceed with extreme caution."
```

Invoke with:
```inform7
say "[danger-warning]"
```

**Naming:** Use hyphens, not spaces, in say-phrase names: `danger-warning` not `danger warning`.

## If/Otherwise in Text

```inform7
say "[if the player carries the key]You have the key.[otherwise]You need to find the key.[end if]"
```

Also supports `[one of]...[or]...[at random]` for variety:
```inform7
say "[one of]You shiver.[or]A chill runs down your spine.[or]The cold bites.[at random]"
```

## Long Text Best Practices

For passages longer than a few sentences, break into multiple `say` calls:
```inform7
To say my-story:
    say "First paragraph of text here.[paragraph break]";
    say "Second paragraph continues.[paragraph break]";
    say "Final paragraph wraps up."
```

This is more maintainable than one enormous string and avoids potential compiler limits.

## Common Mistakes

1. **Forgetting `[roman type]`** after `[bold type]` — all subsequent text stays bold
2. **Using literal quotes** inside strings — always use `[quotation mark]`
3. **Missing `[paragraph break]`** — text runs together without explicit breaks
4. **Using spaces in say-phrase names** — use hyphens: `my-phrase` not `my phrase`
5. **Forgetting semicolons** — each `say` statement inside a phrase needs a semicolon except the last (which uses a period)
