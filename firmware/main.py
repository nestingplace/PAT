# STANDARD LIBRARIES
import uasyncio as asyncio
import time
import ujson
from machine import Pin, UART

# PERIPHERAL DRIVERS
from dfplayer import DFPlayer
from keypad import Keypad
from navpad import Navpad
from encoder import Encoder
from tm1637 import TM1637

# CUSTOM OBJECTS
from sequencer import Sequencer
from tremolo import TremoloController
from synthesizer import Synthesizer

# DRIVER INITIALIZATION
df = DFPlayer(uart_id=0, tx_pin_id=0, rx_pin_id=1)
df.volume(100)

midi_uart = UART(1, baudrate=31250, tx=Pin(20))

tm_display = TM1637(clk=Pin(5), dio=Pin(4))

A_ROWS = 4
A_COLS = 4
A_ROW_PINS = [13, 12, 11, 10]
A_COLUMN_PINS = [9, 8, 7, 6]
A_KEYMAP = ['1', '2', '3', 'A',
          '5', '6', '7', 'B',
          '9', '10', '11', 'C',
          '13', '14', '15', 'D']

keypad = Keypad(A_KEYMAP, A_ROW_PINS, A_COLUMN_PINS, A_ROWS, A_COLS)
keypad.set_debounce_time(200)

B_PINS = [19, 18, 17, 16]
B_KEYMAP = ['17', '18', '19', 'E']

navpad = Navpad(B_KEYMAP, B_PINS)

tremolo = TremoloController(pin_num=19, bpm=80, display=tm_display)

encoder = Encoder(2, 3, 22)

programs = ["P1", "P2", "P3", "P4"]
current_program_index = 0

# BOOT SCREEN

tm_display.scroll("Hello Hello Hello Hello")

# HANDLE PROGRAM DATA [JSON]
from program_io import load_program, save_program

def load_program(program_name):  # Legacy definition replaced
    folder_number = int(program_name[1:])
    try:
        with open(f"{program_name}.json", "r") as f:
            data = ujson.load(f)
    except:
        data = {}
    return {
        "program": program_name,
        "folder": folder_number,
        "bank":data.get("bank",1),
        "bpm": data.get("bpm", 80),
        "waveform": data.get("waveform", "SIN"),
        "control": data.get("control", "DISABLED"),
        "control_value": data.get("control_value", 0),
        "sequence": data.get("sequence", [None] * 16),
        "midi": data.get("midi", False),
        "sync": data.get("sync", False)
    }

def save_program(program_data):
    name = program_data.get("program")
    if not name:
        folder = program_data.get("folder", 1)
        name = f"P{folder}"
        program_data["program"] = name
    with open(f"{name}.json", "w") as f:
        ujson.dump(program_data, f)
        
def display_program(name):
    tm_display.show('    ')
    tm_display.show(name)

def change_bank(program_data, toggle):
    bank = program_data.get("bank", 1)
    if toggle:
        bank = 1 if bank >= 4 else bank + 1
    else:
        bank = 4 if bank <= 1 else bank - 1
    program_data["bank"] = bank
    save_program(program_data)
    
# DISPLAY MAP

def display_mode(mode):
    tm_display.show('    ')
    
    # PROGRAM SUB-MENU
    if mode == "SELECT":
        tm_display.show("SEL")
    elif mode == "SAMPLE":
        tm_display.show("SAMP")
    elif mode == "SYNTH":
        tm_display.show("SYNT")
    elif mode == "SEQ":
        tm_display.show("SEQ")
    elif mode == "CONFIGURE":
    
    # CONFIGURATION MENU
        tm_display.show("CNFG")
    elif mode == "BACK":
        tm_display.show("BACK")
    elif mode == "BPM":
        tm_display.show("BPM")
    elif mode == "WAVE":
    
    # WAVEFORMS
        tm_display.show("WAVE")
    elif mode == "SIN":
        tm_display.show("SIN")
    elif mode == "TRI":
        tm_display.show("TRI")
    elif mode == "SAW":
        tm_display.show("SAW")
    elif mode == "SQR":
        tm_display.show("SQR")
    
    # CONTROL MODES
    elif mode == "CTRL":
        tm_display.show("CTRL")
    elif mode == "DISABLED":
        tm_display.show("DSBL")
    elif mode == "CUTOFF":
        tm_display.show("CUT")
    elif mode == "ASDR":
        tm_display.show("FIN")
    elif mode == "ASDR_WAVE":
        tm_display.show("ASDR")
    elif mode == "FILTER MOD":
        tm_display.show("FMOD")
    elif mode == "FILTER SWEEP":
        tm_display.show("FSWP")
    elif mode == "PITCH BEND":
        tm_display.show("PBND")
    elif mode == "ON":
        tm_display.show("ON")
    elif mode == "OFF":
        tm_display.show("OFF")
        
    # MIDI / SYNC
    elif mode == "MIDI":
        tm_display.show("MIDI")
    elif mode == "MIDI ON":
        tm_display.show("ON")
    elif mode == "MIDI OFF":
        tm_display.show("OFF")
    elif mode == "SYNC":
        tm_display.show("SYNC")
    elif mode == "SYNC ON":
        tm_display.show("ON")
    elif mode == "SYNC OFF":
        tm_display.show("OFF")

