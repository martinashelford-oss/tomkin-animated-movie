from pathlib import Path
import json,sys
root=Path(__file__).resolve().parents[1]
shots=json.loads((root/'shots.json').read_text())
assert len(shots)==90 and sum(s['duration_seconds'] for s in shots)==900
missing=[s['id'] for s in shots if not (root/'assets/video'/f"{s['id']}.mp4").is_file()]
print(f"Timeline: {len(shots)} shots, {sum(s['duration_seconds'] for s in shots)} seconds")
print(f"Video clips present: {90-len(missing)}/90")
if missing:print('Missing:',', '.join(missing));sys.exit(1)
print('Ready to assemble')
