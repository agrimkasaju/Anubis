import os
import time
import threading
import numpy as np
import pyaudio
import openwakeword
from openwakeword.model import Model

class WakeWordListener:
    def __init__(self, callback, model_path="orion.onnx"):
        self.callback = callback
        self.running = False
        self.active = True
        self.cooldown_until = 0.0
        self.thread = None
        self.consecutive_hits = 0

        # Check if custom ONNX model exists; otherwise load default models
        if os.path.exists(model_path):
            print(f"🐺 [ANUBIS]: Loaded custom wake-word model from '{model_path}'")
            # Pass the custom path directly using the internal paths parameter 
            self.oww_model = openwakeword.model.Model(wakeword_model_paths=[os.path.abspath(model_path)])
        else:
            print(f"🐺 [ANUBIS]: Custom model '{model_path}' not found. Loading default built-in models...")
            self.oww_model = openwakeword.model.Model()

    def start(self):
        self.running = True
        self.active = True
        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        self.active = False

    def pause_listening(self):
        """Pauses predictions without destroying the audio stream/buffer."""
        self.active = False

    def resume_listening(self):
        """Resumes predictions and clears stale audio buffers."""
        self.reset()
        self.active = True

    def reset(self):
        """Clear openwakeword prediction buffers and establish a cooldown."""
        if hasattr(self, 'oww_model') and hasattr(self.oww_model, 'prediction_buffer'):
            for k in self.oww_model.prediction_buffer:
                try:
                    self.oww_model.prediction_buffer[k].clear()
                except Exception:
                    pass
        self.cooldown_until = time.time() + 2.0

    def process_prediction(self, predictions):
        # Increase threshold to 0.65 to prevent false triggers
        THRESHOLD = 0.50
        
        # Check scores for your target model(s)
        orion_score = predictions.get("orion", 0.0)

        if orion_score > THRESHOLD:
            self.consecutive_hits += 1
            # Only trigger when detected across consecutive audio frames[cite: 4]
            if self.consecutive_hits >= 2:
                print(f"🐺 [WakeWord]: Confirmed detection! (Score: {max(orion_score) if hasattr(orion_score, '__iter__') else orion_score:.2f})")
                self.consecutive_hits = 0
                self.callback()
        else:
            self.consecutive_hits = 0

    def _listen_loop(self):
            CHUNK = 1280
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 16000
    
            audio = pyaudio.PyAudio()
            stream = audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK
            )
    
            print("🐺 [ANUBIS]: Listening for wake-word...")
    
            while self.running:
                if not self.active or time.time() < getattr(self, 'cooldown_until', 0.0):
                    time.sleep(0.05)
                    continue
    
                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                except Exception:
                    continue
    
                audio_data = np.frombuffer(data, dtype=np.int16)
    
                # Predict wake-word presence
                prediction = self.oww_model.predict(audio_data)
    
                for model_name, score in self.oww_model.prediction_buffer.items():
                    if score[-1] > 0.05:
                        print(f"🐺 [ANUBIS]: Wake-word detected! ({model_name})")
                        self.callback()
                        time.sleep(1.5)
    
            stream.stop_stream()
            stream.close()
            audio.terminate()
