from machine import PWM, Pin
import math
from program_io import save_program
import _thread
import micropython
import time

class Synthesizer:
    def __init__(self, pwm_pin=15, program_data=None, sample_rate=20000):
        self.program_data = program_data
        self.sample_rate = sample_rate
        self.pwm = PWM(Pin(pwm_pin))
        self.pwm.freq(sample_rate)
        self.freq = 440
        self.running = False
        self.thread_lock = False
        self.phase_acc = 0
        self.phase_inc = 0
        self.table_size = 256
        self.octave_shift = 0
        self.volume = 0.5

        if program_data:
            self.waveform = program_data.get("waveform", "SIN")
            self.control = program_data.get("control", "DISABLED")
            self.control_value = program_data.get("control_value", 0)
            self.octave_shift = program_data.get("octave_shift", 0)
            
            # WRITE MISSING KEYS TO DEFAULT
            if "waveform" not in program_data:
                program_data["waveform"] = self.waveform
            if "control" not in program_data:
                program_data["control"] = self.control
            if "control_value" not in program_data:
                program_data["control_value"] = self.control_value
        else:
            self.waveform = "SIN"
            self.control = "DISABLED"
            self.control_value = 0

        self.current_table = self.generate_table(self.waveform)

    def _noop(self, _):
        pass

    def generate_table(self, waveform_type):
        table = []
        for i in range(self.table_size):
            phase = 2 * math.pi * i / self.table_size

            if waveform_type == "SIN":
                value = (math.sin(phase) + 1) / 2
                weight = 1.0  # No harmonic reduction needed
            elif waveform_type == "SQUARE":
                value = 1.0 if i < self.table_size / 2 else 0.0
                weight = (1 - (i / self.table_size)) ** 2
            elif waveform_type == "TRIANGLE":
                value = 2 * abs(2 * (i / self.table_size) - 1)
                weight = 1.0  # Already smooth
            elif waveform_type == "SAWTOOTH":
                value = i / self.table_size
                weight = (1 - (i / self.table_size)) ** 2
            else:
                value = (math.sin(phase) + 1) / 2
                weight = 1.0

            table.append(int(value * 65535 * weight))
        return table

    def set_waveform(self, waveform_type):
        self.waveform = waveform_type
        self.current_table = self.generate_table(waveform_type)
        if self.program_data:
            self.program_data["waveform"] = waveform_type

    def set_control_target(self, target):
        self.control = target
        if self.program_data:
            self.program_data["control"] = target
        if target == "DISABLED":
            self.control_value = 0

    def update_control(self, delta):
        self.control_value = max(1, min(100, self.control_value + delta))
        if self.program_data:
            self.program_data["control_value"] = self.control_value

    def octave_up(self):
        if self.octave_shift < 3:
            self.octave_shift += 1
            if self.program_data:
                self.program_data["octave_shift"] = self.octave_shift
                save_program(self.program_data)

    def octave_down(self):
        if self.octave_shift > -3:
            self.octave_shift -= 1
            if self.program_data:
                self.program_data["octave_shift"] = self.octave_shift
                save_program(self.program_data)

    def start_note(self, freq):
        try:
            if not self.thread_lock and not self.running:
                self.freq = freq * (2 ** self.octave_shift)
                self.running = True
                _thread.start_new_thread(self._play_note, ())
                time.sleep_ms(1)
        except Exception as e:
            print("Synth thread launch failed:", e)

    def _play_note(self):
        self.thread_lock = True
        start_time = time.ticks_ms()
        envelope_phase = 0
        filter_phase = 0
        bend_phase = 0
        bend_max = 200
        sweep_max = 200
        attack = max(1, int(self.control_value / 4))

        while self.running:
            micropython.schedule(self._noop, 0)
            self.phase_inc = self.freq * self.table_size / self.sample_rate
            self.phase_acc = (self.phase_acc + self.phase_inc) % self.table_size
            index = int(self.phase_acc) % self.table_size
            sample = self.current_table[index]

            # HARMONIC WEIGHT
            # weight = (1 - (index / self.table_size)) ** 2
            # sample = int(sample * weight)

# CONTROL MODES
            
            # CUTOFF ENVELOPE
            if self.control == "CUTOFF":
                cutoff_index = int((self.freq / self.sample_rate) * self.control_value * self.table_size)
                smooth_factor = 0.8  # 80% reduction beyond cutoff
                if index > cutoff_index:
                    sample = int(sample * smooth_factor)

            # ASDR : ATTACK FADE-IN
            if self.control == "ASDR":
                amp = min(1.0, envelope_phase / attack)
                sample = int(sample * amp)
                
            #ASDR : WAVEFORM
            elif self.control == "ASDR_WAVE":
                cycle = (envelope_phase / self.sample_rate)
                envelope = min(1.0, (1 - abs(math.sin(cycle * math.pi))) * (self.control_value / 65535))
                sample = int(sample * envelope)
        
            # FILTER SWEEP
            elif self.control == "FILTER SWEEP":
                sweep_max = max(1, int(self.sample_rate / self.freq))  # one sweep cycle per waveform cycle
                sweep_ratio = (math.sin(2 * math.pi * (filter_phase / sweep_max)) + 1) / 2
                mod = int(self.control_value * sweep_ratio)
                sample = int(sample * (mod / 100.0))
                filter_phase = (filter_phase + 1) % sweep_max

            # FILTER MOD
            if self.control == "FILTER MOD":
                mod = math.sin(time.ticks_ms() / 50.0)
                depth = self.control_value / 32767.0
                freq_mod = self.freq * (1.0 + depth * mod * 0.1)
                self.phase_inc = int((freq_mod * self.table_size) / self.sample_rate * (1 << 16))

            # PITCH BEND
            if self.control == "PITCH BEND":
                semitone_range = 2
                bend = (self.control_value / 32767.0 - 0.5) * 2 * semitone_range
                bend_factor = 2 ** (bend / 12.0)
                self.phase_inc = int((self.freq * bend_factor * self.table_size) / self.sample_rate * (1 << 16))

            sample = int(sample * self.volume)
            sample = max(0, min(65535, sample))
            self.pwm.duty_u16(sample)
            time.sleep_us(int(1_000_000 / self.sample_rate))

        self.running = False
        self.thread_lock = False
        self.pwm.duty_u16(0)

    def stop_note(self):
        self.running = False
        while self.thread_lock:
            time.sleep_ms(1)
        self.pwm.duty_u16(0)