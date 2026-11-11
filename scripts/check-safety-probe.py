#!/usr/bin/env python3
"""Exercise the packaged CLI contract without starting a session or changing power settings."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

binary = Path(sys.argv[1]).resolve()
if not binary.is_file():
    raise SystemExit(f"Missing executable: {binary}")
with tempfile.TemporaryDirectory(prefix="insomniac-probe-") as directory:
    root = Path(directory)
    env = dict(os.environ, INSOMNIA_HOME=str(root))
    config = root / "config.json"
    # Only this disposable test configuration disables hardware-dependent rules.
    # No production setting is read or changed.
    scenarios = [
        ("safe", json.dumps({"endFloor": 0, "thermalRules": False}), [], 0, b"safe\n"),
        ("invalid-arguments", "{}", ["unexpected"], 64, b"usage\n"),
        ("invalid-config", "{", [], 10, b"stop-configuration-unreadable\n"),
    ]
    for name, settings, extra, expected_status, expected_output in scenarios:
        config.write_text(settings)
        for transport in ("pipe", "file"):
            args = [str(binary), "--check-session-safety", *extra]
            if transport == "pipe":
                result = subprocess.run(args, input=b"", capture_output=True, env=env, timeout=20)
                output = result.stdout
            else:
                with (root / "out").open("wb+") as target:
                    result = subprocess.run(args, stdin=subprocess.DEVNULL, stdout=target,
                                            stderr=subprocess.PIPE, env=env, timeout=20)
                    target.seek(0)
                    output = target.read()
            print(f"{name}/{transport}: exit={result.returncode}, stdout={output!r}, stderr={result.stderr!r}", flush=True)
            if (result.returncode, output) != (expected_status, expected_output):
                raise SystemExit("Safety probe CLI contract failed")
    for unexpected in ("session.json", "state.json", "LaunchAgents", "Logs"):
        if (root / unexpected).exists():
            raise SystemExit(f"Probe unexpectedly created {unexpected}")
print("All six packaged safety-probe checks passed; no session or recovery state created.")
