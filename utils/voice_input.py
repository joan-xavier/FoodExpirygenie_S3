import tempfile
import numpy as np
import av
import speech_recognition as sr

class AudioProcessor:
    def __init__(self):
        self.audio_frames = []

    def recv_audio(self, frame: av.AudioFrame) -> av.AudioFrame:
        pcm = frame.to_ndarray()
        self.audio_frames.append(pcm)
        return frame

def transcribe_audio(frames, sample_rate=16000):
    if not frames:
        return ""
    audio = np.concatenate(frames, axis=1).flatten().astype(np.int16)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        import wave
        wf = wave.open(f, 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())
        wf.close()
        wav_path = f.name

    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data)
        except Exception as e:
            text = f"Recognition error: {e}"
    return text

# TODO: Implement audio input using an alternative method (e.g., file upload or other library)


