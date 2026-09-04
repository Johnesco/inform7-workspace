/**
 * MoodEngine v2.0 — Declarative mood/atmosphere system for Parchment games.
 *
 * Features:
 *   - Typography presets: font, size, spacing, width
 *   - Color presets and named vibes (bundled presets)
 *   - Room-based palette transitions (Houdini @property + CSS custom properties)
 *   - Declarative triggers: text match / room change -> effects
 *   - Built-in effects: shake, flash, particles, ripple, glitch, vignette, flood, drain, pulse
 *   - Game states with palette overrides + persistent effects (distortion, chromatic, static)
 *   - Intro presets: monitor, crt (or custom config)
 *   - IF Hub integration (platform theme postMessage)
 *   - Full CSS override escape hatch — author CSS always wins
 *
 * Backwards compatible with v1 configs.
 *
 * Usage:
 *   <script src="lib/parchment/mood-engine.js"></script>
 *   <script>
 *     MoodEngine.init({
 *       vibe: 'clinical',
 *       palettes:    { zone: { bufferBg, bufferFg, gridBg, gridFg, accent, uiBg, border } },
 *       roomZones:   { 'Room Name': 'zone' },
 *       triggers:    [ { on: 'text', effect: 'shake' } ],
 *       states:      { name: { palettes: {...}, effects: {...} } },
 *       intro:       'monitor'
 *     });
 *   </script>
 */
