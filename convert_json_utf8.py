import json

files = ["groups.json", "users.json", "full_data.json"]

for filename in files:
    utf8_objects = []
    with open(filename, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    utf8_objects.append(json.loads(line))
                except json.JSONDecodeError:
                    pass  # skip bad lines
    with open(filename.replace(".json", "_utf8.json"), "w", encoding="utf-8") as f:
        json.dump(utf8_objects, f, indent=2)
    print(f"Converted {filename} -> {filename.replace('.json', '_utf8.json')}")
