/**
 * sound-config.js — Fever Dream sound configuration
 *
 * Defines all sound triggers for the game. Loaded after sound-engine.js.
 */
SoundEngine.init({
  storageKey: 'feverdream-audio-muted',

  // Style_user1 triggers (precise, from story.ni via Glulx Text Effects)
  sfx: {
    glass: { src: 'audio/sfx/glass.mp3', volume: 0.4 }
  },

  // Text-matching triggers (ambient/incidental)
  textTriggers: []
});
