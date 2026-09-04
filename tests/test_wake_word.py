import numpy as np

from core import wake_word


def test_wake_word_uses_sounddevice(monkeypatch):
    listener = wake_word.WakeWordListener.__new__(wake_word.WakeWordListener)
    listener.running = True
    listener.active = True
    listener.cooldown_until = 0.0
    listener.callback = lambda: None

    class FakeModel:
        prediction_buffer = {"orion": [0.0]}

        def predict(self, audio):
            assert audio.shape == (1280,)
            assert audio.dtype == np.int16
            listener.running = False

    class FakeStream:
        def __init__(self, **kwargs):
            assert kwargs == {
                "samplerate": 16000,
                "channels": 1,
                "dtype": "int16",
                "blocksize": 1280,
            }

        def start(self):
            pass

        def read(self, frames):
            assert frames == 1280
            return np.zeros((frames, 1), dtype=np.int16), False

        def stop(self):
            pass

        def close(self):
            pass

    listener.oww_model = FakeModel()
    monkeypatch.setattr(wake_word.sd, "InputStream", FakeStream)

    listener._listen_loop()
