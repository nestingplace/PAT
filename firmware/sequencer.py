import uasyncio as asyncio
import time
import ujson
# from tremolo2 import TremoloController
from machine import Timer, Pin
from program_io import save_program
from synthesizer27 import Synthesizer

class Sequencer:
    def __init__(self, encoder, display, audio, keypad, navpad, midi_uart, program_data):
        self.encoder = encoder
        self.display = display
        self.audio = audio
        self.keypad = keypad
        self.navpad = navpad
        # self.tremolo = tremolo
        self.midi_uart = midi_uart
        self.program_data = program_data
        self.sequence = self.program_data.get("sequence", [None] * 16)
        self.running = False
        self.folder = self.program_data.get("folder", 1)
        self.mode = "SEQ"
        self.bpm = self.program_data.get("bpm", 80)
        self.blink_state = True
        self.dual_mode = False
        self.sync_pin = Pin(20, Pin.OUT)
        self.timer = Timer(-1)
        self.synth = Synthesizer(program_data=program_data)
        self.current_step = 0
        self.current_key = None
        self.last_encoder_check = 0
        self.last_drawn_step = None
        self.last_blink_time = time.ticks_ms()
        self.last_toggle = 0
        self.last_key_event = None
        self.last_key_time = 0
        self.note_map = {
            '1': 261.63, '2': 293.66, '3': 329.63, 'A': 349.23,
            '4': 392.00, '5': 440.00, '6': 493.88, 'B': 523.25,
            '7': 554.37, '8': 587.33, '9': 622.25, 'C': 659.25,
            '10': 698.46, '11': 739.99, '12': 783.99, 'D': 830.61
        }
        self.keymap = {
            '1': 1, '2': 2, '3': 3, 'A': 4,
            '4': 5, '5': 6, '6': 7, 'B': 8,
            '7': 9, '8': 10, '9': 11, 'C': 12,
            '10': 13, '11': 14, '12': 15, 'D': 16
        }

    def set_folder(self, folder_number):
        self.sequence = self.program_data.get("sequence", [None] * 16)
        self.folder = folder_number

    def update_display(self):
        self.display.clear()
        for i, sample in enumerate(self.sequence):
            if sample is not None:
                row, col = self.map_step_to_row_col(i)
                if row == 0:
                    self.display.set_top(col, 1)
                else:
                    self.display.set_bottom(col, 1)

        row, col = self.map_step_to_row_col(self.current_step)
        if self.running:
            if row == 0:
                self.display.set_top(col, 1)
            else:
                self.display.set_bottom(col, 1)
        elif not self.dual_mode and self.sequence[self.current_step] is None:
            if row == 0:
                self.display.set_top(col, 1 if self.blink_state else 0)
            else:
                self.display.set_bottom(col, 1 if self.blink_state else 0)

        self.display.show()

    def update_idle_visual(self):
        if self.running or self.dual_mode:
            return
        now = time.ticks_ms()
        if (self.blink_state and time.ticks_diff(now, self.last_blink_time) >= 750) or \
           (not self.blink_state and time.ticks_diff(now, self.last_blink_time) >= 250):
            self.blink_state = not self.blink_state
            self.last_blink_time = now
            self.update_display()

    async def toggle_dual_mode(self):
        self.dual_mode = not self.dual_mode
        self.last_toggle = time.ticks_ms()
        self.blink_state = not self.dual_mode
        if not self.dual_mode:
            self.synth.stop_note()
            self.current_key = None
        self.update_display()

    async def assign_sample(self, key):
        key_str = str(key).strip()
        if key_str not in self.keymap:
            return  # IGNORE GHOST KEYS
        sample_id = self.keymap[key_str]
        self.sequence[self.current_step] = sample_id
        save_program(self.program_data)
        await self.audio.play(self.folder, sample_id)
        self.update_display()

    async def run_sequence(self, _):
        interval = 60 / (self.bpm * 4)
        self.running = True
        self.current_step = 0

        if self.program_data.get("midi"):
            self.start_midi_clock()
        elif self.program_data.get("sync"):
            self.start_sync_pulse()

        while self.running:
            step_val = self.sequence[self.current_step]
            if step_val is not None:
                await self.audio.play(self.folder, step_val)

            self.update_display()
            self.last_drawn_step = self.current_step
            start_time = time.ticks_ms()

            while time.ticks_diff(time.ticks_ms(), start_time) < int(interval * 1000):
                key_event = self.keypad.get_key()
                nav_event = self.navpad.get_key()
                now = time.ticks_ms()

                if nav_event:
                    if nav_event == 'E':
                        self.running = False
                        break
                    elif nav_event == '19':
                        self.clear_entire_pattern()
                        break
                    elif nav_event == '18':
                        self.clear_step()
                        break
                    elif nav_event == '17' and time.ticks_diff(now, self.last_toggle) > 250:
                        await self.toggle_dual_mode()

                elif key_event:
                    if key_event != self.last_key_event or time.ticks_diff(now, self.last_key_time) > 400:
                        self.last_key_event = key_event
                        self.last_key_time = now
                        if self.dual_mode:
                            if key_event in self.note_map:
                                if key_event != self.current_key:
                                    self.synth.stop_note()
                                    self.current_key = key_event
                                    self.synth.start_note(self.note_map[key_event])
                        else:
                            await self.assign_sample(key_event)

                if self.dual_mode and self.current_key and not self.keypad.is_pressed(self.current_key):
                    self.synth.stop_note()
                    self.current_key = None

                direction = self.encoder.get_direction()
                if self.dual_mode and direction:
                    self.synth.update_control(direction)

                if self.encoder.get_button_press():
                    self.stop_sequence()
                    return

                time.sleep_ms(5)

            self.current_step = (self.current_step + 1) % 16

        if self.program_data.get("midi"):
            self.stop_midi_clock()
        elif self.program_data.get("sync"):
            self.stop_sync_pulse()

    def stop_sequence(self):
        self.running = False
        self.blink_state = True
        self.last_blink_time = time.ticks_ms()

        if self.last_drawn_step is not None:
            row, col = self.map_step_to_row_col(self.last_drawn_step)
            if self.sequence[self.last_drawn_step] is None:
                if row == 0:
                    self.display.set_top(col, 0)
                else:
                    self.display.set_bottom(col, 0)

        self.update_display()

    def map_step_to_row_col(self, step):
        if step < 8:
            return 0, step
        else:
            return 1, step - 8

    def clear_step(self):
        self.program_data["sequence"][self.current_step] = None
        save_program(self.program_data)
        self.update_display()

    def clear_entire_pattern(self):
        self.program_data["sequence"] = [None] * 16
        save_program(self.program_data)
        self.sequence = self.program_data["sequence"]
        self.display.scroll("CLEAR")
        self.update_display()

    async def handle_dual_mode_inputs(self):
        if not self.running and self.dual_mode:
            key = self.keypad.get_key()

            # KEY PRESSED != HELD KEY
            if key in self.note_map:
                if key != self.current_key:
                    self.synth.stop_note()
                    self.current_key = key
                    self.synth.start_note(self.note_map[key])

            elif self.current_key:
                # CHECK FOR RELEASE OF HELD KEY
                if not self.keypad.is_pressed(self.current_key):
                    self.synth.stop_note()
                    self.current_key = None

            # IF HELD KEY & NO NOTE RUNNING, LAUNCH
            if self.current_key and not self.synth.running:
                self.synth.start_note(self.note_map[self.current_key])

            # KY040 INPUT
            direction = self.encoder.get_direction()
            if direction and time.ticks_diff(time.ticks_ms(), self.last_encoder_check) > 100:
                self.synth.update_control(direction)
                self.last_encoder_check = time.ticks_ms()