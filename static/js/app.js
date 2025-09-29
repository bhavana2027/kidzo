// Voice Features for Kids Learning App
// Using Web Speech API for text-to-speech functionality

class VoiceManager {
    constructor() {
        this.synth = window.speechSynthesis;
        this.currentUtterance = null;
        this.voices = [];
        this.isPlaying = false;
        this.isPaused = false;
        this.currentText = '';
        
        // Voice settings
        this.settings = {
            rate: 0.8,  // Slower for kids
            pitch: 1.2, // Slightly higher pitch for friendliness
            volume: 0.8,
            voiceIndex: 0
        };
        
        this.init();
    }
    
    init() {
        // Load voices when available
        this.loadVoices();
        
        // Update voices when they change (some browsers load voices asynchronously)
        if (this.synth.onvoiceschanged !== undefined) {
            this.synth.onvoiceschanged = () => this.loadVoices();
        }
        
        // Create global voice controls
        this.createGlobalControls();
    }
    
    loadVoices() {
        this.voices = this.synth.getVoices();
        console.log('Available voices:', this.voices.length);
        
        // Try to find a child-friendly voice
        const preferredVoices = this.voices.filter(voice => 
            voice.lang.startsWith('en') && 
            (voice.name.includes('female') || voice.name.includes('Google'))
        );
        
        if (preferredVoices.length > 0) {
            this.settings.voiceIndex = this.voices.indexOf(preferredVoices[0]);
        }
    }
    
    speak(text, options = {}) {
        if (!text || text.trim() === '') return;
        
        // Stop any current speech
        this.stop();
        
        // Create new utterance
        this.currentUtterance = new SpeechSynthesisUtterance(text);
        this.currentText = text;
        
        // Apply settings
        this.currentUtterance.rate = options.rate || this.settings.rate;
        this.currentUtterance.pitch = options.pitch || this.settings.pitch;
        this.currentUtterance.volume = options.volume || this.settings.volume;
        
        // Set voice
        if (this.voices.length > 0) {
            this.currentUtterance.voice = this.voices[this.settings.voiceIndex];
        }
        
        // Event listeners
        this.currentUtterance.onstart = () => {
            this.isPlaying = true;
            this.isPaused = false;
            this.updateGlobalControlsUI();
            console.log('Speech started');
        };
        
        this.currentUtterance.onend = () => {
            this.isPlaying = false;
            this.isPaused = false;
            this.currentUtterance = null;
            this.updateGlobalControlsUI();
            console.log('Speech ended');
        };
        
        this.currentUtterance.onerror = (event) => {
            console.error('Speech error:', event.error);
            this.isPlaying = false;
            this.isPaused = false;
            this.updateGlobalControlsUI();
        };
        
        // Start speaking
        this.synth.speak(this.currentUtterance);
    }
    
    pause() {
        if (this.isPlaying && !this.isPaused) {
            this.synth.pause();
            this.isPaused = true;
            this.updateGlobalControlsUI();
        }
    }
    
    resume() {
        if (this.isPaused) {
            this.synth.resume();
            this.isPaused = false;
            this.updateGlobalControlsUI();
        }
    }
    
    stop() {
        this.synth.cancel();
        this.isPlaying = false;
        this.isPaused = false;
        this.currentUtterance = null;
        this.updateGlobalControlsUI();
    }
    
    toggle() {
        if (this.isPlaying) {
            if (this.isPaused) {
                this.resume();
            } else {
                this.pause();
            }
        }
    }
    
