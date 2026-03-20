/**
 * Voice Input Module using Web Speech API
 */

class VoiceManager {
    constructor() {
        this.btn = document.getElementById('voice-btn');
        this.input = document.getElementById('emergency-input');
        this.langSelect = document.getElementById('voice-language');
        this.isRecording = false;
        this.recognition = null;
        
        this.init();
    }

    init() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            console.warn("Speech Recognition API not supported in this browser.");
            this.btn.style.display = 'none';
            this.langSelect.style.display = 'none';
            return;
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        this.recognition.continuous = true;
        this.recognition.interimResults = true;

        this.btn.addEventListener('click', () => this.toggleRecording());
        this.langSelect.addEventListener('change', () => {
            if (this.isRecording) {
                this.stopRecording();
                this.startRecording();
            }
        });

        this.recognition.onresult = (event) => {
            let finalTranscript = '';
            let interimTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                } else {
                    interimTranscript += event.results[i][0].transcript;
                }
            }

            if (finalTranscript) {
                const currentVal = this.input.value;
                this.input.value = currentVal ? currentVal + ' ' + finalTranscript : finalTranscript;
                
                // Trigger input event for character counter
                this.input.dispatchEvent(new Event('input'));
            }
        };

        this.recognition.onerror = (event) => {
            console.error("Speech recognition error:", event.error);
            this.stopRecording();
        };

        this.recognition.onend = () => {
            if (this.isRecording) {
                // Auto-restart if it disconnected but we still want to record
                try {
                    this.recognition.start();
                } catch (e) {
                    this.stopRecording();
                }
            } else {
                this.setIdleState();
            }
        };
    }

    toggleRecording() {
        if (this.isRecording) {
            this.stopRecording();
        } else {
            this.startRecording();
        }
    }

    startRecording() {
        try {
            this.recognition.lang = this.langSelect.value || 'en-IN';
            this.recognition.start();
            this.isRecording = true;
            this.setRecordingState();
        } catch (e) {
            console.error("Could not start recognition", e);
        }
    }

    stopRecording() {
        this.isRecording = false;
        try {
            this.recognition.stop();
        } catch (e) { }
        this.setIdleState();
    }

    setRecordingState() {
        this.btn.classList.add('recording');
        this.btn.innerHTML = '<span class="material-symbols-rounded">stop_circle</span>';
        this.btn.setAttribute('aria-label', 'Stop voice input');
        
        const wrapper = this.input.closest('.textarea-wrapper');
        if (wrapper) wrapper.classList.add('recording');
    }

    setIdleState() {
        this.btn.classList.remove('recording');
        this.btn.innerHTML = '<span class="material-symbols-rounded">mic</span>';
        this.btn.setAttribute('aria-label', 'Start voice input');
        
        const wrapper = this.input.closest('.textarea-wrapper');
        if (wrapper) wrapper.classList.remove('recording');
    }
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    window.voiceManager = new VoiceManager();
});
