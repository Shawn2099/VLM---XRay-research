"""Check the MedGemma image wheel bundle for a complete dependency closure.

Run: python medgemma/check_wheels.py
"""

from __future__ import annotations

import pathlib
import re
import zipfile

from pip._vendor.packaging.markers import default_environment
from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.packaging.version import Version

ROOTS = {
    "transformers": "4.51.3",
    "tokenizers": "0.21.4",
    "huggingface-hub": "0.36.0",
    "safetensors": "0.8.0",
    "regex": "2026.11.9",
    "jinja2": "3.1.4",
    "numpy": "2.0.2",
    "fastapi": "0.115.0",
    "starlette": "0.38.6",
    "uvicorn": "0.30.6",
    "python-multipart": "0.0.9",
    "pydantic": "2.14.3",
    "pillow": "11.0.0",
}

# Already present in the base PyTorch/Jupyter image and used at runtime.
BASE_PACKAGES = {
    "requests", "pyyaml", "packaging", "tqdm", "filelock",
    "typing-extensions", "fsspec", "protobuf", "torch", "torchvision",
}

wheels = {}
for whl in pathlib.Path("medgemma/wheels").glob("*.whl"):
    with zipfile.ZipFile(whl) as archive:
        metadata = [n for n in archive.namelist() if n.endswith(".dist-info/METADATA")][0]
        text = archive.read(metadata).decode("utf-8", "ignore")
    name = canonicalize_name(re.search(r"^Name: (.+)$", text, re.M).group(1))
    version = re.search(r"^Version: (.+)$", text, re.M).group(1)
    requires = re.findall(r"^Requires-Dist: (.+)$", text, re.M)
    wheels[name] = (version, requires)

env = default_environment()
env.update(
    python_version="3.11", python_full_version="3.11.9", sys_platform="linux",
    platform_system="Linux", platform_machine="x86_64", os_name="posix",
    implementation_name="cpython", extra="",
)

problems = []
for name, want in ROOTS.items():
    if name not in wheels:
        problems.append(f"MISSING ROOT {name}")
    elif wheels[name][0] != want:
        problems.append(f"ROOT VERSION {name} {wheels[name][0]} != {want}")

seen = set()
stack = list(ROOTS)
while stack:
    name = canonicalize_name(stack.pop())
    if name in seen:
        continue
    seen.add(name)
    if name not in wheels:
        problems.append(f"not bundled: {name}")
        continue
    if name in {"torch", "torchvision"}:
        continue
    for line in wheels[name][1]:
        try:
            req = Requirement(line)
        except Exception:
            continue
        if req.marker is not None and not req.marker.evaluate(env):
            continue
        dep = canonicalize_name(req.name)
        if dep in {"torch", "torchvision"}:
            continue
        if dep not in wheels:
            if dep in BASE_PACKAGES:
                continue
            problems.append(f"not bundled: {dep} (needed by {name} {wheels[name][0]})")
            continue
        if req.specifier and Version(wheels[dep][0]) not in req.specifier:
            problems.append(
                f"version: {dep} {wheels[dep][0]} not in {req.specifier} (needed by {name})"
            )
        stack.append(dep)

print(f"bundled wheels: {len(wheels)}")
print(f"closure: {len(seen)} packages")
if problems:
    print("PROBLEMS:")
    for problem in sorted(set(problems)):
        print("  -", problem)
else:
    print("all root pins present and dependency closure satisfied")