running_program = False
sequencer_global = None  # GLOBAL SEQUENCER REFERENCE

# SYNTH MODE [PWM/THREADING]

async def synth_mode(program_data):
    display_mode("SYNTH")
    synth = Synthesizer(pwm_pin=15, program_data=program_data)

    note_map = {
        '1': 261.63, '2': 293.66, '3': 329.63, 'A': 349.23,
        '4': 392.00, '5': 440.00, '6': 493.88, 'B': 523.25,
        '7': 554.37, '8': 587.33, '9': 622.25, 'C': 659.25,
        '10': 698.46, '11': 739.99, '12': 783.99, 'D': 830.61
    }

    current_key = None
    while True:
        key = keypad.get_key()
        nav = navpad.get_key()

        if nav:
            if nav == 'E':
                synth.octave_up()
            elif nav == '19':
                synth.octave_down()
            # elif nav == '18':
            # elif nav == '17':

        if key in note_map:
            if key != current_key:
                    synth.stop_note()
                    current_key = key
                    synth.start_note(note_map[key])
        else:
            # NO KEY DETECTED, CHECKS FOR RELEASE OF MOST RECENT KEY
            if current_key and not keypad.is_pressed(current_key):
                synth.stop_note()
                current_key = None
       
        direction = encoder.get_direction()
        if direction:
            synth.update_control(direction)

        if encoder.get_button_press():
            synth.stop_note()
            return

        await asyncio.sleep_ms(10)

# SAMPLE MODE [DFPLAYER]

async def sample_mode(folder, program_data):
    global running_program
    running_program = True
    
    SAMPLE_KEYMAP = {
    '1': 1,  '2': 2,  '3': 3,  'A': 4,
    '5': 5,  '6': 6,  '7': 7,  'B': 8,
    '9': 9,  '10': 10, '11': 11, 'C': 12,
    '13': 13, '14': 14, '15': 15, 'D': 16
    }
    
    tm_display.scroll(f"B{program_data['bank']}")
    display_mode("SAMPLE")
    
    while running_program:
        
        key = keypad.get_key()
        nav = navpad.get_key()

        # KEYPAD
        if key in SAMPLE_KEYMAP:
            key_num = SAMPLE_KEYMAP[key]
            sample_offset = (program_data["bank"] - 1) * 16
            sample = key_num + sample_offset
            await df.play(folder, sample)
            
            # DEBUG
            print(f"Key {key} → Sample {sample}")

        # NAVPAD
        if nav:
            if nav == 'E':
                change_bank(program_data, toggle=True)
                tm_display.scroll(f"B{program_data['bank']}")
                display_mode("SAMPLE")
            elif nav == '19':
                change_bank(program_data, toggle=False)
                tm_display.scroll(f"B{program_data['bank']}")
                display_mode("SAMPLE")
                
            # elif nav == '18':
            # elif nav == '17':

        if encoder.get_button_press():
            running_program = False

# PROGRAM SUB-MENU

