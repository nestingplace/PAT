# UPDATED TO EXPOSE PRESSED KEY DIRECTLY
from machine import Pin, Timer
import utime

class Keypad:
    def __init__(self, keymap, row_pins, column_pins, num_rows, num_cols):
        self._keymap = keymap
        self._row_pins = [Pin(pin, Pin.IN, Pin.PULL_UP) for pin in row_pins]
        self._column_pins = [Pin(pin, Pin.OUT) for pin in column_pins]
        self._num_rows = num_rows
        self._num_cols = num_cols
        self._prev_key = None
        self._debounce_time = 400
        self._prev_time = 0

        for col_pin in self._column_pins:
            col_pin.value(1)

    def get_key(self):
        for col_index, col_pin in enumerate(self._column_pins):
            col_pin.value(0)
            for row_index, row_pin in enumerate(self._row_pins):
                if not row_pin.value():
                    key = self._keymap[row_index * self._num_cols + col_index]  # ← define key FIRST
                    current_time = utime.ticks_ms()
                    if self._prev_key != key or (self._prev_key == key and utime.ticks_diff(current_time, self._prev_time) > self._debounce_time):
                        self._prev_key = key
                        self._prev_time = current_time
                        col_pin.value(1)
                        return key
            col_pin.value(1)
        return None


    def is_pressed(self, key_to_check):
        for col_index, col_pin in enumerate(self._column_pins):
            col_pin.value(0)
            for row_index, row_pin in enumerate(self._row_pins):
                if not row_pin.value():
                    key = self._keymap[row_index * self._num_cols + col_index]
                    if key == key_to_check:
                        col_pin.value(1)
                        return True
            col_pin.value(1)
        return False

    def set_debounce_time(self, time_ms):
        self._debounce_time = time_ms
