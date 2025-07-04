import ujson

def save_program(program_data):
    name = program_data.get("program")
    if not name:
        folder = program_data.get("folder", 1)
        name = f"P{folder}"
        program_data["program"] = name
    with open(f"{name}.json", "w") as f:
        ujson.dump(program_data, f)

def load_program(program_name):
    folder_number = int(program_name[1:])
    try:
        with open(f"{program_name}.json", "r") as f:
            data = ujson.load(f)
    except:
        data = {}
    return {
        "program": program_name,
        "folder": folder_number,
        "bpm": data.get("bpm", 80),
        "waveform": data.get("waveform", "SIN"),
        "control": data.get("control", "DISABLED"),
        "control_value": data.get("control_value", 0),
        "sequence": data.get("sequence", [None] * 16),
        "midi": data.get("midi", False),
        "sync": data.get("sync", False)
    }
