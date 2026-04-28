import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the exact string
needle = 'engine = LogicEngine(DB_PATH)'
idx = content.find(needle)
if idx == -1:
    print("NOT FOUND")
else:
    print(f"Found at index {idx}")
    print(repr(content[idx:idx+120]))

# Try replacing using regex to be newline-agnostic
old_pattern = r'(        engine = LogicEngine\(DB_PATH\)\s+)(        files = engine\.generate_outputs\(profile\))'
new_str = (
    r'\g<1>'
    '        print(f"DEBUG: Processing with profile: {profile}")\n'
    r'        files = engine.generate_outputs(profile)'
    '\n        print(f"DEBUG: Generated files: {files}")'
)

new_content, count = re.subn(old_pattern, new_str, content)
if count:
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Patched {count} occurrence(s) successfully.")
else:
    print("Pattern not matched. Showing surrounding context...")
    for i, line in enumerate(content.splitlines()):
        if 'generate_outputs' in line or 'LogicEngine(DB_PATH)' in line:
            print(f"  Line {i+1}: {repr(line)}")
