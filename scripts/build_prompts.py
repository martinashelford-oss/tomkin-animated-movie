#!/usr/bin/env python3
"""Write prompts/ (Veo prompts per shot) and docs/generated/ (shot list, dialogue script,
sound-design and music cue sheets, cost estimate) from shots.json + production/."""
import sys

import _ids  # noqa: F401
from tomkin.project import Project
from tomkin.prompts import write_all

p = Project()
errors, _ = p.validate()
if errors:
    print("\n".join("ERROR: " + e for e in errors))
    sys.exit(2)
write_all(p)
print("Wrote prompts/ALL_PROMPTS.md, prompts/NNN.json and docs/generated/")
