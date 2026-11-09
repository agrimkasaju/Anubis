import os
import time
import threading
import numpy as np
import pyaudio
import openwakeword
from openwakeword.model import Model

class WakeWordListener:
    def __init__(self, callback, model_path="orion.onnx", threshold=0.28):
        self.callback = callback
        self.threshold = threshold
        self.running = False
        self.active = True
        self.cooldown_until = 0.0
        self.thread = None

        if not os.path.isabs(model_path):
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            candidate = os.path.join(base_dir, model_path)
            if os.path.exists(candidate):
                model_path = candidate

        # Check if custom ONNX model exists; otherwise load default models
        if os.path.exists(model_path):
            print(f"🐺 [ANUBIS]: Loaded custom wake-word model from '{model_path}' (threshold: {self.threshold})")
            framework = "onnx" if model_path.endswith(".onnx") else "tflite"
            self.oww_model = openwakeword.model.Model(
                wakeword_models=[os.path.abspath(model_path)],
                inference_framework=framework
            )
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
        """Resumes predictions with cleared buffers to prevent pop-up bounces."""
        self.reset()
        self.cooldown_until = max(self.cooldown_until, time.time() + 0.8)
        self.active = True

    def reset(self):
        """Reset internal model buffers to purge previous wake phrase."""
        if hasattr(self, 'oww_model'):
            try:
                self.oww_model.reset()
            except Exception:
                pass

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
            if not self.active:
                time.sleep(0.05)
                continue

            # Flush any stale backlogged frames so processing is strictly real-time
            try:
                avail = stream.get_read_available()
                if avail > CHUNK:
                    stream.read(avail, exception_on_overflow=False)
            except Exception:
                pass

            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
            except Exception:
                continue

            if time.time() < self.cooldown_until:
                continue

            audio_data = np.frombuffer(data, dtype=np.int16)

            # Predict wake-word presence
            prediction = self.oww_model.predict(audio_data)

            for model_name, score in prediction.items():
                if score > self.threshold:
                    print(f"🐺 [ANUBIS]: Wake-word detected! ({model_name}: {score:.2f})")
                    self.cooldown_until = time.time() + 1.5
                    self.reset()
                    self.callback()
                    break

        try:
            stream.stop_stream()
            stream.close()
            audio.terminate()
        except Exception:
            pass
