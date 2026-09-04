# Glk Styling & Effects Reference

Text styling, colors, images, and window capabilities available in the Emglken Glulxe + AsyncGlk + Parchment browser stack. This is the engine stack required for native Glk sound (see `sound.md`).

## Engine Stack

| Component | Role |
|-----------|------|
| Emglken Glulxe (WASM) | Glulx VM interpreter — the only browser Glulx interpreter with sound |
| AsyncGlk | GlkOte implementation — UI rendering, sound channels, style handling |
| Parchment | Web player shell, Inform 7 template, build system |
| RemGlk-rs | Rust Glk library — bridges interpreter ↔ UI via JSON protocol |

Quixe (erkyrath's JS interpreter) does NOT support sound or Garglk extensions. It does support standard Glk styles, windows, images, and hyperlinks.

## Text Styles

All 11 standard Glk styles are supported:

| Style | ID | Default Look | Inform 7 Syntax |
|-------|----|-------------|-----------------|
| Normal | 0 | Base text | `say "text"` |
| Emphasized | 1 | Italic | `say "[italic type]text[roman type]"` |
| Preformatted | 2 | Monospace | `say "[fixed letter spacing]text[variable letter spacing]"` |
| Header | 3 | Large bold | Via I6 or extensions |
| Subheader | 4 | Bold | Via I6 or extensions |
| Alert | 5 | Bold | Via I6 or extensions |
| Note | 6 | Italic | Via I6 or extensions |
| BlockQuote | 7 | Indented (margin: 0 2em) | Via I6 or extensions |
| Input | 8 | Bold + input color | Player input styling |
| User1 | 9 | Game-defined (empty by default) | Via Glulx Text Effects extension |
| User2 | 10 | Game-defined (empty by default) | Via Glulx Text Effects extension |

### Using Styles from Inform 7

Basic styles:
```inform7
say "[bold type]Important![roman type]";
say "[italic type]whispered[roman type]";
say "[fixed letter spacing]monospace output[variable letter spacing]";
```

User1/User2 via Glulx Text Effects by Emily Short:
```inform7
Include Glulx Text Effects by Emily Short.

say "[first custom style]hidden command[roman type]";
say "[second custom style]another style[roman type]";
```

Header/Subheader/Alert/Note/BlockQuote require I6 inline:
```inform7
To say header style: (- glk_set_style(style_Header); -).
To say subheader style: (- glk_set_style(style_Subheader); -).
To say alert style: (- glk_set_style(style_Alert); -).
To say note style: (- glk_set_style(style_Note); -).
To say blockquote style: (- glk_set_style(style_BlockQuote); -).
```

## Style Hints (Dynamic Style Customization)

Games can customize any style's appearance at runtime via `glk_stylehint_set()`. These must be set **before** opening the window they apply to.

| Hint | What it controls | Value format |
|------|-----------------|-------------|
| `stylehint_TextColor` | Foreground color | 24-bit RGB (`$FF0000` = red) |
| `stylehint_BackColor` | Background color | 24-bit RGB |
| `stylehint_ReverseColor` | Swap fg/bg | 0 = normal, 1 = reversed |
| `stylehint_Weight` | Bold/light | -1 = lighter, 0 = normal, 1 = bold |
| `stylehint_Oblique` | Italic | 0 = normal, 1 = italic |
| `stylehint_Size` | Font size | Relative (-2 to +2 typical), maps to `(1 + value*0.1)em` |
| `stylehint_Proportional` | Font family | 0 = monospace, 1 = proportional (serif) |
| `stylehint_Justification` | Alignment | 0 = left, 1 = justify, 2 = center, 3 = right |
| `stylehint_Indentation` | Left margin | Value in em units |
| `stylehint_ParaIndentation` | First-line indent | Value in em units |

### Setting Style Hints from Inform 7

Requires I6 inline. Example — make User1 red bold text:

```inform7
When play begins (this is the set custom styles rule):
	(- glk_stylehint_set(wintype_AllTypes, style_User1, stylehint_TextColor, $FF0000);
	   glk_stylehint_set(wintype_AllTypes, style_User1, stylehint_Weight, 1); -).
```

Style hints apply per window type:
- `wintype_AllTypes` — all windows
- `wintype_TextBuffer` — buffer windows (main game text)
- `wintype_TextGrid` — grid windows (status bar)

## Colors

- Full 24-bit RGB color support for text and background via style hints
- Garglk extension: `garglk_set_zcolors(fg, bg)` for Z-machine color compatibility
- Special color constants: `zcolor_Default` (-1), `zcolor_Current` (-2)
- Reverse video mode swaps foreground and background

## Fonts

Two font families available in AsyncGlk:

| Type | CSS Variable | Default Fonts |
|------|-------------|--------------|
| Proportional | `--glkote-prop-family` | Georgia, serif |
| Monospace | `--glkote-mono-family` | Lucida Console, DejaVu Sans Mono, monospace |

Toggled per-style via `stylehint_Proportional`. Custom web fonts are not available through the Glk API but can be loaded via page-level CSS overriding these variables.

Font sizes:
- `--glkote-buffer-size: 15px` (buffer window default)
- `--glkote-grid-size: 14px` (grid window default)
- Adjustable per-style via `stylehint_Size`

## Windows

| Type | Purpose | Styling |
|------|---------|---------|
| Buffer window | Scrolling proportional text (main game output) | Full style/color/image support |
| Grid window | Fixed-width character grid (status bar) | Full style/color support |
| Graphics window | Canvas-based drawing | Rects, fill colors, images (no text) |

### Window Splitting

Windows can be split via `glk_window_open()`:
- **Directions**: Above, Below, Left, Right
- **Sizing**: Fixed (pixels) or Proportional (percentage)
- **Rearrangement**: `glk_window_set_arrangement()` to resize after creation

From Inform 7, the status bar is a grid window. Additional windows require I6 or extensions.

## Images

### In Buffer Windows
- `glk_image_draw(win, image_id, alignment, 0)` — inline image
- `glk_image_draw_scaled(win, image_id, alignment, width, height)` — scaled
- Alignment options: InlineUp, InlineDown, InlineCenter, MarginLeft, MarginRight

### In Graphics Windows
- `glk_image_draw(win, image_id, x, y)` — draw at position
- `glk_image_draw_scaled(win, image_id, x, y, width, height)` — scaled
- `glk_window_fill_rect(win, colour, x, y, w, h)` — colored rectangle
- `glk_window_erase_rect(win, x, y, w, h)` — clear area
- `glk_window_set_background_color(win, colour)` — canvas background

Images loaded from Blorb resources (embedded in .gblorb via `Picture` chunks).

### From Inform 7
```inform7
Figure of Cover is the file "cover.png".
display Figure of Cover;
```

## Hyperlinks

- `glk_set_hyperlink(value)` — make subsequent text clickable with integer value
- `glk_set_hyperlink(0)` — end hyperlink
- `glk_request_hyperlink_event(win)` — listen for clicks
- Returns `evtype_Hyperlink` event with the value when clicked
- Rendered as `<a>` tags in the browser

From Inform 7 (requires I6 inline or extension):
```inform7
To set hyperlink (N - number): (- glk_set_hyperlink({N}); -).
To clear hyperlink: (- glk_set_hyperlink(0); -).
```

## Themes

Two built-in themes (light/dark) with CSS custom properties:

| Variable | Purpose |
|----------|---------|
| `--glkote-buffer-bg` | Buffer window background |
| `--glkote-buffer-fg` | Buffer window text color |
| `--glkote-buffer-reverse-bg` | Reverse video background |
| `--glkote-grid-bg` | Grid window background |
| `--glkote-grid-fg` | Grid window text color |
| `--glkote-grid-reverse-bg` | Grid reverse background |
| `--glkote-input-fg` | Player input text color |

Override in the page CSS to customize the look.

## CSS Class Names

AsyncGlk generates CSS classes for each style that can be targeted from page-level CSS:

- `.Style_normal`, `.Style_emphasized`, `.Style_preformatted`
- `.Style_header`, `.Style_subheader`, `.Style_alert`, `.Style_note`
- `.Style_blockquote`, `.Style_input`
- `.Style_user1`, `.Style_user2`

Paragraph-level: `.Style_normal_par`, `.Style_user1_par`, etc.

**Important**: The `.Style_input` / `.Input` class is engine-dependent. In Emglken WASM mode, user input is rendered as regular text nodes without the `.Input` class. Code that queries `.BufferWindow .Input` to detect what the player typed will find nothing. Instead, use a MutationObserver to track added node text — the user's command appears as a regular element node immediately before the game's response.

This allows effects beyond the Glk API (shadows, animations, custom fonts, gradients) by adding CSS to the play.html page:

```css
.Style_user1 { display: none; }  /* hide SFX commands */
.Style_header { text-shadow: 1px 1px 2px rgba(0,0,0,0.3); }
.Style_alert { color: #cc0000; animation: pulse 1s infinite; }
```

## What's NOT Available via Glk API

- Custom web fonts (only serif/monospace toggle — override with page CSS)
- Text shadows, gradients, animations (use page CSS targeting style classes)
- Multiple font faces per style (just serif or monospace)
- Advanced CSS features like transforms or filters
- Video or embedded media (only images and sound)

## Related Documentation

- `sound.md` — Sound system architecture and decision record
- `build-pipeline.md` — Compilation and deployment pipeline
- `text-formatting.md` — Inform 7 text substitutions
- `C:\code\parchment\CLAUDE.md` — Parchment fork architecture and known gotchas

## Source Files

| File | What it defines |
|------|----------------|
| `asyncglk/src/glkote/web/styles.css` | Default style appearances |
| `asyncglk/src/glkapi/lib_constants.ts` | Style IDs, hint IDs, CSS property mapping |
| `asyncglk/src/glkapi/glkapi.ts:1030-1102` | `glk_stylehint_set/clear` implementation |
| `asyncglk/src/glkote/web/windows.ts` | Dynamic CSS generation per window |
| `asyncglk/src/common/protocol.ts` | Text run and style protocol types |