async def launch_program(program_index):
    global running_program, sequencer_global
    folder = program_index + 1
    program_data = load_program(programs[program_index])
    program_data["folder"] = folder
    submenu_index = 0
    submenu_options = ["SELECT", "SAMPLE", "SYNTH", "SEQ", "CONFIGURE"]
    last_time = time.ticks_ms()
    last_dir = 0

    if "bpm" not in program_data:
        program_data["bpm"] = 80
    if "bank" not in program_data:
        program_data["bank"] = 1

    while True:
        display_mode(submenu_options[submenu_index])
        direction = encoder.get_direction()
        now = time.ticks_ms()

        if direction != 0:
            if direction != last_dir or time.ticks_diff(now, last_time) > 200:
                submenu_index = (submenu_index + direction) % len(submenu_options)
                display_mode(submenu_options[submenu_index])
                last_dir = direction
                last_time = now

        if encoder.get_button_press():
            mode = submenu_options[submenu_index]

            if mode == "SELECT":
                return

            elif mode == "SAMPLE":
                await sample_mode(folder, program_data)

            elif mode == "SYNTH":
                await synth_mode(program_data)

            elif mode == "SEQ":
                display_mode("SEQ")
                tm_display.show('    ')
                sequencer = Sequencer(encoder, tm_display, df, keypad, navpad, midi_uart, program_data)
                sequencer.set_folder(folder)
                sequencer.mode = "SEQ"
                sequencer.update_display()
                sequencer_global = sequencer
            
                keypad._prev_key = None
                
                while True:
                    direction = encoder.get_direction()
                    now = time.ticks_ms()

                    # BLOCK BLINKING CURSOR : DUAL MODE
                    if not sequencer.dual_mode and direction != 0:
                        if direction != last_dir or time.ticks_diff(now, last_time) > 200:
                            sequencer.current_step = (sequencer.current_step + direction) % 16
                            sequencer.update_display()
                            sequencer.blink_state = True
                            sequencer.last_blink_time = now
                            last_dir = direction
                            last_time = now

                    key_event = keypad.get_key()
                    nav_event = navpad.get_key()

                    if key_event:
                        
                        if sequencer.dual_mode and not sequencer.running:
                            # KEY HANDLING : DUAL MODE [IDLE]
                            sequencer.current_key = key_event
                            await sequencer.handle_dual_mode_inputs()

                        elif not sequencer.dual_mode :
                            await sequencer.assign_sample(key_event)
                            
                    elif nav_event:
                        
                        if nav_event == 'E':
                            
                            if not sequencer.running:
                                await sequencer.run_sequence(None)
                            else:
                                sequencer.stop_sequence()
                                
                        elif nav_event == '19':
                            sequencer.clear_entire_pattern()
                            
                        elif nav_event == '18':
                            sequencer.clear_step()
                            
                        elif nav_event == '17':
                            if time.ticks_diff(time.ticks_ms(), sequencer.last_toggle) > 250:
                                await sequencer.toggle_dual_mode()

                    # CONSTANT SYNTH SCAN : DUAL MODE [IDLE]
                    if sequencer.dual_mode and not sequencer.running and not key_event:
                        await sequencer.handle_dual_mode_inputs()

                    if encoder.get_button_press():
                        sequencer.stop_sequence()
                        return

                    await asyncio.sleep_ms(1)
                    
                    # BLINKING CURSOR : SEQUENCE EDIT MODE
                    sequencer.update_idle_visual()

            elif mode == "CONFIGURE":
                await open_configure_menu(program_data)

        await asyncio.sleep_ms(1)

# BOOT CONDITIONS

# tm_display.scroll("Hello Hello Hello Hello")
# time.sleep(0.5)

display_program(programs[current_program_index])

last_direction = 0
last_time = 0

# PROGRAM CONFIGURATION MENU

