from micropython import const
from machine import Pin
from utime import sleep_us, sleep_ms

TM1637_CMD1 = const(64)
TM1637_CMD2 = const(192)
TM1637_CMD3 = const(128)
TM1637_DSP_ON = const(8)
TM1637_DELAY = const(10)

class TM1637:
    def __init__(self, clk, dio, brightness=7):
        self.clk = clk
        self.dio = dio

        if not 0 <= brightness <= 7:
            raise ValueError("Brightness out of range")
        self._brightness = brightness

        self.clk.init(Pin.OUT, value=0)
        self.dio.init(Pin.OUT, value=0)
        sleep_us(TM1637_DELAY)

        self.top_buffer = [0] * 8     # top row (steps 1–8)
        self.bottom_buffer = [0] * 8  # bottom row (steps 9–16)

        self._write_data_cmd()
        self._write_dsp_ctrl()

    def _start(self):
        self.dio(0)
        sleep_us(TM1637_DELAY)
        self.clk(0)
        sleep_us(TM1637_DELAY)

    def _stop(self):
        self.dio(0)
        sleep_us(TM1637_DELAY)
        self.clk(1)
        sleep_us(TM1637_DELAY)
        self.dio(1)

    def _write_data_cmd(self):
        self._start()
        self._write_byte(TM1637_CMD1)
        self._stop()

    def _write_dsp_ctrl(self):
        self._start()
        self._write_byte(TM1637_CMD3 | TM1637_DSP_ON | self._brightness)
        self._stop()

    def _write_byte(self, b):
        for i in range(8):
            self.dio((b >> i) & 1)
            sleep_us(TM1637_DELAY)
            self.clk(1)
            sleep_us(TM1637_DELAY)
            self.clk(0)
            sleep_us(TM1637_DELAY)
        self.clk(0)
        sleep_us(TM1637_DELAY)
        self.clk(1)
        sleep_us(TM1637_DELAY)
        self.clk(0)
        sleep_us(TM1637_DELAY)

    def brightness(self, val=None):
        if val is None:
            return self._brightness
        if not 0 <= val <= 7:
            raise ValueError("Brightness out of range")
        self._brightness = val
        self._write_data_cmd()
        self._write_dsp_ctrl()

    def write(self, segments, pos=0):
        self._write_data_cmd()
        self._start()
        self._write_byte(TM1637_CMD2 | pos)
        for seg in segments:
            self._write_byte(seg)
        self._stop()
        self._write_dsp_ctrl()

    def encode_char(self, char):
        _SEGMENTS = bytearray(b'\x3F\x06\x5B\x4F\x66\x6D\x7D\x07\x7F\x6F\x77\x7C\x39\x5E\x79\x71\x3D\x76\x06\x1E\x76\x38\x55\x54\x3F\x73\x67\x50\x6D\x78\x3E\x1C\x2A\x76\x6E\x5B\x00\x40\x63')
        o = ord(char)
        if o == 32:
            return _SEGMENTS[36]
        if o == 42:
            return _SEGMENTS[38]
        if o == 45:
            return _SEGMENTS[37]
        if 65 <= o <= 90:
            return _SEGMENTS[o-55]
        if 97 <= o <= 122:
            return _SEGMENTS[o-87]
        if 48 <= o <= 57:
            return _SEGMENTS[o-48]
        raise ValueError("Character out of range: {:d} '{:s}'".format(o, chr(o)))

    def encode_string(self, string):
        return bytearray([self.encode_char(c) for c in string])

    def show(self, string=None):
        if string is not None:
            self.write(self.encode_string(string[:4]))
        else:
            display_buf = [0x00] * 4

            # TOP row: steps 1–8 → segment F (bit 5, left) and B (bit 1, right)
            for i in range(8):
                col = i // 2
                if self.top_buffer[i]:
                    if i % 2 == 0:
                        display_buf[col] |= 0b00100000  # segment F (left top)
                    else:
                        display_buf[col] |= 0b00000010  # segment B (right top)

            # BOTTOM row: steps 9–16 → segment E (bit 4, left) and C (bit 2, right)
            for i in range(8):
                col = i // 2
                if self.bottom_buffer[i]:
                    if i % 2 == 0:
                        display_buf[col] |= 0b00010000  # segment E (left bottom)
                    else:
                        display_buf[col] |= 0b00000100  # segment C (right bottom)

            self.write(display_buf)

    def clear(self):
        self.top_buffer = [0] * 8
        self.bottom_buffer = [0] * 8
        self.show()

    def scroll(self, string, delay=250):
        segments = self.encode_string(string)
        padded = [0x00] * 4 + list(segments) + [0x00] * 4
        for i in range(len(padded) - 3):
            self.write(padded[i:i+4])
            sleep_ms(delay)

    def number(self, num):
        num = max(-999, min(num, 9999))
        string = '{0: >4d}'.format(num)
        self.show(string)

    def set_top(self, col, state):
        if 0 <= col < 8:
            self.top_buffer[col] = 1 if state else 0

    def set_bottom(self, col, state):
        if 0 <= col < 8:
            self.bottom_buffer[col] = 1 if state else 0
