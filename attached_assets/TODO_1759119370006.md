# Voice Features Implementation Plan

## Overview
Adding voice narration and interactive audio features across modules (colors, rhymes, etc.) and story builder using Web Speech API for TTS. This includes core JS functions, template updates for buttons, and controls for play/pause/stop.

## Steps

1. **[ ] Add Core Voice Functions to static/js/app.js**
   - Implement speechSynthesis functions: speak(text), pauseSpeech(), resumeSpeech(), stopSpeech()
   - Add voice selection, rate/pitch controls
   - Handle browser compatibility and voice loading
   - Add event listeners for speech events (end, error)

2. **[ ] Update templates/module.html for Voice Integration**
   - Add "🔊 Listen" buttons to lesson content sections (e.g., content, images, rhymes)
   - For rhymes: Add "🎵 Sing Along" with paused narration
   - For colors/shapes: Narrate descriptions and examples
   - For animals/actions: Voice sounds and instructions
   - Integrate with new JS functions

3. **[ ] Update templates/story_builder.html for Story Voice**
   - Add "📖 Read Aloud" button in story display section
   - Narrate generated story content with natural pauses
   - Add play/pause/stop controls near the button

4. **[ ] Add Global Voice Controls**
   - Create a floating voice control UI (play/pause/stop, volume slider)
   - Make it accessible across pages
   - Handle multiple utterances (queue or replace)

5. **[ ] Test and Refine**
   - Test on different browsers (Chrome, Firefox, Safari)
   - Verify bilingual support (english/native)
   - Check for errors in console
   - Ensure no conflicts with existing animations/notifications

## Dependencies
- No new Python/Flask changes needed
- Relies on browser's speechSynthesis API (no external libs)
- Update CSS if needed for new buttons/UI

## Next Steps After Completion
- Run the app and test voice in modules and stories
- Gather user feedback for voice quality/speed
