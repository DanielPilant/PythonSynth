"""
Polyphonic sine synth - one chromatic octave, C4 to B4.

Piano-style key layout (hold keys, chords work):

    w e   t y u          <- black keys  (C# D#   F# G# A#)
   a s d f g h j         <- white keys  (C  D  E  F  G  A  B)

Press Esc to quit.

pip install sounddevice keyboard
"""
import numpy as np
import sounddevice as sd
import keyboard

SAMPLE_RATE = 44100
BLOCK_SIZE = 256          # samples per buffer
AMPLITUDE = 0.5           # master gain applied to the summed mix

ATTACK = 0.01             # seconds to fade in  -> kills the start click
RELEASE = 0.01            # seconds to fade out -> kills the stop click

# how much the envelope gain moves per sample
attack_step = 1.0 / (ATTACK * SAMPLE_RATE)
release_step = 1.0 / (RELEASE * SAMPLE_RATE)

# Key -> MIDI note number, in piano layout. C4 = MIDI 60 ... B4 = MIDI 71.
KEY_TO_MIDI = {
    "a": 60,  # C4
    "w": 61,  # C#4
    "s": 62,  # D4
    "e": 63,  # D#4
    "d": 64,  # E4
    "f": 65,  # F4
    "t": 66,  # F#4
    "g": 67,  # G4
    "y": 68,  # G#4
    "h": 69,  # A4
    "u": 70,  # A#4
    "j": 71,  # B4
}


def midi_to_freq(n):
    """Equal-temperament frequency of MIDI note n (A4 = 69 = 440 Hz)."""
    return 440.0 * 2.0 ** ((n - 69) / 12.0)


class Voice:
    """One oscillator + its own envelope. Keeps phase/gain across buffers."""

    def __init__(self, freq):
        self.phase_inc = 2 * np.pi * freq / SAMPLE_RATE
        self.phase = 0.0
        self.gain = 0.0
        self.note_on = False

    def is_silent(self):
        return not self.note_on and self.gain <= 0.0

    def render(self, frames):
        # Oscillator: continue the phase from the last buffer (no click between buffers)
        phases = self.phase + self.phase_inc * np.arange(1, frames + 1)
        sine = np.sin(phases)
        self.phase = phases[-1] % (2 * np.pi)

        # Envelope: ramp gain toward 1.0 (held) or 0.0 (released), per sample
        if self.note_on:
            env = np.clip(self.gain + attack_step * np.arange(1, frames + 1), 0.0, 1.0)
        else:
            env = np.clip(self.gain - release_step * np.arange(1, frames + 1), 0.0, 1.0)
        self.gain = env[-1]

        return sine * env


# One Voice instance per key, built once at startup.
voices = {key: Voice(midi_to_freq(midi)) for key, midi in KEY_TO_MIDI.items()}


def callback(outdata, frames, time, status):
    if status:
        print(status)

    # Polyphony = sum the active voices. Silent voices are skipped (cheap).
    mix = np.zeros(frames)
    for v in voices.values():
        if not v.is_silent():
            mix += v.render(frames)

    # Master gain, then hard-limit to [-1, 1] as a safety net for big chords.
    outdata[:, 0] = np.clip(mix * AMPLITUDE, -1.0, 1.0).astype(np.float32)


def main():
    for key, voice in voices.items():
        keyboard.on_press_key(key,   lambda _, v=voice: setattr(v, "note_on", True))
        keyboard.on_release_key(key, lambda _, v=voice: setattr(v, "note_on", False))

    with sd.OutputStream(
        samplerate=SAMPLE_RATE,
        blocksize=BLOCK_SIZE,
        latency="low",
        channels=1,
        dtype="float32",
        callback=callback,
    ):
        print("Play: a w s e d f t g y h u j   (C4 -> B4).  Esc to quit.")
        keyboard.wait("esc")


if __name__ == "__main__":
    main()
