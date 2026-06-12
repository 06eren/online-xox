import wave
import struct
import math
import os

def generate_tone(file_name, freqs, duration, volume=0.5, decay=True):
    sample_rate = 44100.0
    num_samples = int(duration * sample_rate)
    
    with wave.open(file_name, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        for i in range(num_samples):
            t = float(i) / sample_rate
            value = 0.0
            
            if isinstance(freqs, list):
                for f, st, dur in freqs:
                    if st <= t < st + dur:
                        local_t = t - st
                        env = math.exp(-5 * local_t) if decay else 1.0
                        value += math.sin(2.0 * math.pi * f * local_t) * env
            else:
                env = math.exp(-5 * t) if decay else 1.0
                value = math.sin(2.0 * math.pi * freqs * t) * env
                value += 0.3 * math.sin(2.0 * math.pi * (freqs / 2) * t) * env
                
            master_env = 1.0
            if i < 200:
                master_env = i / 200.0
            elif i > num_samples - 200:
                master_env = (num_samples - i) / 200.0
                
            packed_value = struct.pack('h', int(value * volume * master_env * 16000.0))
            wav_file.writeframes(packed_value)

def sesleri_hazirla():
    generate_tone("click.wav", 1000, 0.05, volume=0.3, decay=True)
    generate_tone("place_x.wav", 440, 0.15, volume=0.4, decay=True)
    generate_tone("place_o.wav", 523.25, 0.15, volume=0.4, decay=True)
    
    melody_win = [
        (523.25, 0.0, 0.15),
        (659.25, 0.15, 0.15),
        (783.99, 0.3, 0.15),
        (1046.50, 0.45, 0.4)
    ]
    generate_tone("win.wav", melody_win, 0.85, volume=0.4)
    
    melody_lose = [
        (392.0, 0.0, 0.3),
        (370.0, 0.3, 0.3),
        (349.0, 0.6, 0.3),
        (330.0, 0.9, 0.6)
    ]
    generate_tone("lose.wav", melody_lose, 1.5, volume=0.4)

if __name__ == "__main__":
    sesleri_hazirla()