    createGlobalControls() {
        // Create floating voice control panel
        const controlsHTML = `
            <div id="voice-controls" class="voice-controls">
                <button id="voice-toggle" class="voice-btn" title="Play/Pause">
                    <span class="voice-icon">🔊</span>
                </button>
                <button id="voice-stop" class="voice-btn" title="Stop">
                    <span class="voice-icon">⏹️</span>
                </button>
                <input type="range" id="voice-volume" min="0" max="1" step="0.1" value="0.8" title="Volume">
                <input type="range" id="voice-speed" min="0.5" max="2" step="0.1" value="0.8" title="Speed">
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', controlsHTML);
        
        // Add CSS styles
        const styles = `
            <style>
                .voice-controls {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: rgba(255, 255, 255, 0.95);
                    border-radius: 15px;
                    padding: 10px;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    z-index: 1000;
                    border: 2px solid #4ecdc4;
                }
                
                .voice-btn {
                    background: #4ecdc4;
                    border: none;
                    border-radius: 50%;
                    width: 40px;
                    height: 40px;
                    cursor: pointer;
                    transition: all 0.2s;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                
                .voice-btn:hover {
                    transform: scale(1.1);
                    background: #45b7b8;
                }
                
                .voice-btn:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                    transform: none;
                }
                
                .voice-icon {
                    font-size: 16px;
                }
                
                #voice-volume, #voice-speed {
                    width: 60px;
                    height: 5px;
                    border-radius: 5px;
                    background: #ddd;
                    outline: none;
                    cursor: pointer;
                }
                
                .listen-btn {
                    background: #ff6b6b;
                    color: white;
                    border: none;
                    border-radius: 15px;
                    padding: 8px 15px;
                    font-size: 0.9em;
                    cursor: pointer;
                    margin: 5px;
                    transition: all 0.2s;
                    font-family: 'Comic Sans MS', cursive;
                }
                
                .listen-btn:hover {
                    transform: scale(1.05);
                    background: #ff5252;
                }
                
                .listen-btn.playing {
                    background: #4ecdc4;
                    animation: pulse 1.5s infinite;
                }
                
                @keyframes pulse {
                    0% { opacity: 1; }
                    50% { opacity: 0.7; }
                    100% { opacity: 1; }
                }
            </style>
        `;
        
        document.head.insertAdjacentHTML('beforeend', styles);
        
        // Add event listeners
        this.setupGlobalControlsEvents();
    }
    
    setupGlobalControlsEvents() {
        const toggleBtn = document.getElementById('voice-toggle');
        const stopBtn = document.getElementById('voice-stop');
        const volumeSlider = document.getElementById('voice-volume');
        const speedSlider = document.getElementById('voice-speed');
        
        toggleBtn.addEventListener('click', () => this.toggle());
        stopBtn.addEventListener('click', () => this.stop());
        
        volumeSlider.addEventListener('input', (e) => {
            this.settings.volume = parseFloat(e.target.value);
        });
        
        speedSlider.addEventListener('input', (e) => {
            this.settings.rate = parseFloat(e.target.value);
        });
    }
    
    updateGlobalControlsUI() {
        const toggleBtn = document.getElementById('voice-toggle');
        const stopBtn = document.getElementById('voice-stop');
        
        if (toggleBtn) {
            if (this.isPlaying) {
                toggleBtn.innerHTML = this.isPaused ? 
                    '<span class="voice-icon">▶️</span>' : 
                    '<span class="voice-icon">⏸️</span>';
                toggleBtn.disabled = false;
            } else {
                toggleBtn.innerHTML = '<span class="voice-icon">🔊</span>';
                toggleBtn.disabled = true;
            }
        }
        
        if (stopBtn) {
            stopBtn.disabled = !this.isPlaying;
        }
    }
    
    // Helper method to add listen buttons to elements
    addListenButton(element, text, options = {}) {
        const button = document.createElement('button');
        button.className = 'listen-btn';
        button.innerHTML = options.icon || '🔊 Listen';
        button.addEventListener('click', () => {
            this.speak(text, options);
            button.classList.add('playing');
            
            // Remove playing class when speech ends
            const originalOnEnd = this.currentUtterance?.onend;
            if (this.currentUtterance) {
                this.currentUtterance.onend = () => {
                    button.classList.remove('playing');
                    if (originalOnEnd) originalOnEnd();
                };
            }
        });
        
        element.appendChild(button);
        return button;
    }
}

// Initialize voice manager when page loads
let voiceManager;
document.addEventListener('DOMContentLoaded', function() {
    voiceManager = new VoiceManager();
    console.log('Voice Manager initialized');
});

// Export for global use
window.voiceManager = voiceManager;