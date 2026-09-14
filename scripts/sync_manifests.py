#!/usr/bin/env python3
import pathlib
import tomllib

import tomlkit

root = pathlib.Path(__file__).resolve().parents[1]
pixi_path = root / 'pixi.toml'
pyproject_path = root / 'pyproject.toml'

pixi = tomllib.loads(pixi_path.read_text())
pyproject = tomllib.loads(pyproject_path.read_text())

# --- Sync version ---
pixi_version = pixi['package']['version']
pyproject['project']['version'] = pixi_version

# --- Sync only [package.run-dependencies] ---
run_deps = pixi.get('package', {}).get('run-dependencies', {})
runtime_deps = [f'{k}{v}' if isinstance(v, str) else k for k, v in run_deps.items()]

pyproject['project']['dependencies'] = runtime_deps

# --- Write back ---
pixi_path.write_text(tomlkit.dumps(pixi))
pyproject_path.write_text(tomlkit.dumps(pyproject))

print(
    f'Synced version {pixi_version} and {len(runtime_deps)} runtime dependencies from [package.run-dependencies].'
)
