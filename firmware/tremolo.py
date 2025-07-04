import time
import ujson
from machine import Pin, PWM

class TremoloController:
    def __init__(self, pin_num, bpm, display):
        self.pin = Pin(pin_num, Pin.OUT)
        self.pwm = PWM(self.pin)
        self.enabled = False
        self.display = display
        self.bpm = bpm
        self.set_frequency_from_bpm(bpm)
        self.pwm.duty_u16(0)  # OFF BY DEFAULT

    def set_frequency_from_bpm(self, bpm):
        self.bpm = bpm
        base_freq = 4  # 4 Hz @ 120 BPM
        freq = int((bpm / 120) * base_freq)
        freq = max(freq, 10)  # MINIMUM FREQUENCY FOR PWM HARDWARE
        self.pwm.freq(freq)
        if self.enabled:
            self.pwm.duty_u16(32768)  # 50% DITY

    def enable(self):
        self.enabled = True
        self.pwm.duty_u16(32768) # 50% DUTY
        self.display.scroll("TREMOLO ON")

    def disable(self):
        self.enabled = False
        self.pwm.duty_u16(0)  # Off
        self.display.scroll("TREMOLO OFF")

    def toggle(self):
        if self.enabled:
            self.disable()
        else:
            self.enable()