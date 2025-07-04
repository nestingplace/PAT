import machine
import time

class Encoder:
    def __init__(self, clk_pin, dt_pin, sw_pin):
        self.clk = machine.Pin(clk_pin, machine.Pin.IN, machine.Pin.PULL_UP)
        self.dt = machine.Pin(dt_pin, machine.Pin.IN, machine.Pin.PULL_UP)
        self.sw = machine.Pin(sw_pin, machine.Pin.IN, machine.Pin.PULL_UP)

        self.last_state = (self.clk.value() << 1) | self.dt.value()
        self.last_time = time.ticks_ms()

    def get_direction(self):
        state = (self.clk.value() << 1) | self.dt.value()
        now = time.ticks_ms()

        if state != self.last_state and time.ticks_diff(now, self.last_time) > 5:
            self.last_time = now
            transition = (self.last_state << 2) | state
            self.last_state = state

            # Reversed directions to match intended CW = increase
            if transition in (0b0001, 0b0111, 0b1110, 0b1000):
                return -1  # Originally CW, now interpreted as decrease
            elif transition in (0b0010, 0b0100, 0b1101, 0b1011):
                return 1   # Originally CCW, now interpreted as increase

        return 0

    def get_button_press(self):
        if self.sw.value() == 0:
            time.sleep_ms(50)
            if self.sw.value() == 0:
                while self.sw.value() == 0:
                    pass
                return True
        return False
