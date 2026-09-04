# Inform 7 Extensions Reference

## Overview

Extensions expand Inform 7's core simulation model. There is no "official" solution for any domain -- multiple competing extensions can address the same need (money, clothing, liquids, etc.).

## Including Extensions

Every source file automatically includes the Standard Rules by Graham Nelson. To include additional extensions:

```inform7
Include Locksmith by Emily Short.
```

The Include statement replaces itself with the full text of the referenced extension. Circular dependencies are handled gracefully -- if A includes B and B includes A, Inform processes both without infinite recursion; once an extension is included, subsequent Include statements for it are silently ignored.

### Version Requirements

```inform7
Include version 2.4 of Locksmith by Emily Short.
```

This accepts version 2.4 or any later version within major version 2 (e.g., 2.5, 2.9.1). Version 3.0 would be rejected as incompatible. An unversioned Include accepts any version.

### Extension Resolution Order

When searching for an extension, Inform checks these locations in priority order:
1. **Project-specific**: `.materials/Extensions/` folder within the project
2. **Installed**: User's system-wide extension folder
3. **Built-in**: ~20 extensions bundled with the Inform application

This hierarchy allows overriding any extension (even the Standard Rules) for testing or customization without affecting other projects.

## The Standard Rules

The Standard Rules extension is always included automatically. It provides:
- Fundamental kind declarations (thing, container, supporter, person, etc.)
- Core phrase definitions
- The action system
- Grammar rules for standard commands
- Room description rules

## Authoring Extensions

### File Structure

Extensions are UTF-8 plain text files. Two special sentences are required:

```inform7
Locksmith by Emily Short begins here.

"Automatic key-handling for doors and containers."

"based on original I6 code by David Kinder"

[... extension source code ...]

Locksmith ends here.
```

**Line 1 (required):** `[Title] by [Author] begins here.` -- must be the sole content of the first line, no comments allowed. Use `begin` instead of `begins` for plural titles.

**Rubric (optional):** A double-quoted description immediately after the opening sentence. Should not exceed 500 characters.

**Credits (optional):** A second double-quoted text providing attribution for prior contributors. Styled as a lowercase phrase without terminal punctuation.

**Last line (required):** `[Title] ends here.`

### Extension Content

Between the markers, extensions contain standard Inform source material: rooms, objects, kinds, rules, grammar definitions, phrases -- in any order. When writing extensions for reuse, **name every rule** so users can manipulate them from their own source:

```inform7
The automatic key-fitting rule is listed before the can't unlock without the correct key rule.
```

### Naming Rules

**Extension titles:**
- Use Sentence Capitalisation (upper case first letter of each word)
- Cannot contain "by", "version", or punctuation
- May contain "and"
- Maximum 50 characters

**Author names:**
- Use Sentence Capitalisation
- Cannot start with "The"
- Cannot contain "by", "and", "version", or punctuation
- Maximum 50 characters
- ISO Latin-1 characters allowed (e.g., Francoise Gauss)

### Version Numbering

Extensions use semantic versioning with 1-3 numbers separated by dots:

```inform7
Version 2.1.3 of Locksmith by Emily Short begins here.
```

| Part | When to increment | Resets |
|---|---|---|
| **Major (X)** | Breaking changes: removed phrases, renamed kinds | Y and Z to 0 |
| **Minor (Y)** | New features that don't break existing usage | Z to 0 |
| **Patch (Z)** | Bug fixes, docs, efficiency improvements only | Nothing |

Legacy format `N/YYMMDD` (e.g., `6/040426`) converts to `N.0.YYMMDD`.

### Extension Credits at Runtime

The VERSION command lists all included extensions. Authors can suppress their credit:

```inform7
Use authorial modesty.
```

Text substitutions for credits:
- `[the list of extension credits]` -- respects modesty settings
- `[the complete list of extension credits]` -- shows all extensions regardless

## Public vs. Private Extensions

**Private:** For personal use across multiple projects or sharing with associates.

**Public:** Archived on the Inform website. Must follow style guidelines. Authors donate work under Creative Commons (broadest form) but retain copyright and attribution. May be used in commercial works.

If an extension is not marked public, check with the author before incorporating it in published work.
