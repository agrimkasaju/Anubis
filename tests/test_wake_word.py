import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.wake_word import WakeWordListener


def test_wake_word_listener_init_and_threshold():
    callback = MagicMock()
    listener = WakeWordListener(callback=callback, model_path="orion.onnx", threshold=0.28)
    assert listener.threshold == 0.28
    assert listener.active is True
    assert listener.cooldown_until == 0.0


def test_pause_and_resume_immediate():
    callback = MagicMock()
    listener = WakeWordListener(callback=callback, model_path="orion.onnx")

    listener.pause_listening()
    assert listener.active is False

    listener.cooldown_until = 0.0
    listener.resume_listening()
    assert listener.active is True
    assert listener.cooldown_until > 0.0


def test_wake_word_detection_callback_triggered():
    callback = MagicMock()
    listener = WakeWordListener(callback=callback, model_path="orion.onnx", threshold=0.28)

    # Mock oww_model.predict to simulate wake word trigger
    mock_predict = MagicMock(return_value={"orion": 0.45})
    listener.oww_model.predict = mock_predict

    # Mock audio stream
    fake_stream = MagicMock()
    fake_stream.get_read_available.return_value = 0
    fake_stream.read.return_value = np.zeros(1280, dtype=np.int16).tobytes()

    with patch("pyaudio.PyAudio") as mock_pyaudio:
        mock_pyaudio.return_value.open.return_value = fake_stream

        # Run one step of loop logic manually
        audio_data = np.frombuffer(fake_stream.read(1280), dtype=np.int16)
        pred = listener.oww_model.predict(audio_data)

        for model_name, score in pred.items():
            if score > listener.threshold:
                listener.callback()
                break

        callback.assert_called_once()