(function() {
  'use strict';

  // ══════════════════════════════════════════════════════════════
  //  PRESET DATA
  // ══════════════════════════════════════════════════════════════

  var FONTS = {
    serif: {
      prop: '"Iowan Old Style", Palatino, Georgia, "Times New Roman", serif',
      mono: '"SF Mono", "Fira Code", "Cascadia Code", Consolas, "Courier New", monospace'
    },
    sans: {
      prop: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
      mono: '"SF Mono", "Fira Code", Consolas, monospace'
    },
    mono: {
      prop: '"SF Mono", "Fira Code", "Cascadia Code", Consolas, "Courier New", monospace',
      mono: '"SF Mono", "Fira Code", "Cascadia Code", Consolas, "Courier New", monospace'
    },
    typewriter: {
      prop: '"Courier New", Courier, "Lucida Console", monospace',
      mono: '"Courier New", Courier, monospace'
    },
    gothic: {
      prop: '"Palatino Linotype", "Book Antiqua", Palatino, serif',
      mono: '"SF Mono", "Fira Code", Consolas, monospace'
    }
  };

  var SIZES = {
    small:       { buffer: '14px', lineHeight: '1.5', grid: '12px' },
    default:     { buffer: '16px', lineHeight: '1.6', grid: '14px' },
    comfortable: { buffer: '17px', lineHeight: '1.7', grid: '14px' },
    large:       { buffer: '19px', lineHeight: '1.8', grid: '16px' }
  };

  var SPACINGS = {
    tight:   '10px 20px',
    default: '20px 40px',
    relaxed: '28px 50px',
    airy:    '40px 60px'
  };

  var WIDTHS = {
    narrow:   '32em',
    readable: '38em',
    wide:     '52em',
    full:     'none'
  };

  var COLORS = {
    dark: {
      bufferBg:'#111111', bufferFg:'#c8c4b8', gridBg:'#1a1814', gridFg:'#908870',
      accent:'#d0b870', uiBg:'#111111', border:'#2a2418',
      scrollbar:'#3a3020', scrollbarHover:'#5a4a30',
      headerFg:'#c8c4b8', alertFg:'#cc8844', noteFg:'#808898', bodyBg:'#0a0a0a'
    },
    parchment: {
      bufferBg:'#1a1408', bufferFg:'#e8d8b0', gridBg:'#2a1a08', gridFg:'#c09040',
      accent:'#f0c060', uiBg:'#1a1408', border:'#3a2810',
      scrollbar:'#3a2810', scrollbarHover:'#5a4020',
      headerFg:'#e8d8b0', alertFg:'#cc8844', noteFg:'#a09060', bodyBg:'#100a04'
    },
    sepia: {
      bufferBg:'#181210', bufferFg:'#d0c0a0', gridBg:'#241c14', gridFg:'#a09070',
      accent:'#c0a060', uiBg:'#181210', border:'#302418',
      scrollbar:'#302418', scrollbarHover:'#4a3828',
      headerFg:'#d0c0a0', alertFg:'#cc8844', noteFg:'#808898', bodyBg:'#0e0a08'
    },
    terminal: {
      bufferBg:'#0a0a0a', bufferFg:'#33ff00', gridBg:'#0a0a0a', gridFg:'#22aa00',
      accent:'#33ff00', uiBg:'#0a0a0a', border:'#1a3a00',
      scrollbar:'#1a3a00', scrollbarHover:'#2a5a00',
      headerFg:'#66ff33', alertFg:'#ffaa00', noteFg:'#22aa00', bodyBg:'#000000'
    },
    ice: {
      bufferBg:'#0a0c14', bufferFg:'#b0c0d8', gridBg:'#0e1018', gridFg:'#6080a0',
      accent:'#80b0e0', uiBg:'#0a0c14', border:'#142030',
      scrollbar:'#1a2a40', scrollbarHover:'#2a4060',
      headerFg:'#c0d0e8', alertFg:'#cc8844', noteFg:'#6080a0', bodyBg:'#060810'
    },
    clinical: {
      bufferBg:'#0e0e12', bufferFg:'#c0beb8', gridBg:'#161420', gridFg:'#808090',
      accent:'#9098b0', uiBg:'#0e0e12', border:'#1e1e28',
      scrollbar:'#282830', scrollbarHover:'#404050',
      headerFg:'#c0c8d0', alertFg:'#b08870', noteFg:'#808898', bodyBg:'#080808'
    }
  };

  var VIBES = {
    cozy:     { font:'serif',    size:'comfortable', spacing:'relaxed', width:'readable', color:'parchment' },
    stark:    { font:'sans',     size:'default',     spacing:'tight',   width:'wide',     color:'dark' },
    retro:    { font:'mono',     size:'default',     spacing:'default', width:'full',     color:'terminal' },
    gothic:   { font:'gothic',   size:'large',       spacing:'relaxed', width:'readable', color:'sepia' },
    clinical: { font:'mono',     size:'default',     spacing:'default', width:'readable', color:'clinical' }
  };

  // ══════════════════════════════════════════════════════════════
  //  INTERNAL STATE
  // ══════════════════════════════════════════════════════════════

  var _palettes = {};
  var _roomZones = {};
  var _fallbackZone = null;
  var _currentRoom = null;
  var _currentZone = null;
  var _onRoomChangeCb = null;
  var _onBufferTextCb = null;
  var _resolvePaletteCb = null;
  var _introConfig = null;
  var _lastBufferText = '';
  var _triggers = [];
  var _states = {};
  var _activeStates = {};
  var _transitionSec = 1.2;
  var _managed = false;
  var _baseStyleEl = null;
  var _stateStyleEls = {};

  // ══════════════════════════════════════════════════════════════
  //  PRESET RESOLUTION
  // ══════════════════════════════════════════════════════════════

  function resolvePresets(cfg) {
    var vibe = cfg.vibe && VIBES[cfg.vibe] ? VIBES[cfg.vibe] : {};
    return {
      font:    FONTS[cfg.font || vibe.font || 'serif'] || FONTS.serif,
      size:    SIZES[cfg.size || vibe.size || 'default'] || SIZES['default'],
      spacing: SPACINGS[cfg.spacing || vibe.spacing || 'default'] || SPACINGS['default'],
      width:   WIDTHS[cfg.width || vibe.width || 'full'] || WIDTHS.full,
      color:   resolveColor(cfg, vibe)
    };
  }

  function resolveColor(cfg, vibe) {
    if (cfg.color && typeof cfg.color === 'object') return cfg.color;
    var name = (typeof cfg.color === 'string' && cfg.color) || (vibe && vibe.color) || 'dark';
    return COLORS[name] || COLORS.dark;
  }

  // ══════════════════════════════════════════════════════════════
  //  CSS GENERATION — BASE
  // ══════════════════════════════════════════════════════════════

  function generateBaseCSS(presets) {
    var c = presets.color;
    var t = _transitionSec + 's ease-in-out';
    var L = [];

    // @property declarations for smooth color transitions
    var props = ['buffer-bg','buffer-fg','grid-bg','grid-fg','accent','ui-bg','border'];
    var defaults = [c.bufferBg, c.bufferFg, c.gridBg, c.gridFg, c.accent, c.uiBg, c.border];
    for (var i = 0; i < props.length; i++) {
      L.push('@property --mood-' + props[i] + ' { syntax: "<color>"; inherits: true; initial-value: ' + defaults[i] + '; }');
    }

    // :root — mood + GlkOte/AsyncGlk variables
    L.push(':root {');
    L.push('  --mood-buffer-bg:' + c.bufferBg + '; --mood-buffer-fg:' + c.bufferFg + ';');
    L.push('  --mood-grid-bg:' + c.gridBg + '; --mood-grid-fg:' + c.gridFg + ';');
    L.push('  --mood-accent:' + c.accent + '; --mood-ui-bg:' + c.uiBg + '; --mood-border:' + c.border + ';');
    L.push('  transition: --mood-buffer-bg ' + t + ', --mood-buffer-fg ' + t + ', --mood-grid-bg ' + t + ', --mood-grid-fg ' + t + ', --mood-accent ' + t + ', --mood-ui-bg ' + t + ', --mood-border ' + t + ';');
    L.push('  --glkote-buffer-bg:' + c.bufferBg + '; --glkote-buffer-fg:' + c.bufferFg + ';');
    L.push('  --glkote-buffer-reverse-bg:' + c.bufferFg + '; --glkote-buffer-reverse-fg:' + c.bufferBg + ';');
    L.push('  --glkote-buffer-size:' + presets.size.buffer + '; --glkote-buffer-line-height:' + presets.size.lineHeight + ';');
    L.push('  --glkote-grid-bg:' + c.gridBg + '; --glkote-grid-fg:' + c.gridFg + ';');
    L.push('  --glkote-grid-reverse-bg:' + c.gridFg + '; --glkote-grid-reverse-fg:' + c.gridBg + ';');
    L.push('  --glkote-grid-size:' + presets.size.grid + '; --glkote-input-fg:' + c.accent + ';');
    L.push('  --glkote-error-border:#882020; --glkote-warning-border:#3333aa;');
    L.push('  --glkote-prop-family:' + presets.font.prop + ';');
    L.push('  --glkote-mono-family:' + presets.font.mono + ';');
    L.push('  --glkote-grid-mono-family:var(--glkote-mono-family);');
    L.push('  --asyncglk-ui-bg:' + c.uiBg + '; --asyncglk-ui-border:' + c.border + ';');
    L.push('  --asyncglk-ui-fg:' + c.bufferFg + '; --asyncglk-ui-selected:' + c.uiBg + '; --asyncglk-ui-textbox:' + c.bufferBg + ';');
    L.push('}');

    // Structural CSS
    L.push('html, body { height:100%; margin:0; padding:0; background:' + (c.bodyBg || '#0a0a0a') + '; overflow:hidden; }');
    L.push('div#gameport { position:absolute; inset:0; background:var(--mood-ui-bg); transition:background-color ' + t + '; }');
    L.push('#gameport::before, #gameport::after { content:""; position:fixed; inset:0; pointer-events:none; z-index:10000; opacity:0; transition:opacity 0.3s ease; }');
    L.push('.WindowFrame { background:var(--mood-ui-bg) !important; }');
    L.push('.WindowFrame:has(.GridWindow) { background:var(--mood-buffer-fg) !important; transition:background-color ' + t + '; }');
    L.push('.GridWindow, .GridWindow * { background-color:var(--mood-buffer-fg) !important; color:#0a0a0a !important; font-weight:bold; transition:background-color ' + t + ', color ' + t + '; }');
    L.push('.GridWindow { padding:6px 12px; }');
    L.push('.BufferWindow { background-color:var(--mood-buffer-bg) !important; color:var(--mood-buffer-fg) !important; transition:background-color ' + t + ', color ' + t + '; }');
    L.push('.BufferWindowInner { padding:' + presets.spacing + '; text-rendering:optimizeLegibility; }');
    if (presets.width !== 'none') {
      L.push('.BufferWindowInner { max-width:' + presets.width + '; margin-left:auto; margin-right:auto; }');
    }
    L.push('.Input { font-weight:bold; color:var(--mood-accent); caret-color:var(--mood-accent); caret-shape:underscore; transition:color ' + t + ', caret-color ' + t + '; }');

    // Text fade-in
    L.push('@keyframes mood-buffer-fade { from { opacity:0; transform:translateY(4px); } to { opacity:1; transform:translateY(0); } }');
    L.push('.BufferLine { animation:mood-buffer-fade 0.3s ease-out; }');

    // Style classes
    L.push('.Style_header { color:' + (c.headerFg || 'var(--mood-accent)') + '; text-shadow:0 0 8px ' + (c.headerFg || c.accent) + '26; transition:color ' + t + '; }');
    L.push('.Style_alert { color:' + (c.alertFg || '#cc8844') + '; text-shadow:0 0 6px ' + (c.alertFg || '#b08870') + '1f; }');
    L.push('.Style_note { color:' + (c.noteFg || '#808898') + '; }');
    L.push('.Style_user1 { display:none; }');

    // Scrollbar
    L.push('.BufferWindow { scrollbar-width:thin; scrollbar-color:' + (c.scrollbar || '#282830') + ' transparent; }');
    L.push('.BufferWindow::-webkit-scrollbar { width:6px; }');
    L.push('.BufferWindow::-webkit-scrollbar-track { background:transparent; }');
    L.push('.BufferWindow::-webkit-scrollbar-thumb { background:' + (c.scrollbar || '#282830') + '; border-radius:3px; }');
    L.push('.BufferWindow::-webkit-scrollbar-thumb:hover { background:' + (c.scrollbarHover || '#404050') + '; }');

    // Loading pane
    L.push('#loadingpane { position:absolute; width:100%; text-align:center; top:35%; color:#607080; font-size:1.2em; font-family:var(--glkote-prop-family); }');
    L.push('@keyframes mood-loading-pulse { 0%,100% { opacity:0.4; } 50% { opacity:1; } }');
    L.push('#loadingpane em { animation:mood-loading-pulse 1.5s ease-in-out infinite; }');

    // Platform theme suppression
    L.push('body.platform-theme-active div#gameport { transition:none !important; }');
    L.push('body.platform-theme-active .BufferWindow { transition:none !important; }');
    L.push('body.platform-theme-active .BufferLine { animation:none !important; }');
    L.push('body.platform-theme-active .Input { color:inherit !important; caret-color:inherit !important; transition:none !important; }');

    return L.join('\n');
  }

  // ══════════════════════════════════════════════════════════════
  //  CSS GENERATION — EFFECTS
  // ══════════════════════════════════════════════════════════════

  function generateEffectCSS() {
    var L = [];

    // Shake — three intensity levels
    L.push('@keyframes mood-fx-shake-light {');
    L.push('  0%,100% { transform:translate(0,0); }');
    L.push('  10% { transform:translate(-2px,1px); } 20% { transform:translate(3px,-2px); }');
    L.push('  30% { transform:translate(-2px,2px); } 40% { transform:translate(2px,-1px); }');
    L.push('  50% { transform:translate(-1px,1px); } 60% { transform:translate(1px,-1px); }');
    L.push('  70% { transform:translate(-1px,1px); } 80% { transform:translate(1px,0); }');
    L.push('}');
    L.push('@keyframes mood-fx-shake-medium {');
    L.push('  0%,100% { transform:translate(0,0); }');
    L.push('  10% { transform:translate(-4px,2px); } 20% { transform:translate(5px,-3px); }');
    L.push('  30% { transform:translate(-3px,4px); } 40% { transform:translate(4px,-2px); }');
    L.push('  50% { transform:translate(-2px,3px); } 60% { transform:translate(3px,-1px); }');
    L.push('  70% { transform:translate(-1px,2px); } 80% { transform:translate(2px,-1px); }');
    L.push('}');
    L.push('@keyframes mood-fx-shake-heavy {');
    L.push('  0%,100% { transform:translate(0,0); }');
    L.push('  10% { transform:translate(-6px,3px); } 20% { transform:translate(7px,-5px); }');
    L.push('  30% { transform:translate(-5px,6px); } 40% { transform:translate(6px,-4px); }');
    L.push('  50% { transform:translate(-4px,5px); } 60% { transform:translate(5px,-3px); }');
    L.push('  70% { transform:translate(-3px,4px); } 80% { transform:translate(3px,-2px); }');
    L.push('}');
    L.push('body.mood-fx-shake-light #gameport { animation:mood-fx-shake-light 0.5s ease-out; }');
    L.push('body.mood-fx-shake-medium #gameport { animation:mood-fx-shake-medium 0.6s ease-out; }');
    L.push('body.mood-fx-shake-heavy #gameport { animation:mood-fx-shake-heavy 0.5s ease-out; }');

    // Ripple — hue-rotate cycle
    L.push('@keyframes mood-fx-ripple {');
    L.push('  0%   { filter:hue-rotate(0deg) saturate(1); }');
    L.push('  20%  { filter:hue-rotate(30deg) saturate(1.4); }');
    L.push('  40%  { filter:hue-rotate(-20deg) saturate(1.2); }');
    L.push('  60%  { filter:hue-rotate(15deg) saturate(1.1); }');
    L.push('  80%  { filter:hue-rotate(-5deg) saturate(1.05); }');
    L.push('  100% { filter:hue-rotate(0deg) saturate(1); }');
    L.push('}');

    // Glitch — hue-rotate + invert step flicker
    L.push('@keyframes mood-fx-glitch {');
    L.push('  0% { filter:none; } 10% { filter:hue-rotate(90deg) invert(0.1); }');
    L.push('  12% { filter:none; } 30% { filter:hue-rotate(-60deg) invert(0.15); }');
    L.push('  33% { filter:none; } 50% { filter:hue-rotate(120deg) saturate(2); }');
    L.push('  53% { filter:none; } 70% { filter:invert(0.2) hue-rotate(-90deg); }');
    L.push('  73% { filter:none; } 85% { filter:hue-rotate(45deg) invert(0.08); }');
    L.push('  88% { filter:none; } 100% { filter:none; }');
    L.push('}');

    // Particle keyframes
    L.push('@keyframes mood-fx-particle-burst {');
    L.push('  0% { opacity:1; transform:translate(0,0) rotate(0deg); }');
    L.push('  100% { opacity:0; transform:translate(var(--px),var(--py)) rotate(var(--pr)); }');
    L.push('}');
    L.push('@keyframes mood-fx-particle-fall {');
    L.push('  0% { opacity:var(--po,0.6); transform:translateY(0) translateX(0); }');
    L.push('  100% { opacity:0; transform:translateY(var(--py,100vh)) translateX(var(--px,0)); }');
    L.push('}');

    // Flash overlay
    L.push('@keyframes mood-fx-flash { 0% { opacity:0; } 15% { opacity:0.6; } 40% { opacity:0.3; } 100% { opacity:0; } }');

    // Vignette overlay
    L.push('@keyframes mood-fx-vignette { 0% { opacity:0; } 30% { opacity:0.5; } 60% { opacity:0.3; } 100% { opacity:0; } }');

    // Flood overlay
    L.push('@keyframes mood-fx-flood {');
    L.push('  0% { transform:translateY(100%); opacity:0.3; }');
    L.push('  60% { transform:translateY(20%); opacity:0.4; }');
    L.push('  100% { transform:translateY(0%); opacity:0.5; }');
    L.push('}');

    // Drain overlay
    L.push('@keyframes mood-fx-drain { 0% { opacity:0.25; transform:translateY(0); } 100% { opacity:0; transform:translateY(100%); } }');

    // Pulse
    L.push('@keyframes mood-fx-pulse { 0%,100% { opacity:0; } 50% { opacity:0.5; } }');

    // Fade
    L.push('@keyframes mood-fx-fade-in { from { opacity:1; } to { opacity:0; } }');
    L.push('@keyframes mood-fx-fade-out { from { opacity:0; } to { opacity:1; } }');

    // Scanline drift (for intro modes)
    L.push('@keyframes mood-scanline-drift { 0% { transform:translateY(-100%); } 100% { transform:translateY(100vh); } }');
    L.push('.mood-scanbar { display:none; position:fixed; left:0; right:0; height:3px; pointer-events:none; z-index:10002; animation:mood-scanline-drift 4s linear infinite; }');

    // ── Tier 1 effects ──

    // Invert — filter invert + hue-rotate flicker
    L.push('@keyframes mood-fx-invert {');
    L.push('  0%,100% { filter:none; }');
    L.push('  6%  { filter:invert(1) hue-rotate(180deg) brightness(1.5); }');
    L.push('  12% { filter:none; }');
    L.push('  18% { filter:invert(0.3) hue-rotate(60deg); }');
    L.push('  24% { filter:none; }');
    L.push('}');

    // TextGlow — golden/colored glow on last BufferLine
    L.push('@keyframes mood-fx-textglow {');
    L.push('  0%   { color:inherit; text-shadow:none; }');
    L.push('  15%  { color:var(--mood-fx-glow-color, #ffd700); text-shadow:0 0 12px var(--mood-fx-glow-color, rgba(255,215,0,0.6)), 0 0 30px var(--mood-fx-glow-outer, rgba(255,165,0,0.3)), 0 0 60px var(--mood-fx-glow-far, rgba(255,100,0,0.15)); }');
    L.push('  50%  { color:var(--mood-fx-glow-mid, #ffe870); text-shadow:0 0 8px var(--mood-fx-glow-color, rgba(255,215,0,0.3)); }');
    L.push('  100% { color:inherit; text-shadow:none; }');
    L.push('}');

    // Shockwave ring — expanding circle
    L.push('@keyframes mood-fx-shockwave {');
    L.push('  0%   { transform:translate(-50%,-50%) scale(0); opacity:0.8; border-width:3px; }');
    L.push('  100% { transform:translate(-50%,-50%) scale(5); opacity:0; border-width:0.5px; }');
    L.push('}');

    // ── Tier 2 effects ──

    // Sway — gentle rotation + translation on text area
    L.push('@keyframes mood-fx-sway {');
    L.push('  0%,100% { transform:rotate(-0.5deg) translateX(-3px); }');
    L.push('  30%     { transform:rotate(0.3deg) translateX(2px); }');
    L.push('  60%     { transform:rotate(0.5deg) translateX(4px); }');
    L.push('  80%     { transform:rotate(-0.2deg) translateX(-1px); }');
    L.push('}');

    // Glow — pulsing box-shadow on BufferWindow
    L.push('@keyframes mood-fx-glow {');
    L.push('  0%,100% { box-shadow:inset 0 0 120px 20px var(--mood-fx-glow-dim, rgba(30,120,20,0.04)), inset 0 80px 80px -30px var(--mood-fx-glow-dim2, rgba(60,160,30,0.06)); }');
    L.push('  50%     { box-shadow:inset 0 0 120px 20px var(--mood-fx-glow-bright, rgba(50,150,30,0.10)), inset 0 80px 80px -30px var(--mood-fx-glow-bright2, rgba(80,200,40,0.14)); }');
    L.push('}');

    // Leaf fall — 3 distinct drift paths for ambient leaves
    L.push('@keyframes mood-fx-leaf1 {');
    L.push('  0%   { transform:translateY(-20px) translateX(0) rotate(0deg); opacity:0; }');
    L.push('  8%   { opacity:0.7; }');
    L.push('  25%  { transform:translateY(25vh) translateX(40px) rotate(190deg); }');
    L.push('  50%  { transform:translateY(50vh) translateX(-25px) rotate(380deg); }');
    L.push('  75%  { transform:translateY(75vh) translateX(55px) rotate(560deg); }');
    L.push('  92%  { opacity:0.3; }');
    L.push('  100% { transform:translateY(105vh) translateX(15px) rotate(720deg); opacity:0; }');
    L.push('}');
    L.push('@keyframes mood-fx-leaf2 {');
    L.push('  0%   { transform:translateY(-20px) translateX(0) rotate(0deg); opacity:0; }');
    L.push('  8%   { opacity:0.6; }');
    L.push('  30%  { transform:translateY(28vh) translateX(-35px) rotate(170deg); }');
    L.push('  55%  { transform:translateY(52vh) translateX(30px) rotate(350deg); }');
    L.push('  80%  { transform:translateY(80vh) translateX(-40px) rotate(530deg); }');
    L.push('  92%  { opacity:0.25; }');
    L.push('  100% { transform:translateY(105vh) translateX(-10px) rotate(680deg); opacity:0; }');
    L.push('}');
    L.push('@keyframes mood-fx-leaf3 {');
    L.push('  0%   { transform:translateY(-20px) translateX(0) rotate(0deg); opacity:0; }');
    L.push('  10%  { opacity:0.5; }');
    L.push('  20%  { transform:translateY(18vh) translateX(25px) rotate(120deg); }');
    L.push('  50%  { transform:translateY(48vh) translateX(-35px) rotate(310deg); }');
    L.push('  75%  { transform:translateY(74vh) translateX(45px) rotate(500deg); }');
    L.push('  90%  { opacity:0.2; }');
    L.push('  100% { transform:translateY(105vh) translateX(20px) rotate(660deg); opacity:0; }');
    L.push('}');

    // Snow drift
    L.push('@keyframes mood-fx-snowfall {');
    L.push('  0%   { transform:translateY(-10px) translateX(0); opacity:0; }');
    L.push('  10%  { opacity:0.5; }');
    L.push('  50%  { transform:translateY(50vh) translateX(var(--px, 20px)); }');
    L.push('  90%  { opacity:0.2; }');
    L.push('  100% { transform:translateY(105vh) translateX(var(--px2, -10px)); opacity:0; }');
    L.push('}');

    // Rain
    L.push('@keyframes mood-fx-rainfall {');
    L.push('  0%   { transform:translateY(-10px); opacity:0; }');
    L.push('  5%   { opacity:0.6; }');
    L.push('  95%  { opacity:0.4; }');
    L.push('  100% { transform:translateY(105vh); opacity:0; }');
    L.push('}');

    // Dust/firefly float
    L.push('@keyframes mood-fx-float {');
    L.push('  0%   { transform:translate(0,0); opacity:0; }');
    L.push('  20%  { opacity:var(--po,0.4); }');
    L.push('  50%  { transform:translate(var(--px,15px), var(--py,-30px)); }');
    L.push('  80%  { opacity:var(--po,0.4); }');
    L.push('  100% { transform:translate(var(--px2,-10px), var(--py2,20px)); opacity:0; }');
    L.push('}');

    return L.join('\n');
  }

  // ══════════════════════════════════════════════════════════════
  //  CSS GENERATION — INTRO
  // ══════════════════════════════════════════════════════════════

  function generateIntroCSS(intro) {
    if (!intro) return '';
    var bc = intro.bodyClass;
    var fc = intro.fadeClass;
    var color = intro.color || '#70b0a0';
    var bg = '#060a0a';
    var L = [];

    // Flicker + glow animations
    L.push('@keyframes mood-intro-flicker {');
    L.push('  0%,100% { opacity:1; } 5% { opacity:0.92; } 8% { opacity:1; }');
    L.push('  50% { opacity:0.96; } 52% { opacity:1; } 80% { opacity:0.94; } 83% { opacity:1; }');
    L.push('}');
    L.push('@keyframes mood-intro-pulse {');
    L.push('  0%,100% { text-shadow:0 0 4px ' + color + '66, 0 0 10px ' + color + '26; }');
    L.push('  50%     { text-shadow:0 0 6px ' + color + '99, 0 0 16px ' + color + '40; }');
    L.push('}');

    // Active intro — monochrome screen effect
    L.push('body.' + bc + ' .BufferWindow {');
    L.push('  background-color:' + bg + ' !important; color:' + color + ' !important;');
    L.push('  font-family:var(--glkote-mono-family);');
    L.push('  animation:mood-intro-flicker 5s steps(1) infinite, mood-intro-pulse 3s ease-in-out infinite;');
    L.push('  transition:none;');
    L.push('}');
    L.push('body.' + bc + ' .BufferWindow .Input { color:' + color + ' !important; caret-color:' + color + ' !important; text-shadow:0 0 4px ' + color + '66; }');
    L.push('body.' + bc + ' .GridWindow, body.' + bc + ' .GridWindow * {');
    L.push('  background-color:' + color + ' !important; color:' + bg + ' !important;');
    L.push('  font-family:var(--glkote-mono-family); text-shadow:none;');
    L.push('}');
    L.push('body.' + bc + ' .GridWindow { box-shadow:0 0 12px ' + color + '33, 0 0 24px ' + color + '14; }');

    // Scanlines + vignette
    L.push('body.' + bc + ' #gameport::before {');
    L.push('  background:repeating-linear-gradient(to bottom, transparent 0px, transparent 3px, rgba(0,0,0,0.15) 3px, rgba(0,0,0,0.15) 4px);');
    L.push('  opacity:1;');
    L.push('}');
    L.push('body.' + bc + ' #gameport::after {');
    L.push('  box-shadow:inset 0 0 80px 20px rgba(0,0,0,0.5), inset 0 0 200px 50px rgba(0,0,0,0.25);');
    L.push('  opacity:1;');
    L.push('}');

    // Scanbar
    L.push('body.' + bc + ' .mood-scanbar {');
    L.push('  display:block;');
    L.push('  background:linear-gradient(to bottom, transparent, ' + color + '06 30%, ' + color + '14 50%, ' + color + '06 70%, transparent);');
    L.push('}');

    // Fade out transition
    L.push('body.' + fc + ' .BufferWindow { transition:background-color 2.5s ease, color 2.5s ease, text-shadow 2.5s ease; }');
    L.push('body.' + fc + ' .GridWindow { transition:background-color 2.5s ease, color 2.5s ease, text-shadow 2.5s ease; }');
    L.push('body.' + fc + ' #gameport::before, body.' + fc + ' #gameport::after { transition:opacity 2.5s ease; opacity:0; }');

    return L.join('\n');
  }

  // ══════════════════════════════════════════════════════════════
  //  CSS GENERATION — STATE PERSISTENT EFFECTS
  // ══════════════════════════════════════════════════════════════

  function generateStateCSS(name, state) {
    var cls = 'mood-state-' + name;
    var fx = state.effects || {};
    var L = [];

    // Distortion — text blur, hue-rotate, letter-spacing ramp/peak/settle
    if (fx.distortion) {
      var d = typeof fx.distortion === 'object' ? fx.distortion : {};
      var dur = (d.duration || 40) + 's';
      var s = d.intensity || 0.8;
      L.push('@keyframes mood-st-' + name + '-distort {');
      L.push('  0% { filter:blur(0.5px) hue-rotate(5deg) saturate(1.1); letter-spacing:0.5px; word-spacing:1px; text-shadow:-0.5px 0 rgba(200,140,40,0.1), 0.5px 0 rgba(80,160,60,0.08); transform:skewX(0deg) translateX(0); }');
      L.push('  25% { filter:blur(' + (2*s).toFixed(1) + 'px) hue-rotate(' + Math.round(40*s) + 'deg) saturate(' + (1+0.6*s).toFixed(1) + '); letter-spacing:' + Math.round(3*s) + 'px; word-spacing:' + Math.round(5*s) + 'px; text-shadow:-1.5px 0 rgba(200,140,40,0.35), 1.5px 0 rgba(80,160,60,0.25), 0 1px rgba(160,100,180,0.2); transform:skewX(' + (0.4*s).toFixed(1) + 'deg) translateX(' + Math.round(3*s) + 'px); }');
      L.push('  40% { filter:blur(' + (3*s).toFixed(1) + 'px) hue-rotate(' + Math.round(65*s) + 'deg) saturate(' + (1+s).toFixed(1) + '); letter-spacing:' + Math.round(6*s) + 'px; word-spacing:' + Math.round(10*s) + 'px; text-shadow:-2.5px 0 rgba(200,140,40,0.5), 2.5px 0 rgba(80,160,60,0.4), 0 1.5px rgba(160,100,180,0.3); transform:skewX(-' + (0.5*s).toFixed(1) + 'deg) translateX(-' + Math.round(4*s) + 'px); }');
      L.push('  70% { filter:blur(1px) hue-rotate(18deg) saturate(1.2); letter-spacing:1px; word-spacing:1.5px; text-shadow:-0.6px 0 rgba(200,140,40,0.12), 0.6px 0 rgba(80,160,60,0.08); transform:skewX(0.1deg) translateX(0.5px); }');
      L.push('  100% { filter:blur(0.3px) hue-rotate(8deg) saturate(1.1); letter-spacing:0.3px; word-spacing:0.5px; text-shadow:-0.4px 0 rgba(180,120,40,0.08), 0.4px 0 rgba(80,140,60,0.05); transform:skewX(0deg) translateX(0); }');
      L.push('}');
      L.push('body.' + cls + ' .BufferWindowInner { animation:mood-st-' + name + '-distort ' + dur + ' ease-in-out forwards; transform-origin:top center; }');
      L.push('body.' + cls + ' .BufferLine { animation-duration:0.6s; }');
    }

    // Vignette — persistent edge darkening with ramp/peak/settle
    if (fx.vignette) {
      var v = typeof fx.vignette === 'object' ? fx.vignette : {};
      var vDur = (v.duration || 40) + 's';
      var vColor = v.color || 'rgba(160,120,40,';
      // Parse base color for intensity scaling
      L.push('@keyframes mood-st-' + name + '-vignette {');
      L.push('  0% { box-shadow:inset 0 0 60px 15px rgba(160,120,40,0.06), inset 0 0 120px 30px rgba(140,100,30,0.03); }');
      L.push('  40% { box-shadow:inset 0 0 100px 35px rgba(160,120,40,0.35), inset 0 0 200px 60px rgba(140,100,30,0.2), inset 0 0 300px 80px rgba(120,80,20,0.1); }');
      L.push('  100% { box-shadow:inset 0 0 60px 15px rgba(160,120,40,0.08), inset 0 0 120px 30px rgba(140,100,30,0.04); }');
      L.push('}');
      L.push('body.' + cls + ' #gameport::after { opacity:1; animation:mood-st-' + name + '-vignette ' + vDur + ' ease-in-out forwards; }');
    }

    // Chromatic — periodic RGB split text-shadow flicker
    if (fx.chromatic) {
      var ch = typeof fx.chromatic === 'object' ? fx.chromatic : {};
      var chFreq = (ch.frequency || 6) + 's';
      var chI = ch.intensity || 0.3;
      L.push('@keyframes mood-st-' + name + '-chromatic {');
      L.push('  0%,89%,100% { text-shadow:none; }');
      L.push('  90% { text-shadow:-1px 0 rgba(255,60,60,' + chI.toFixed(2) + '), 1px 0 rgba(60,60,255,' + chI.toFixed(2) + '); }');
      L.push('  93% { text-shadow:1px 0 rgba(255,60,60,' + (chI*0.7).toFixed(2) + '), -1px 0 rgba(60,60,255,' + (chI*0.7).toFixed(2) + '); }');
      L.push('  95% { text-shadow:none; }');
      L.push('}');
      L.push('body.' + cls + ' .BufferWindow { animation:mood-st-' + name + '-chromatic ' + chFreq + ' steps(1) infinite; }');
    }

    // Static — periodic scanline overlay flicker
    if (fx['static']) {
      var st = typeof fx['static'] === 'object' ? fx['static'] : {};
      var stFreq = (st.frequency || 8) + 's';
      var stI = st.intensity || 0.06;
      L.push('@keyframes mood-st-' + name + '-static {');
      L.push('  0%,92%,100% { opacity:0; }');
      L.push('  93% { opacity:' + (stI * 0.7).toFixed(3) + '; }');
      L.push('  95% { opacity:0; }');
      L.push('  96% { opacity:' + (stI * 0.5).toFixed(3) + '; }');
      L.push('  97% { opacity:0; }');
      L.push('}');
      L.push('body.' + cls + ' #gameport::before {');
      L.push('  background:repeating-linear-gradient(to bottom, transparent 0px, transparent 2px, rgba(255,255,255,' + stI.toFixed(2) + ') 2px, rgba(255,255,255,' + stI.toFixed(2) + ') 3px);');
      L.push('  animation:mood-st-' + name + '-static ' + stFreq + ' steps(1) infinite; opacity:0;');
      L.push('}');
    }

    return L.join('\n');
  }

  // ══════════════════════════════════════════════════════════════
  //  STYLE INJECTION
  // ══════════════════════════════════════════════════════════════

  function injectStyles(presets) {
    if (_baseStyleEl) _baseStyleEl.remove();
    _baseStyleEl = document.createElement('style');
    _baseStyleEl.id = 'mood-engine-css';

    var parts = [];
    if (_managed) parts.push(generateBaseCSS(presets));
    parts.push(generateEffectCSS());
    if (_introConfig) parts.push(generateIntroCSS(_introConfig));

    _baseStyleEl.textContent = parts.join('\n');
    document.head.appendChild(_baseStyleEl);
  }

  function injectStateStyle(name, state) {
    var el = _stateStyleEls[name];
    if (el) el.remove();
    el = document.createElement('style');
    el.id = 'mood-state-' + name + '-css';
    el.textContent = generateStateCSS(name, state);
    document.head.appendChild(el);
    _stateStyleEls[name] = el;
  }

  // ══════════════════════════════════════════════════════════════
  //  PALETTE APPLICATION
  // ══════════════════════════════════════════════════════════════

  function resolvePaletteForZone(zone) {
    // Active states override (later states win)
    var keys = Object.keys(_activeStates);
    for (var i = keys.length - 1; i >= 0; i--) {
      var st = _states[keys[i]];
      if (st && st.palettes && st.palettes[zone]) return st.palettes[zone];
    }
    if (_resolvePaletteCb) {
      var p = _resolvePaletteCb(zone, _palettes);
      if (p) return p;
    }
    return _palettes[zone];
  }

  function applyPalette(zone) {
    var p = resolvePaletteForZone(zone);
    if (!p && _fallbackZone) p = resolvePaletteForZone(_fallbackZone);
    if (!p) {
      var keys = Object.keys(_palettes);
      if (keys.length) p = _palettes[keys[0]];
    }
    if (!p) return;

    var root = document.documentElement.style;
    root.setProperty('--mood-buffer-bg', p.bufferBg);
    root.setProperty('--mood-buffer-fg', p.bufferFg);
    root.setProperty('--mood-grid-bg', p.gridBg);
    root.setProperty('--mood-grid-fg', p.gridFg);
    root.setProperty('--mood-accent', p.accent);
    root.setProperty('--mood-ui-bg', p.uiBg);
    root.setProperty('--mood-border', p.border);

    root.setProperty('--glkote-buffer-bg', p.bufferBg);
    root.setProperty('--glkote-buffer-fg', p.bufferFg);
    root.setProperty('--glkote-grid-bg', p.gridBg);
    root.setProperty('--glkote-grid-fg', p.gridFg);
    root.setProperty('--glkote-input-fg', p.accent);
    root.setProperty('--asyncglk-ui-bg', p.uiBg);
    root.setProperty('--asyncglk-ui-border', p.border);

    var gp = document.getElementById('gameport');
    if (gp) gp.style.backgroundColor = p.uiBg;
  }

  // ══════════════════════════════════════════════════════════════
  //  ROOM DETECTION
  // ══════════════════════════════════════════════════════════════

  function extractRoomName(gridWindow) {
    var firstLine = gridWindow.querySelector('.GridLine');
    if (!firstLine) return null;
    var text = (firstLine.textContent || '').trim();
    text = text.replace(/\s{2,}.*$/, '').trim();
    return text || null;
  }

  function handleRoomChange(roomName) {
    if (roomName === _currentRoom) return;
    var prevRoom = _currentRoom;
    var prevZone = _currentZone;
    _currentRoom = roomName;

    var zone = _roomZones[roomName] || _fallbackZone;
    if (!zone) return;

    _currentZone = zone;
    if (zone !== prevZone || Object.keys(_activeStates).length > 0) {
      console.log('[mood] ' + roomName + ' \u2192 ' + zone);
      applyPalette(zone);
    }

    processRoomTriggers(roomName, zone, prevRoom, prevZone);
    if (_onRoomChangeCb) _onRoomChangeCb(roomName, zone);
  }

  function attachGridObserver(grid) {
    var observer = new MutationObserver(function() {
      var name = extractRoomName(grid);
      if (name) handleRoomChange(name);
    });
    observer.observe(grid, { childList: true, characterData: true, subtree: true });
    var name = extractRoomName(grid);
    if (name) handleRoomChange(name);
  }

  function startGridObserving() {
    var grid = document.querySelector('.GridWindow');
    if (grid) { attachGridObserver(grid); return; }
    var poll = setInterval(function() {
      grid = document.querySelector('.GridWindow');
      if (grid) { clearInterval(poll); attachGridObserver(grid); }
    }, 500);
  }

  // ══════════════════════════════════════════════════════════════
  //  BUFFER TEXT WATCHING
  // ══════════════════════════════════════════════════════════════

  function watchBuffer() {
    // Only attach if there are triggers or callbacks
    var needsWatch = _triggers.length > 0 || _onBufferTextCb;
    if (!needsWatch) return;

    function tryAttach() {
      var buf = document.querySelector('.BufferWindow');
      if (!buf) return false;
      new MutationObserver(function(muts) {
        for (var i = 0; i < muts.length; i++) {
          for (var j = 0; j < muts[i].addedNodes.length; j++) {
            var node = muts[i].addedNodes[j];
            if (node.nodeType !== 1) continue;
            var text = (node.textContent || '').trim();
            if (text.length > 0) {
              processTextTriggers(text, _lastBufferText);
              if (_onBufferTextCb) _onBufferTextCb(text, _lastBufferText);
              _lastBufferText = text.toLowerCase();
            }
          }
        }
      }).observe(buf, { childList: true, subtree: true });
      return true;
    }
    if (!tryAttach()) {
      var poll = setInterval(function() { if (tryAttach()) clearInterval(poll); }, 500);
    }
  }

  // ══════════════════════════════════════════════════════════════
  //  BUILT-IN EFFECTS
  // ══════════════════════════════════════════════════════════════

  function fireEffect(name, opts) {
    opts = opts || {};
    var fn = EFFECTS[name];
    if (fn) { fn(opts); console.log('[fx] ' + name); }
    else console.warn('[mood] Unknown effect: ' + name);
  }

  var EFFECTS = {
    shake: function(opts) {
      var intensity = opts.intensity != null ? opts.intensity : 0.5;
      var level = intensity < 0.4 ? 'light' : (intensity > 0.7 ? 'heavy' : 'medium');
      var dur = opts.duration || (level === 'medium' ? 600 : 500);
      var cls = 'mood-fx-shake-' + level;
      document.body.classList.add(cls);
      setTimeout(function() { document.body.classList.remove(cls); }, dur + 100);
    },

    flash: function(opts) {
      var color = opts.color || 'rgba(255,255,240,0.6)';
      var dur = opts.duration || 2500;
      var intensity = opts.intensity != null ? opts.intensity : 1.0;
      var big = opts.size === 'large';
      var el = document.createElement('div');
      el.style.cssText = 'position:fixed; pointer-events:none; z-index:10003;' +
        (big ? ' inset:-50%; width:200%; height:200%;' : ' inset:0;') +
        ' background:radial-gradient(ellipse at center, ' + color + ' 0%, transparent 70%);' +
        ' opacity:0; animation:mood-fx-flash ' + dur + 'ms ease-out forwards;' +
        (intensity < 1 ? ' --mood-fx-flash-scale:' + intensity + ';' : '');
      // Scale peak opacity via a wrapper style if intensity < 1
      if (intensity < 1) {
        var styleEl = document.createElement('style');
        var id = 'mood-fx-flash-' + Date.now();
        el.id = id;
        styleEl.textContent = '@keyframes mood-fx-flash-scaled { 0% { opacity:0; } 15% { opacity:' + (0.6 * intensity).toFixed(2) + '; } 40% { opacity:' + (0.3 * intensity).toFixed(2) + '; } 100% { opacity:0; } }' +
          ' #' + id + ' { animation-name:mood-fx-flash-scaled !important; }';
        document.head.appendChild(styleEl);
        document.body.appendChild(el);
        setTimeout(function() { el.remove(); styleEl.remove(); }, dur + 500);
      } else {
        document.body.appendChild(el);
        setTimeout(function() { el.remove(); }, dur + 500);
      }
    },

    particles: function(opts) {
      var type = opts.particle || 'glass';
      var count = opts.count || 15;
      var dur = opts.duration || 1200;
      var colors = opts.colors || null;
      var cx = window.innerWidth / 2;
      var cy = window.innerHeight * 0.4;

      var defs = {
        glass: { css:'background:linear-gradient(135deg,rgba(200,220,240,0.8),rgba(140,170,200,0.4)); clip-path:polygon(20% 0%,100% 10%,80% 100%,0% 90%);', minW:3, maxW:9, minH:5, maxH:15, anim:'mood-fx-particle-burst', glow:false },
        sparks: { css:'border-radius:50%;', minW:2, maxW:7, minH:2, maxH:7, anim:'mood-fx-particle-burst', glow:true, defaultColors:['#ffd700','#ffb800','#ff8c00','#fff4c0','#ffe066','#ffffff','#ffaa00'] },
        embers: { css:'background:rgba(255,100,30,0.7); border-radius:50%;', minW:2, maxW:5, minH:2, maxH:5, anim:'mood-fx-particle-fall', glow:false }
      };

      var def = defs[type] || defs.glass;
      var palette = colors || def.defaultColors || null;
      var els = [];
      for (var i = 0; i < count; i++) {
        var el = document.createElement('div');
        var angle = (i / count) * Math.PI * 2 + (Math.random() - 0.5) * 0.6;
        var dist = 50 + Math.random() * 200;
        var w = def.minW + Math.random() * (def.maxW - def.minW);
        var h = def.minH + Math.random() * (def.maxH - def.minH);
        var d = 0.6 + Math.random() * 0.6;
        var sparkColor = palette ? palette[Math.floor(Math.random() * palette.length)] : '';
        var sparkCSS = def.css;
        if (palette && def.glow) {
          sparkCSS = 'background:' + sparkColor + '; border-radius:50%; box-shadow:0 0 8px ' + sparkColor + ', 0 0 16px rgba(255,200,0,0.3);';
        } else if (palette) {
          sparkCSS = 'background:' + sparkColor + '; ' + def.css;
        }
        el.style.cssText = 'position:fixed; pointer-events:none; z-index:10003;' +
          ' left:' + cx + 'px; top:' + cy + 'px; width:' + w + 'px; height:' + h + 'px;' +
          ' ' + sparkCSS +
          ' --px:' + (Math.cos(angle) * dist).toFixed(0) + 'px;' +
          ' --py:' + (Math.sin(angle) * dist + 40).toFixed(0) + 'px;' +
          ' --pr:' + (Math.random() * 360 - 180).toFixed(0) + 'deg;' +
          ' animation:' + def.anim + ' ' + d.toFixed(2) + 's ease-out forwards;';
        document.body.appendChild(el);
        els.push(el);
      }
      setTimeout(function() { for (var i = 0; i < els.length; i++) els[i].remove(); }, dur + 500);
    },

    ripple: function(opts) {
      var dur = opts.duration || 2500;
      // Apply via temporary style to control duration
      var el = document.createElement('style');
      el.textContent = 'body.mood-fx-ripple #gameport { animation:mood-fx-ripple ' + dur + 'ms ease-in-out; }';
      document.head.appendChild(el);
      document.body.classList.add('mood-fx-ripple');
      setTimeout(function() { document.body.classList.remove('mood-fx-ripple'); el.remove(); }, dur + 100);
    },

    glitch: function(opts) {
      var dur = opts.duration || 1500;
      var el = document.createElement('style');
      el.textContent = 'body.mood-fx-glitch #gameport { animation:mood-fx-glitch ' + dur + 'ms steps(1) forwards; }';
      document.head.appendChild(el);
      document.body.classList.add('mood-fx-glitch');

      // Static overlay
      var staticEl = document.createElement('div');
      staticEl.style.cssText = 'position:fixed; inset:0; pointer-events:none; z-index:10003;' +
        ' background:repeating-linear-gradient(to bottom, transparent 0px, transparent 2px, rgba(255,255,255,0.08) 2px, rgba(255,255,255,0.08) 3px);' +
        ' animation:mood-fx-flash ' + dur + 'ms steps(1) forwards;';
      document.body.appendChild(staticEl);

      setTimeout(function() { document.body.classList.remove('mood-fx-glitch'); staticEl.remove(); el.remove(); }, dur + 100);
    },

    vignette: function(opts) {
      var color = opts.color || 'rgba(160,60,30,0.4)';
      var dur = opts.duration || 1500;
      var el = document.createElement('div');
      el.style.cssText = 'position:fixed; inset:0; pointer-events:none; z-index:10003;' +
        ' box-shadow:inset 0 0 80px 20px ' + color + ', inset 0 0 160px 40px ' + color + ';' +
        ' animation:mood-fx-vignette ' + dur + 'ms ease-out forwards;';
      document.body.appendChild(el);
      setTimeout(function() { el.remove(); }, dur + 300);
    },

    flood: function(opts) {
      var dur = opts.duration || 3000;
      var el = document.createElement('div');
      el.style.cssText = 'position:fixed; inset:0; pointer-events:none; z-index:10003;' +
        ' background:linear-gradient(to top, rgba(20,40,60,0.5) 0%, rgba(30,50,70,0.3) 40%, rgba(20,40,60,0.15) 70%, transparent 100%);' +
        ' animation:mood-fx-flood ' + dur + 'ms ease-in forwards;';
      document.body.appendChild(el);
      setTimeout(function() { el.remove(); }, dur + 1000);
    },

    drain: function(opts) {
      var dur = opts.duration || 2000;
      fireEffect('shake', { intensity: 0.7, duration: 500 });
      var el = document.createElement('div');
      el.style.cssText = 'position:fixed; inset:0; pointer-events:none; z-index:10003;' +
        ' background:linear-gradient(to bottom, transparent 30%, rgba(60,100,140,0.15) 60%, rgba(40,80,120,0.25) 100%);' +
        ' animation:mood-fx-drain ' + dur + 'ms ease-in forwards;';
      document.body.appendChild(el);
      setTimeout(function() { el.remove(); }, dur + 500);
    },

    pulse: function(opts) {
      var color = opts.color || 'var(--mood-accent)';
      var dur = opts.duration || 1000;
      var el = document.createElement('div');
      el.style.cssText = 'position:fixed; inset:0; pointer-events:none; z-index:10003;' +
        ' box-shadow:inset 0 0 30px 5px ' + color + ';' +
        ' animation:mood-fx-pulse ' + dur + 'ms ease-in-out forwards;';
      document.body.appendChild(el);
      setTimeout(function() { el.remove(); }, dur + 100);
    },

    'fade-in': function(opts) {
      var dur = opts.duration || 1500;
      var el = document.createElement('div');
      el.style.cssText = 'position:fixed; inset:0; pointer-events:none; z-index:10004; background:#000;' +
        ' animation:mood-fx-fade-in ' + dur + 'ms ease forwards;';
      document.body.appendChild(el);
      setTimeout(function() { el.remove(); }, dur + 100);
    },

    'fade-out': function(opts) {
      var dur = opts.duration || 1500;
      var el = document.createElement('div');
      el.style.cssText = 'position:fixed; inset:0; pointer-events:none; z-index:10004; background:#000;' +
        ' animation:mood-fx-fade-out ' + dur + 'ms ease forwards;';
      document.body.appendChild(el);
    },

    // ── Tier 1: textGlow ──
    // Golden/colored glow on the last BufferLine
    textGlow: function(opts) {
      var color = opts.color || '#ffd700';
      var dur = opts.duration || 2500;
      var midColor = opts.midColor || lightenColor(color, 0.3);
      var outerColor = opts.outerColor || color;
      var farColor = opts.farColor || darkenColor(color, 0.3);
      var styleEl = document.createElement('style');
      var id = 'mood-fx-tg-' + Date.now();
      styleEl.id = id;
      styleEl.textContent =
        '@keyframes ' + id + ' {' +
        '  0% { color:inherit; text-shadow:none; }' +
        '  15% { color:' + color + '; text-shadow:0 0 12px ' + color + '99, 0 0 30px ' + outerColor + '4d, 0 0 60px ' + farColor + '26; }' +
        '  50% { color:' + midColor + '; text-shadow:0 0 8px ' + color + '4d; }' +
        '  100% { color:inherit; text-shadow:none; }' +
        '}' +
        ' body.' + id + ' .BufferLine:last-of-type { animation:' + id + ' ' + dur + 'ms ease-out; }';
      document.head.appendChild(styleEl);
      document.body.classList.add(id);
      setTimeout(function() { document.body.classList.remove(id); styleEl.remove(); }, dur + 100);
    },

    // ── Tier 1: invert ──
    // Filter invert + hue-rotate flicker (shock/surprise)
    invert: function(opts) {
      var dur = opts.duration || 800;
      var styleEl = document.createElement('style');
      styleEl.textContent = 'body.mood-fx-invert { animation:mood-fx-invert ' + dur + 'ms ease-out; }';
      document.head.appendChild(styleEl);
      document.body.classList.add('mood-fx-invert');
      setTimeout(function() { document.body.classList.remove('mood-fx-invert'); styleEl.remove(); }, dur + 100);
    },

    // ── Tier 1: shockwave ──
    // Expanding rings from screen center
    shockwave: function(opts) {
      var count = opts.count || 5;
      var color = opts.color || '#ffd700';
      var dur = opts.duration || 2000;
      var els = [];
      for (var i = 0; i < count; i++) {
        var ring = document.createElement('div');
        var ringDur = (dur / 2000) * (1 + i * 0.25);
        var ringDelay = i * 0.12;
        ring.style.cssText = 'position:fixed; top:50%; left:50%; width:80px; height:80px;' +
          ' border-radius:50%; border:3px solid ' + color + '80;' +
          ' box-shadow:0 0 20px ' + color + '4d, inset 0 0 20px ' + color + '1a;' +
          ' pointer-events:none; z-index:10005;' +
          ' animation:mood-fx-shockwave ' + ringDur.toFixed(2) + 's ' + ringDelay.toFixed(2) + 's ease-out forwards;';
        document.body.appendChild(ring);
        els.push(ring);
      }
      setTimeout(function() { for (var i = 0; i < els.length; i++) els[i].remove(); }, dur + 500);
    },

    // ── Tier 1: aura ──
    // Persistent screen-edge vignette glow (toggleable)
    aura: function(opts) {
      var color = opts.color || 'rgba(80,130,255,0.2)';
      var intensity = opts.intensity || 'faint';
      // Remove existing aura
      var existing = document.getElementById('mood-fx-aura');
      var existingStyle = document.getElementById('mood-fx-aura-css');
      if (existing) existing.remove();
      if (existingStyle) existingStyle.remove();
      // Build shadow based on intensity
      var shadow;
      if (intensity === 'bright') {
        shadow = 'inset 0 0 100px 25px ' + color + ', inset 0 0 200px 50px ' + color + ', inset 0 0 300px 80px ' + color;
      } else {
        shadow = 'inset 0 0 80px 15px ' + color + ', inset 0 0 160px 30px ' + color;
      }
      var el = document.createElement('div');
      el.id = 'mood-fx-aura';
      el.style.cssText = 'position:fixed; inset:0; pointer-events:none; z-index:9999;' +
        ' box-shadow:' + shadow + '; transition:box-shadow 1.5s ease-in-out, opacity 1.5s ease-in-out;';
      document.body.appendChild(el);
    },

    // ── Tier 1: ambient ──
    // Persistent looping particles tied to room (auto-cleanup on room exit)
    ambient: function(opts) {
      var type = opts.particle || 'leaves';
      var count = opts.count || 20;
      clearAmbient();  // remove existing ambient particles

      var AMBIENT_DEFS = {
        leaves: {
          colors: ['#4a8030','#5a9035','#3d7028','#6aaa40','#8ab850','#a0c060','#7a6030','#9a8040','#c4a050','#b8a040'],
          anims: ['mood-fx-leaf1','mood-fx-leaf2','mood-fx-leaf3'],
          shape: 'border-radius:50% 0 50% 0; filter:blur(0.3px);',
          minW:6, maxW:16, aspect:0.65, minDur:7, maxDur:15, maxDelay:12
        },
        snow: {
          colors: ['rgba(200,215,235,0.5)','rgba(220,230,245,0.4)','rgba(240,245,255,0.6)'],
          anims: ['mood-fx-snowfall'],
          shape: 'border-radius:50%;',
          minW:2, maxW:6, aspect:1, minDur:8, maxDur:18, maxDelay:15
        },
        rain: {
          colors: ['rgba(140,170,200,0.4)','rgba(120,150,190,0.3)'],
          anims: ['mood-fx-rainfall'],
          shape: 'border-radius:0 0 50% 50%; width:1px !important;',
          minW:1, maxW:2, aspect:4, minDur:1.5, maxDur:3, maxDelay:4
        },
        dust: {
          colors: ['rgba(200,180,140,0.3)','rgba(180,160,120,0.2)','rgba(220,200,160,0.25)'],
          anims: ['mood-fx-float'],
          shape: 'border-radius:50%;',
          minW:2, maxW:5, aspect:1, minDur:10, maxDur:20, maxDelay:15
        },
        embers: {
          colors: ['rgba(255,120,30,0.6)','rgba(255,80,20,0.5)','rgba(255,160,40,0.5)','rgba(255,200,60,0.4)'],
          anims: ['mood-fx-float'],
          shape: 'border-radius:50%;',
          minW:2, maxW:4, aspect:1, minDur:6, maxDur:14, maxDelay:10
        },
        fireflies: {
          colors: ['rgba(180,255,80,0.5)','rgba(200,255,100,0.4)','rgba(160,240,60,0.6)'],
          anims: ['mood-fx-float'],
          shape: 'border-radius:50%; box-shadow:0 0 4px currentColor;',
          minW:2, maxW:4, aspect:1, minDur:8, maxDur:16, maxDelay:12
        }
      };

      var def = AMBIENT_DEFS[type] || AMBIENT_DEFS.leaves;
      var container = document.createElement('div');
      container.id = 'mood-fx-ambient';
      document.body.appendChild(container);
      _ambientContainer = container;

      for (var i = 0; i < count; i++) {
        var p = document.createElement('div');
        var size = def.minW + Math.random() * (def.maxW - def.minW);
        var animName = def.anims[Math.floor(Math.random() * def.anims.length)];
        var color = def.colors[Math.floor(Math.random() * def.colors.length)];
        var dur = def.minDur + Math.random() * (def.maxDur - def.minDur);
        var delay = Math.random() * def.maxDelay;
        var px = (Math.random() * 60 - 30).toFixed(0);
        var py = (Math.random() * -60 - 20).toFixed(0);
        p.style.cssText = 'position:fixed; pointer-events:none; z-index:10002; opacity:0;' +
          ' left:' + (Math.random() * 100) + '%; top:0;' +
          ' width:' + size + 'px; height:' + (size * def.aspect) + 'px;' +
          ' background:' + color + '; ' + def.shape +
          ' --px:' + px + 'px; --py:' + py + 'px; --px2:' + (-px * 0.6).toFixed(0) + 'px; --py2:' + (-py * 0.7).toFixed(0) + 'px;' +
          ' --po:' + (0.2 + Math.random() * 0.4).toFixed(2) + ';' +
          ' animation:' + animName + ' ' + dur.toFixed(1) + 's ' + delay.toFixed(1) + 's ease-in-out infinite;';
        container.appendChild(p);
      }
    },

    // ── Tier 2: sway ──
    // Persistent gentle motion on BufferWindowInner
    sway: function(opts) {
      var speed = opts.speed || 12;
      var intensity = opts.intensity || 0.5;
      var existing = document.getElementById('mood-fx-sway-css');
      if (existing) existing.remove();
      var styleEl = document.createElement('style');
      styleEl.id = 'mood-fx-sway-css';
      // Scale transform values by intensity
      var r1 = (0.5 * intensity).toFixed(1), r2 = (0.3 * intensity).toFixed(1);
      var r3 = (0.5 * intensity).toFixed(1), r4 = (0.2 * intensity).toFixed(1);
      var t1 = Math.round(3 * intensity), t2 = Math.round(2 * intensity);
      var t3 = Math.round(4 * intensity), t4 = Math.round(1 * intensity);
      styleEl.textContent =
        'body.mood-fx-sway .BufferWindowInner {' +
        '  position:relative; transform-origin:top center;' +
        '  animation:mood-fx-sway-custom ' + speed + 's ease-in-out infinite;' +
        '}' +
        '@keyframes mood-fx-sway-custom {' +
        '  0%,100% { transform:rotate(-' + r1 + 'deg) translateX(-' + t1 + 'px); }' +
        '  30% { transform:rotate(' + r2 + 'deg) translateX(' + t2 + 'px); }' +
        '  60% { transform:rotate(' + r3 + 'deg) translateX(' + t3 + 'px); }' +
        '  80% { transform:rotate(-' + r4 + 'deg) translateX(-' + t4 + 'px); }' +
        '}';
      document.head.appendChild(styleEl);
      document.body.classList.add('mood-fx-sway');
    },

    // ── Tier 2: glow ──
    // Persistent pulsing box-shadow on BufferWindow
    glow: function(opts) {
      var color = opts.color || 'rgba(50,150,30,0.10)';
      var speed = opts.speed || 7;
      var existing = document.getElementById('mood-fx-glow-css');
      if (existing) existing.remove();
      var styleEl = document.createElement('style');
      styleEl.id = 'mood-fx-glow-css';
      styleEl.textContent =
        'body.mood-fx-glow .BufferWindow {' +
        '  animation:mood-fx-glow-custom ' + speed + 's ease-in-out infinite;' +
        '}' +
        '@keyframes mood-fx-glow-custom {' +
        '  0%,100% { box-shadow:inset 0 0 120px 20px ' + color + ', inset 0 80px 80px -30px ' + color + '; }' +
        '  50% { box-shadow:inset 0 0 120px 20px ' + scaleAlpha(color, 2.5) + ', inset 0 80px 80px -30px ' + scaleAlpha(color, 2.3) + '; }' +
        '}';
      document.head.appendChild(styleEl);
      document.body.classList.add('mood-fx-glow');
    }
  };

  // ── Ambient particle management ──

  var _ambientContainer = null;

  function clearAmbient() {
    if (_ambientContainer) { _ambientContainer.remove(); _ambientContainer = null; }
  }

  function clearSway() {
    document.body.classList.remove('mood-fx-sway');
    var el = document.getElementById('mood-fx-sway-css');
    if (el) el.remove();
  }

  function clearGlow() {
    document.body.classList.remove('mood-fx-glow');
    var el = document.getElementById('mood-fx-glow-css');
    if (el) el.remove();
  }

  function clearAura() {
    var el = document.getElementById('mood-fx-aura');
    if (el) el.remove();
  }

  // ── Color utility helpers ──

  function lightenColor(hex, amount) {
    hex = hex.replace('#', '');
    if (hex.length === 3) hex = hex[0]+hex[0]+hex[1]+hex[1]+hex[2]+hex[2];
    var r = parseInt(hex.slice(0,2), 16), g = parseInt(hex.slice(2,4), 16), b = parseInt(hex.slice(4,6), 16);
    r = Math.min(255, Math.round(r + (255-r) * amount));
    g = Math.min(255, Math.round(g + (255-g) * amount));
    b = Math.min(255, Math.round(b + (255-b) * amount));
    return '#' + ((1<<24)+(r<<16)+(g<<8)+b).toString(16).slice(1);
  }

  function darkenColor(hex, amount) {
    hex = hex.replace('#', '');
    if (hex.length === 3) hex = hex[0]+hex[0]+hex[1]+hex[1]+hex[2]+hex[2];
    var r = parseInt(hex.slice(0,2), 16), g = parseInt(hex.slice(2,4), 16), b = parseInt(hex.slice(4,6), 16);
    r = Math.max(0, Math.round(r * (1-amount)));
    g = Math.max(0, Math.round(g * (1-amount)));
    b = Math.max(0, Math.round(b * (1-amount)));
    return '#' + ((1<<24)+(r<<16)+(g<<8)+b).toString(16).slice(1);
  }

  function scaleAlpha(rgbaStr, factor) {
    // Scale the alpha of an rgba() string
    var m = rgbaStr.match(/rgba?\((\d+),\s*(\d+),\s*(\d+),?\s*([\d.]*)\)/);
    if (!m) return rgbaStr;
    var a = parseFloat(m[4] || '1');
    return 'rgba(' + m[1] + ',' + m[2] + ',' + m[3] + ',' + Math.min(1, a * factor).toFixed(3) + ')';
  }

  // ══════════════════════════════════════════════════════════════
  //  STATE MANAGEMENT
  // ══════════════════════════════════════════════════════════════

  function activateState(name) {
    if (_activeStates[name]) return;
    var st = _states[name];
    if (!st) { console.warn('[mood] Unknown state: ' + name); return; }
    console.log('[mood] State activated: ' + name);
    _activeStates[name] = true;

    if (st.effects && Object.keys(st.effects).length > 0) {
      injectStateStyle(name, st);
    }

    document.body.classList.add('mood-state-' + name);
    if (_currentZone) applyPalette(_currentZone);
  }

  function deactivateState(name) {
    if (!_activeStates[name]) return;
    delete _activeStates[name];
    document.body.classList.remove('mood-state-' + name);
    var el = _stateStyleEls[name];
    if (el) { el.remove(); delete _stateStyleEls[name]; }
    if (_currentZone) applyPalette(_currentZone);
  }

  // ══════════════════════════════════════════════════════════════
  //  TRIGGER PROCESSING
  // ══════════════════════════════════════════════════════════════

  function matchText(pattern, text) {
    if (pattern instanceof RegExp) return pattern.test(text);
    if (typeof pattern === 'string') return text.toLowerCase().indexOf(pattern.toLowerCase()) !== -1;
    return false;
  }

  function executeTriggerActions(trigger) {
    if (trigger.effect) fireEffect(trigger.effect, trigger);

    if (trigger.addClass) {
      document.body.classList.add(trigger.addClass);
      if (trigger.duration && !trigger.setState) {
        var cls = trigger.addClass;
        setTimeout(function() { document.body.classList.remove(cls); }, trigger.duration);
      }
    }
    if (trigger.removeClass) document.body.classList.remove(trigger.removeClass);

    if (trigger.setState) {
      var delay = trigger.delay || 0;
      var sn = trigger.setState;
      if (delay > 0) setTimeout(function() { activateState(sn); }, delay);
      else activateState(sn);
    }
    if (trigger.clearState) deactivateState(trigger.clearState);

    if (trigger.palette && !trigger.setState) {
      var zone = trigger.palette;
      applyPalette(zone);
      if (trigger.duration) {
        setTimeout(function() { if (_currentZone) applyPalette(_currentZone); }, trigger.duration);
      }
    }

    // Clear a persistent effect (aura, sway, glow, ambient)
    if (trigger.clearEffect) {
      var ce = trigger.clearEffect;
      if (ce === 'aura') clearAura();
      else if (ce === 'sway') clearSway();
      else if (ce === 'glow') clearGlow();
      else if (ce === 'ambient') clearAmbient();
    }
  }

  function processTextTriggers(text) {
    for (var i = 0; i < _triggers.length; i++) {
      var t = _triggers[i];
      if (!t.on) continue;
      if (t._fired && t.once) continue;
      if (matchText(t.on, text)) {
        t._fired = true;
        executeTriggerActions(t);
      }
    }
  }

  function processRoomTriggers(roomName, zone, prevRoom, prevZone) {
    // Auto-generate leave triggers for persistent room effects
    // If a trigger uses onRoom with ambient/sway/glow, auto-clear on room exit
    for (var i = 0; i < _triggers.length; i++) {
      var t = _triggers[i];

      // Auto-clear persistent effects when leaving the room that activated them
      if (t.onRoom && prevRoom === t.onRoom && roomName !== t.onRoom) {
        if (t.effect === 'ambient') clearAmbient();
        if (t.effect === 'sway') clearSway();
        if (t.effect === 'glow') clearGlow();
      }

      if (t._fired && t.once) continue;
      if (t.onRoom && roomName === t.onRoom) { t._fired = true; executeTriggerActions(t); }
      if (t.onLeaveRoom && prevRoom === t.onLeaveRoom) { t._fired = true; executeTriggerActions(t); }
      if (t.onZone && zone === t.onZone && prevZone !== t.onZone) { t._fired = true; executeTriggerActions(t); }
      if (t.onLeaveZone && prevZone === t.onLeaveZone && zone !== t.onLeaveZone) { t._fired = true; executeTriggerActions(t); }
    }
  }

  // ══════════════════════════════════════════════════════════════
  //  INTRO MODE
  // ══════════════════════════════════════════════════════════════

  var INTRO_PRESETS = {
    monitor: { bodyClass:'mood-intro-monitor', fadeClass:'mood-intro-monitor-fade', fadeDuration:2500, color:'#70b0a0' },
    crt:     { bodyClass:'mood-intro-crt',     fadeClass:'mood-intro-crt-fade',     fadeDuration:2500, color:'#33ff33' }
  };

  function resolveIntro(intro) {
    if (!intro) return null;
    if (typeof intro === 'string') return INTRO_PRESETS[intro] || null;
    return intro;
  }

  function startIntro() {
    if (!_introConfig) return;
    document.body.classList.add(_introConfig.bodyClass);
  }

  function endIntro() {
    if (!_introConfig) return;
    if (!document.body.classList.contains(_introConfig.bodyClass)) return;
    document.body.classList.remove(_introConfig.bodyClass);
    document.body.classList.add(_introConfig.fadeClass);
    setTimeout(function() {
      document.body.classList.remove(_introConfig.fadeClass);
    }, _introConfig.fadeDuration || 2500);
    console.log('[mood] Intro ended');
  }

  function watchForFirstInput() {
    if (!_introConfig) return;
    var settled = false;
    var settleTimer = null;
    function tryAttachInput() {
      var buf = document.querySelector('.BufferWindow');
      if (!buf) return false;
      var obs = new MutationObserver(function(muts) {
        if (settled) { endIntro(); obs.disconnect(); return; }
        for (var i = 0; i < muts.length; i++) {
          for (var j = 0; j < muts[i].addedNodes.length; j++) {
            var node = muts[i].addedNodes[j];
            if (node.nodeType !== 1) continue;
            var inp = node.querySelector && node.querySelector('.Input');
            if (inp) { endIntro(); obs.disconnect(); return; }
          }
        }
        clearTimeout(settleTimer);
        settleTimer = setTimeout(function() { settled = true; }, 1000);
      });
      obs.observe(buf, { childList: true, subtree: true });
      return true;
    }
    if (!tryAttachInput()) {
      var poll = setInterval(function() { if (tryAttachInput()) clearInterval(poll); }, 500);
    }
  }

  // ══════════════════════════════════════════════════════════════
  //  HUB INTEGRATION — platform theme postMessage
  // ══════════════════════════════════════════════════════════════

  function setupHubListener() {
    function ensureRetroFonts() {
      if (document.getElementById('retro-platform-fonts')) return;
      var link = document.createElement('link');
      link.id = 'retro-platform-fonts';
      link.rel = 'stylesheet';
      link.href = 'https://fonts.googleapis.com/css2?family=Pixelify+Sans&family=Press+Start+2P&family=Silkscreen&family=Sixtyfour&family=Tiny5&family=VT323&family=Workbench&display=swap';
      document.head.appendChild(link);
    }

    function applyPlatformTheme(g, sb) {
      ensureRetroFonts();
      var el = document.getElementById('platform-theme-override');
      if (el) el.remove();
      var style = document.createElement('style');
      style.id = 'platform-theme-override';
      var glh = (parseInt(g.gridLineHeight) || 20) + 10;
      style.textContent =
        'body, html { background: ' + g.bodyBg + ' !important; }\n' +
        '.BufferWindow { color: ' + g.bufferFg + ' !important; background-color: ' + g.bufferBg + ' !important; font-family: ' + g.monoFamily + ' !important; font-size: ' + g.bufferSize + ' !important; line-height: ' + g.bufferLineHeight + ' !important; }\n' +
        '.BufferWindow span { color: ' + g.bufferFg + ' !important; }\n' +
        '.BufferWindow span.reverse { color: ' + g.bufferBg + ' !important; background-color: ' + g.bufferFg + ' !important; }\n' +
        '.BufferWindow .Style_input { color: ' + g.inputFg + ' !important; }\n' +
        '.BufferWindow .Style_emphasized { color: ' + g.emphFg + ' !important; }\n' +
        '.BufferWindow .Style_header { color: ' + g.headerFg + ' !important; }\n' +
        '.BufferWindow .Style_subheader, .BufferWindow .Style_alert { color: ' + g.headerFg + ' !important; }\n' +
        '.BufferWindow .Input, .BufferWindow textarea.Input { color: ' + g.inputFg + ' !important; caret-color: ' + g.inputFg + '; font-family: ' + g.monoFamily + ' !important; }\n' +
        '.GridWindow { color: ' + g.gridFg + ' !important; background-color: ' + g.gridBg + ' !important; padding:4px 12px !important; border:none !important; box-shadow:none !important; }\n' +
        '.GridWindow span { color: ' + g.gridFg + ' !important; background-color: ' + g.gridBg + ' !important; }\n' +
        '#loadingpane { color: ' + g.bufferFg + '; background: ' + g.bodyBg + '; font-family: ' + g.monoFamily + '; }\n' +
        '.WindowFrame { background: transparent !important; }\n' +
        'div#gameport { background:linear-gradient(to bottom, ' + g.gridBg + ' 0px, ' + g.gridBg + ' ' + glh + 'px, ' + g.bufferBg + ' ' + glh + 'px) !important; }\n' +
        '* { scrollbar-color: ' + sb.thumb + ' ' + sb.track + '; }\n' +
        '::-webkit-scrollbar { width:10px; background: ' + sb.track + '; }\n' +
        '::-webkit-scrollbar-thumb { background: ' + sb.thumb + '; border-radius:4px; }\n' +
        '::-webkit-scrollbar-thumb:hover { background: ' + sb.thumbHover + '; }\n';
      document.head.appendChild(style);
      setTimeout(function() { window.dispatchEvent(new Event('resize')); }, 50);
    }

    function removePlatformTheme() {
      var el = document.getElementById('platform-theme-override');
      if (el) el.remove();
      setTimeout(function() { window.dispatchEvent(new Event('resize')); }, 50);
    }

    window.addEventListener('message', function(e) {
      if (!e.data) return;
      if (e.data.type === 'ifhub:applyTheme') {
        document.body.classList.add('platform-theme-active');
        applyPlatformTheme(e.data.game, e.data.scrollbar);
      }
      if (e.data.type === 'ifhub:restoreOverlay') {
        document.body.classList.remove('platform-theme-active');
        removePlatformTheme();
      }
    });

    // Auto-apply theme from URL param (standalone mode from hub)
    var params = new URLSearchParams(window.location.search);
    var urlTheme = params.get('theme');
    if (urlTheme && urlTheme !== 'classic') {
      var s = document.createElement('script');
      s.src = '/ifhub/themes.js';
      s.onload = function() {
        if (typeof getTheme === 'function') {
          var t = getTheme(urlTheme);
          if (t) {
            document.body.classList.add('platform-theme-active');
            applyPlatformTheme(t.game, t.scrollbar);
          }
        }
      };
      document.head.appendChild(s);
    }
  }

  // ══════════════════════════════════════════════════════════════
  //  PUBLIC API
  // ══════════════════════════════════════════════════════════════

  function init(config) {
    config = config || {};

    // Determine if engine should manage base CSS
    _managed = !!(config.vibe || config.font || config.size || config.spacing || config.width || (typeof config.color === 'string'));
    _transitionSec = config.transition || 1.2;
    _introConfig = resolveIntro(config.intro);

    var presets = resolvePresets(config);

    // Store config
    _palettes = config.palettes || {};
    _roomZones = config.roomZones || {};
    _fallbackZone = config.fallbackZone || null;
    _onRoomChangeCb = config.onRoomChange || null;
    _onBufferTextCb = config.onBufferText || null;
    _resolvePaletteCb = config.resolvePalette || null;
    _triggers = config.triggers || [];
    _states = config.states || {};
    _activeStates = {};

    // Inject CSS
    injectStyles(presets);

    // Ensure scanbar element exists for intro
    if (_introConfig && !document.querySelector('.mood-scanbar')) {
      var sb = document.createElement('div');
      sb.className = 'mood-scanbar';
      var gp = document.getElementById('gameport');
      if (gp) gp.appendChild(sb);
    }

    // Start systems
    startIntro();
    startGridObserving();
    watchBuffer();
    watchForFirstInput();
    setupHubListener();

    // Page restore handler
    window.addEventListener('pageshow', function(e) {
      if (e.persisted) window.location.reload();
    });
  }

  window.MoodEngine = {
    init: init,
    refresh: function() { if (_currentZone) applyPalette(_currentZone); },
    setState: function(name) { activateState(name); },
    clearState: function(name) { deactivateState(name); },
    fireEffect: function(name, opts) { fireEffect(name, opts); },
    clearAmbient: clearAmbient,
    clearSway: clearSway,
    clearGlow: clearGlow,
    clearAura: clearAura,
    get currentRoom() { return _currentRoom; },
    get currentZone() { return _currentZone; },
    get activeStates() { return Object.keys(_activeStates); },
    presets: { FONTS: FONTS, SIZES: SIZES, SPACINGS: SPACINGS, WIDTHS: WIDTHS, COLORS: COLORS, VIBES: VIBES }
  };
})();
