# CI/CD Review: Build & Release Workflows

## Overview

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **build-Linux.yml** | `workflow_dispatch` | Build Linux (x86_64, arm64), upload artifacts |
| **build-macOS-Apple.yml** | `workflow_dispatch` | Build macOS ARM64 (Apple Silicon), upload DMG |
| **build-macOS-Intel.yml** | `workflow_dispatch` | Build macOS x86_64, upload DMG |
| **build-Windows.yml** | `workflow_dispatch` | Build Windows x86_64, Inno Setup installer + artifacts |
| **release.yml** | `release: types: [created]` (draft only) or `workflow_dispatch` | Build all platforms, upload to draft release, then publish (avoids immutable release errors) |

---

## Fixes Applied

1. **VERSION in app**  
   `app.common.setting` did not export `VERSION`, so every workflow step that runs  
   `from app.common.setting import VERSION` would fail.  
   **Fix:** `VERSION` is now defined in `app/common/setting.py`, reading from `pyproject.toml` (with fallback when the package is not installed, e.g. in CI).

2. **Release uploads never ran**  
   `release.yml` is triggered by **Release published**, so `github.ref` is the default branch (e.g. `refs/heads/main`), not a tag. The condition `if: startsWith(github.ref, 'refs/tags/')` was always false, so no assets were uploaded.  
   **Fix:** Condition changed to `if: github.event_name == 'release'` and `tag_name: ${{ github.event.release.tag_name }}` added so `softprops/action-gh-release` attaches assets to the correct release.

3. **macOS DMG failure not failing the job**  
   In `release.yml`, the ARM64 macOS job’s retry loop did not `exit 1` after max attempts.  
   **Fix:** `exit 1` added after "Failed to create DMG after $max_attempts attempts".

---

## Critical: Missing Build Commands

The workflows assume build output already exists but **do not run the actual build**:

| Workflow / Job | Step name | Issue |
|----------------|-----------|--------|
| **build-Linux.yml** | "Build with PyInstaller" | Only sets `VERSION`; no `pyinstaller` or `python -m PyInstaller` (e.g. `vok.spec`). So `dist/VOK-Get` is never created. |
| **build-Windows.yml** | "Build with Nuitka" | Only sets `VERSION`; no Nuitka invocation. So `dist/VOK-Get.dist` is never created. |
| **release.yml** (Windows) | "Build with Nuitka" | Run block is **empty**; no build and no `VERSION` in that step. |
| **release.yml** (macOS ARM/Intel) | "Build with Nuitka" | Only sets `VERSION`, `chmod`, and `rm`; no Nuitka. So `dist/VOK-Get.app` is never created. |
| **build-macOS-Apple.yml** / **build-macOS-Intel.yml** | "Build with Nuitka" | Same: no Nuitka run. |

**What you need to do:** Add the real build command in each “Build with PyInstaller” / “Build with Nuitka” step (e.g. call your Nuitka/PyInstaller command or a script that runs it). The repo’s `vok.spec` and `scripts/build_mac.sh` use **PyInstaller** and produce `dist/VOK.app`, while the workflows expect **Nuitka** and `dist/VOK-Get.app` / `dist/VOK-Get.dist` — align either the workflows with PyInstaller/spec or add Nuitka config and call it here.

---

## Other Recommendations

- **Step name vs Python version:** Steps say "Set up Python 3.11" but use `python-version: '3.12'`. Update the step names to "Set up Python 3.12" to avoid confusion.
- **Actions:** Consider upgrading `actions/checkout@v2` → `@v4` and pin major versions for other actions.
- **Runners:** `ubuntu-20.04` and `windows-2019` are older; consider `ubuntu-22.04` and `windows-2022` when convenient.
- **release.yml – Windows:** Move or duplicate the `VERSION` export into the "Build with Nuitka" step so the job has `env.VERSION` even if you later reorder steps.

---

## How to Test

- **Build workflows:** Run manually via **Actions → [workflow] → Run workflow**.
- **Release (with build files):** To get zip/DMG/installer assets on a release, **do not** publish from the UI first. Either: (1) Run **Actions → Release → Run workflow** and enter a **new** tag (e.g. `v1.0.1`) — the workflow creates a draft, builds all platforms, uploads assets, then publishes; or (2) Create a new release in the UI **as draft** with a new tag — the workflow runs on draft creation, builds, uploads, then publishes. Releases published before the workflow runs (e.g. v1.0.0) are immutable and cannot get assets added later.