async def open_configure_menu(program_data):
    config_options = ["BACK", "BPM", "WAVE", "CTRL", "MIDI", "SYNC"]
    config_index = 0
    last_dir = 0
    last_time = time.ticks_ms()

    display_mode(config_options[config_index])

    while True:
        display_mode(config_options[config_index])
        direction = encoder.get_direction()
        now = time.ticks_ms()
        if direction != 0:
            if direction != last_dir or time.ticks_diff(now, last_time) > 200:
                config_index = (config_index + direction) % len(config_options)
                last_dir = direction
                last_time = now
                display_mode(config_options[config_index])

        if encoder.get_button_press():
            selected = config_options[config_index]
            if selected == "BACK":
                return

            elif selected == "BPM":
                bpm = program_data.get("bpm", 80)
                tm_display.number(bpm)
                while True:
                    direction = encoder.get_direction()
                    now = time.ticks_ms()
                    if direction != 0:
                        if direction != last_dir or time.ticks_diff(now, last_time) > 200:
                            bpm = max(60, min(140, bpm + direction))
                            tm_display.number(bpm)
                            last_dir = direction
                            last_time = now
                    if encoder.get_button_press():
                        program_data["bpm"] = bpm
                        save_program(program_data)
                        break
                    time.sleep_ms(10)

            elif selected == "WAVE":
                waveforms = ["SIN", "TRI", "SAW", "SQR"]
                current_index = waveforms.index(program_data.get("waveform", "SIN"))
                display_mode(waveforms[current_index])
                while True:
                    direction = encoder.get_direction()
                    now = time.ticks_ms()
                    if direction != 0:
                        if direction != last_dir or time.ticks_diff(now, last_time) > 200:
                            current_index = (current_index + direction) % len(waveforms)
                            display_mode(waveforms[current_index])
                            last_dir = direction
                            last_time = now
                    if encoder.get_button_press():
                        program_data["waveform"] = waveforms[current_index]
                        save_program(program_data)
                        break
                    time.sleep_ms(10)

            elif selected == "CTRL":
                ctrl_options = ["DISABLED", "CUTOFF", "ASDR","ASDR_WAVE", "FILTER MOD", "FILTER SWEEP", "PITCH BEND"]
                current_ctrl = program_data.get("control", "DISABLED")
                if current_ctrl not in ctrl_options:
                    current_ctrl = "DISABLED"
                current_index = ctrl_options.index(current_ctrl)
                display_mode(ctrl_options[current_index])
                while True:
                    direction = encoder.get_direction()
                    now = time.ticks_ms()
                    if direction != 0:
                        if direction != last_dir or time.ticks_diff(now, last_time) > 200:
                            current_index = (current_index + direction) % len(ctrl_options)
                            display_mode(ctrl_options[current_index])
                            last_dir = direction
                            last_time = now
                    if encoder.get_button_press():
                        selected_ctrl = ctrl_options[current_index]
                        program_data["control"] = selected_ctrl
                        
                        if selected_ctrl == "DISABLED":
                            program_data["control_value"] = 0
                        elif selected_ctrl == "CUTOFF":
                            program_data["control_value"] = 32767
                        elif selected_ctrl == "ASDR":
                            program_data["control_value"] = 10000
                        elif selected_ctrl == "ASDR_WAVE":
                            program_data["control_value"] = 32767
                        elif selected_ctrl == "FILTER MOD":
                            program_data["control_value"] = 16384
                        elif selected_ctrl == "FILTER SWEEP":
                            program_data["control_value"] = 1000
                        elif selected_ctrl == "PITCH BEND":
                            program_data["control_value"] = 32767

                        display_mode("ON")
                        time.sleep(1)
                        save_program(program_data)
                        break
                    time.sleep_ms(10)

            elif selected == "MIDI":
                program_data["midi"] = not program_data.get("midi", False)
                program_data["sync"] = False
                display_mode("MIDI ON" if program_data["midi"] else "MIDI OFF")
                save_program(program_data)
                time.sleep(1)
                display_mode(config_options[config_index])

            elif selected == "SYNC":
                program_data["sync"] = not program_data.get("sync", False)
                program_data["midi"] = False
                display_mode("SYNC ON" if program_data["sync"] else "SYNC OFF")
                save_program(program_data)
                time.sleep(1)
                display_mode(config_options[config_index])

# OPERATIONAL LOGIC

async def main_loop():
    global last_direction, last_time, running_program, current_program_index, sequencer_global
    while True:
        if not running_program:
            direction = encoder.get_direction()
            current_time = time.ticks_ms()
            if direction != 0:
                if direction != last_direction or time.ticks_diff(current_time, last_time) > 200:
                    current_program_index = (current_program_index + direction) % len(programs)
                    display_program(programs[current_program_index])
                    last_direction = direction
                    last_time = current_time

            if encoder.get_button_press():
                await launch_program(current_program_index)
                display_program(programs[current_program_index])

        await asyncio.sleep_ms(20)

asyncio.run(main_loop())
