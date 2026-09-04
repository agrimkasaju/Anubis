import os
import time
import threading
import numpy as np
import sounddevice as sd
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
            self.oww_model = Model(wakeword_model_paths=[os.path.abspath(model_path)])
        else:
            print(f"🐺 [ANUBIS]: Custom model '{model_path}' not found. Loading default built-in models...")
            self.oww_model = Model()

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
        chunk = 1280
        channels = 1
        rate = 16000

        try:
            stream = sd.InputStream(
                samplerate=rate,
                channels=channels,
                dtype="int16",
                blocksize=chunk,
            )
            stream.start()
            print("🐺 [ANUBIS]: Listening for wake-word...")

            while self.running:
                try:
                    data, _overflowed = stream.read(chunk)
                except Exception:
                    time.sleep(0.05)
                    continue

                if not self.active or time.time() < getattr(self, 'cooldown_until', 0.0):
                    continue

                audio_data = np.asarray(data[:, 0], dtype=np.int16)

                # Predict wake-word presence
                self.oww_model.predict(audio_data)

                for model_name, score in self.oww_model.prediction_buffer.items():
                    if score[-1] > 0.05:
                        print(f"🐺 [ANUBIS]: Wake-word detected! ({model_name})")
                        self.callback()
                        time.sleep(1.5)
        except Exception as exc:
            print(f"🐺 [ANUBIS]: Could not open wake-word microphone: {exc}")
        finally:
            if 'stream' in locals():
                stream.close()
