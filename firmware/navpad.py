from machine import Pin
import utime

class Navpad:
    def __init__(self, keymap, column_pins, debounce_time=200):
        self._keymap = keymap
        self._pins = [Pin(pin, Pin.IN, Pin.PULL_UP) for pin in column_pins]
        self._debounce_time = debounce_time
        self._last_pressed = None
        self._last_time = 0

    def get_key(self):
        current_time = utime.ticks_ms()
        for index, pin in enumerate(self._pins):
            if not pin.value():  # ACTIVE LOW
                if self._last_pressed != index or utime.ticks_diff(current_time, self._last_time) > self._debounce_time:
                    self._last_pressed = index
                    self._last_time = current_time
                    return self._keymap[index]
        return None

    def is_pressed(self, key_to_check):
        if key_to_check in self._keymap:
            index = self._keymap.index(key_to_check)
            return not self._pins[index].value()
        return False