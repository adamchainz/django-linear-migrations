#!/usr/bin/env python
from __future__ import annotations

import os
import subprocess
import sys
from functools import partial
from pathlib import Path

if __name__ == "__main__":
    os.chdir(Path(__file__).parent)
    common_args = [
        "uv",
        "pip",
        "compile",
        "--quiet",
        "--generate-hashes",
        "--constraint",
        "-",
        "requirements.in",
        *sys.argv[1:],
    ]
    run = partial(subprocess.run, check=True)
    configs = [
        ("3.9", "py39-django42.txt", b"Django>=4.2a1,<5.0"),
        ("3.10", "py310-django42.txt", b"Django>=4.2a1,<5.0"),
        ("3.10", "py310-django50.txt", b"Django>=5.0a1,<5.1"),
        ("3.10", "py310-django51.txt", b"Django>=5.1a1,<5.2"),
        ("3.11", "py311-django42.txt", b"Django>=4.2a1,<5.0"),
        ("3.11", "py311-django50.txt", b"Django>=5.0a1,<5.1"),
        ("3.11", "py311-django51.txt", b"Django>=5.1a1,<5.2"),
        ("3.12", "py312-django42.txt", b"Django>=4.2a1,<5.0"),
        ("3.12", "py312-django50.txt", b"Django>=5.0a1,<5.1"),
        ("3.12", "py312-django51.txt", b"Django>=5.1a1,<5.2"),
        ("3.13", "py313-django51.txt", b"Django>=5.1a1,<5.2"),
    ]
    for py, requirements_file, constraint in configs:
        run(
            [
                *common_args,
                "--python",
                py,
                "--output-file",
                requirements_file,
            ],
            input=constraint,
        )
