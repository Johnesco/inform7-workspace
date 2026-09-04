# Inform 7 Lists Reference

## Overview

A list is a sequence of values (called entries), numbered from 1 upwards. All entries must be the same kind. Lists are mutable -- they can grow, shrink, and be reordered at runtime.

## Declaring Lists

```inform7
let L be a list of numbers;
let names be a list of text;
```

**Pitfall:** `let L be a list;` is invalid -- you must always specify the kind.

Lists initialize as empty (0 entries).

## Constant Lists (Brace Notation)

```inform7
let L be {1, 2, 3, 4};
let fruits be {"apple", "pear", "loganberry"};
let nested be {{1, 2}, {6, 7, 8}};
```

**Rules:**
- Spaces after commas are **mandatory**: `{1, 2, 3}` works, `{1,2,3}` does not
- Spaces around braces are optional
- Only constants are permitted inside braces: `{100, the turn count}` is invalid
- Order matters: `{1, 2, 3}` is different from `{3, 2, 1}` (sequences, not sets)

### Empty list pitfall

```inform7
[INVALID -- type is ambiguous:]
let M be { };

[VALID -- assign to existing typed variable:]
let M be a list of numbers;
now M is { };
```

### Constant lists in tables

```inform7
Table of Requirements
recipe              ingredients
"duck a l'orange"   {the duck, the orange}
"fruit salad"       {the apple, the pear, the banana}
```

## Checking Lists

```inform7
if L is empty: ...
if L is non-empty: ...
say "L has [number of entries in L] entries.";
```

## Accessing Entries by Index

```inform7
let X be entry 1 of L;
let last be entry (number of entries in L) of L;
now entry 2 of L is 42;
```

## Adding Entries

```inform7
[Add single value to end:]
add 5 to L;

[Add list to end:]
add {6, 7, 8} to L;

[Insert at specific position:]
add 99 at entry 2 in L;

[Insert list at specific position:]
add {10, 20} at entry 3 in L;

[Add only if not already present:]
add 5 to L, if absent;
```

## Removing Entries

```inform7
[Remove all instances of a value:]
remove 5 from L;

[Remove multiple values:]
remove {2, 4, 6} from L;

[Remove by index:]
remove entry 3 from L;

[Remove a range:]
remove entries 2 to 4 from L;

[Remove only if present (suppress error if missing):]
remove 5 from L, if present;
```

## Testing Membership

```inform7
if 5 is listed in L: ...
if 5 is not listed in L: ...
```

## Iterating

```inform7
repeat with item running through L:
    say "[item].";
```

**Critical pitfall:** Never modify a list while iterating through it. Removing items during a loop produces unexpected results (skipped entries). Instead, build a separate removal list and apply changes after the loop:

```inform7
let removals be a list of numbers;
repeat with N running through L:
    if N is odd:
        add N to removals;
repeat with N running through removals:
    remove N from L;
```

## Saying Lists

```inform7
[Default formatting -- "2, 3, 5, 7 and 11":]
say "[L]";

[Brace notation -- "{2, 3, 5, 7, 11}":]
say "[L in brace notation]";

[With definite articles -- "the piano and the music stand":]
say "[list of things in brace notation with definite articles]";

[With indefinite articles -- "a piano and a music stand":]
say "[list of things with indefinite articles]";
```

Inform handles commas, conjunctions, and serial comma preferences automatically.

## Creating Lists from Descriptions

```inform7
let L be the list of open containers;
let enemies be the list of hostile people in the Dungeon;
let doors be the list of open doors;
```

## Sorting

```inform7
[Ascending order:]
sort L;

[Descending order:]
sort L in reverse order;

[Random shuffle:]
sort L in random order;

[Sort objects by property (ascending):]
sort L in weight order;

[Sort objects by property (descending):]
sort L in reverse weight order;
```

Property-based sorting works only on lists of objects, where the property is a value property of those objects.

## Reversing

```inform7
reverse L;
```

The old entry 1 becomes the last entry and vice versa.

## Rotating

```inform7
[Forward (right) -- last entry becomes first:]
rotate L;

[Backward (left) -- first entry becomes last:]
rotate L backwards;
```

## Type Safety

Lists enforce homogeneity. You cannot mix kinds (numbers with text, etc.). Attempting to add a value of the wrong kind produces a compiler error.

## Nested Lists

```inform7
let grid be a list of lists of numbers;
add {1, 2, 3} to grid;
add {4, 5, 6} to grid;
```

`list of lists of numbers` is a valid kind. Nested lists print inner lists in brace notation automatically for clarity.

## Lists vs. Tables

Use **lists** when you need a simple, ordered, homogeneous sequence that grows and shrinks dynamically.

Use **tables** when you need to associate different kinds of values together (like rows with multiple typed columns).

## Quick Reference

| Operation | Syntax |
|---|---|
| Declare | `let L be a list of numbers;` |
| Constant | `let L be {1, 2, 3};` |
| Length | `number of entries in L` |
| Access | `entry N of L` |
| Add to end | `add X to L;` |
| Add at position | `add X at entry N in L;` |
| Add if absent | `add X to L, if absent;` |
| Remove value | `remove X from L;` |
| Remove if present | `remove X from L, if present;` |
| Remove by index | `remove entry N from L;` |
| Remove range | `remove entries N to M from L;` |
| Membership test | `if X is listed in L` |
| Iterate | `repeat with item running through L:` |
| Sort ascending | `sort L;` |
| Sort descending | `sort L in reverse order;` |
| Shuffle | `sort L in random order;` |
| Sort by property | `sort L in (property) order;` |
| Reverse | `reverse L;` |
| Rotate forward | `rotate L;` |
| Rotate backward | `rotate L backwards;` |
| Is empty | `if L is empty` |
| From description | `let L be the list of open doors;` |
