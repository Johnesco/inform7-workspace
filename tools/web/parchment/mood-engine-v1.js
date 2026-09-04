/**
 * MoodEngine — shared mood palette system for Parchment games.
 *
 * Provides room-based color palette transitions via CSS custom properties,
 * MutationObserver-driven room detection from the GlkOte status bar, and
 * optional hooks for buffer text matching and intro mode.
 *
 * Usage:
 *   <script src="lib/parchment/mood-engine.js"></script>
 *   <script>
 *     MoodEngine.init({
 *       palettes:      { zone: { bufferBg, bufferFg, gridBg, gridFg, accent, uiBg, border } },
 *       roomZones:     { 'Room Name': 'zone' },
 *       fallbackZone:  'cave',                              // optional
 *       onRoomChange:  function(roomName, zone) {},          // optional
 *       onBufferText:  function(text, prevText) {},          // optional
 *       resolvePalette: function(zone, palettes) {},         // optional
 *       intro: { bodyClass: 'crt-intro', fadeClass: 'crt-fade', fadeDuration: 2500 }
 *     });
 */
(function() {
  'use strict';

  var palettes = {};
  var roomZones = {};
  var fallbackZone = null;
  var currentRoom = null;
  var currentZone = null;
  var onRoomChangeCb = null;
  var onBufferTextCb = null;
  var resolvePaletteCb = null;
  var introConfig = null;
  var lastBufferText = '';

  // ── Palette application ──────────────────────────────────────

  function applyPalette(zone) {
    var p = resolvePaletteCb ? resolvePaletteCb(zone, palettes) : null;
    if (!p) p = palettes[zone];
    if (!p && fallbackZone) p = palettes[fallbackZone];
    if (!p) {
      var keys = Object.keys(palettes);
      if (keys.length) p = palettes[keys[0]];
    }
    if (!p) return;

    var root = document.documentElement.style;

    // Mood variables (animated via Houdini @property)
    root.setProperty('--mood-buffer-bg', p.bufferBg);
    root.setProperty('--mood-buffer-fg', p.bufferFg);
    root.setProperty('--mood-grid-bg', p.gridBg);
    root.setProperty('--mood-grid-fg', p.gridFg);
    root.setProperty('--mood-accent', p.accent);
    root.setProperty('--mood-ui-bg', p.uiBg);
    root.setProperty('--mood-border', p.border);

    // Sync GlkOte/AsyncGlk variables so inline styles follow the mood
    root.setProperty('--glkote-buffer-bg', p.bufferBg);
    root.setProperty('--glkote-buffer-fg', p.bufferFg);
    root.setProperty('--glkote-grid-bg', p.gridBg);
    root.setProperty('--glkote-grid-fg', p.gridFg);
    root.setProperty('--glkote-input-fg', p.accent);
    root.setProperty('--asyncglk-ui-bg', p.uiBg);
    root.setProperty('--asyncglk-ui-border', p.border);

    // Direct fallback for gameport background
    var gp = document.getElementById('gameport');
    if (gp) gp.style.backgroundColor = p.uiBg;
  }

  // ── Room name extraction ─────────────────────────────────────

  function extractRoomName(gridWindow) {
    var firstLine = gridWindow.querySelector('.GridLine');
    if (!firstLine) return null;
    var text = (firstLine.textContent || '').trim();
    // Strip trailing score/moves info (everything after 2+ spaces)
    text = text.replace(/\s{2,}.*$/, '').trim();
    return text || null;
  }

  // ── Room change handling ─────────────────────────────────────

  function onRoomChange(roomName) {
    if (roomName === currentRoom) return;
    currentRoom = roomName;

    var zone = roomZones[roomName];
    if (!zone && fallbackZone) zone = fallbackZone;
    if (!zone) return;

    var zoneChanged = (zone !== currentZone);
    currentZone = zone;

    if (zoneChanged) {
      console.log('[mood] ' + roomName + ' \u2192 ' + zone);
      applyPalette(zone);
    }

    // Hook fires on every room change, not just zone changes
    if (onRoomChangeCb) onRoomChangeCb(roomName, zone);
  }

  // ── Grid MutationObserver — room detection from status bar ───

  function attachGridObserver(grid) {
    var observer = new MutationObserver(function() {
      var name = extractRoomName(grid);
      if (name) onRoomChange(name);
    });
    observer.observe(grid, { childList: true, characterData: true, subtree: true });
    // Initial read
    var name = extractRoomName(grid);
    if (name) onRoomChange(name);
  }

  function startGridObserving() {
    var grid = document.querySelector('.GridWindow');
    if (grid) { attachGridObserver(grid); return; }
    var poll = setInterval(function() {
      grid = document.querySelector('.GridWindow');
      if (grid) { clearInterval(poll); attachGridObserver(grid); }
    }, 500);
  }

  // ── Buffer MutationObserver — text pattern matching ──────────

  function watchBuffer() {
    if (!onBufferTextCb) return;
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
              onBufferTextCb(text, lastBufferText);
              lastBufferText = text.toLowerCase();
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

  // ── Intro mode — body class until first user input ───────────

  function startIntro() {
    if (!introConfig) return;
    document.body.classList.add(introConfig.bodyClass);
  }

  function endIntro() {
    if (!introConfig) return;
    if (!document.body.classList.contains(introConfig.bodyClass)) return;
    document.body.classList.remove(introConfig.bodyClass);
    document.body.classList.add(introConfig.fadeClass);
    setTimeout(function() {
      document.body.classList.remove(introConfig.fadeClass);
    }, introConfig.fadeDuration || 2500);
    console.log('[mood] Intro ended');
  }

  function watchForFirstInput() {
    if (!introConfig) return;
    var settled = false;
    var settleTimer = null;
    function tryAttachInput() {
      var buf = document.querySelector('.BufferWindow');
      if (!buf) return false;
      var inputObserver = new MutationObserver(function(muts) {
        // After initial output settled, any new mutation = user input
        if (settled) {
          endIntro();
          inputObserver.disconnect();
          return;
        }
        // Fast path: .Input spans (non-WASM engines like Quixe)
        for (var i = 0; i < muts.length; i++) {
          for (var j = 0; j < muts[i].addedNodes.length; j++) {
            var node = muts[i].addedNodes[j];
            if (node.nodeType !== 1) continue;
            var inp = node.querySelector && node.querySelector('.Input');
            if (inp) {
              endIntro();
              inputObserver.disconnect();
              return;
            }
          }
        }
        // Reset settle timer — output still arriving
        clearTimeout(settleTimer);
        settleTimer = setTimeout(function() { settled = true; }, 1000);
      });
      inputObserver.observe(buf, { childList: true, subtree: true });
      return true;
    }
    if (!tryAttachInput()) {
      var poll = setInterval(function() { if (tryAttachInput()) clearInterval(poll); }, 500);
    }
  }

  // ── Public API ───────────────────────────────────────────────

  function init(config) {
    palettes = config.palettes || {};
    roomZones = config.roomZones || {};
    fallbackZone = config.fallbackZone || null;
    onRoomChangeCb = config.onRoomChange || null;
    onBufferTextCb = config.onBufferText || null;
    resolvePaletteCb = config.resolvePalette || null;
    introConfig = config.intro || null;

    startIntro();
    startGridObserving();
    watchBuffer();
    watchForFirstInput();
  }

  window.MoodEngine = {
    init: init,
    refresh: function() { if (currentZone) applyPalette(currentZone); },
    get currentRoom() { return currentRoom; },
    get currentZone() { return currentZone; }
  };
})();
