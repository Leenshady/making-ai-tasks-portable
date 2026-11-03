# Task Snapshot (Example)

> This is an example snapshot showing what a valid task snapshot looks like. A successor can fully resume by reading this one file.

## Identity & Meta

| Field | Value |
|---|---|
| Task ID | `task-20261102-1530` |
| Slug | `ndm-download-filter` |
| Title | Adjust download interception strategy for the NDM extension |
| Status | in-progress |
| Created At | 2026-11-02T14:00:00+08:00 |
| Updated At | 2026-11-02T15:30:00+08:00 |
| Schema Version | 1.2.0 |

## Goal

**Goal**

Adjust the NDM Chrome extension's download interception to support file-type filtering, without affecting other features (download management, status monitoring).

**Success Criteria**

- `ct.js` gains file-type filtering logic, and existing interception paths behave unchanged.
- Manual test passes: MP4 files are intercepted, other types pass through normally.
- `bg.js` requires no change (verify cross-context communication is unaffected).

**Constraints**

- Must keep the MV3 architecture using `chrome.storage.session` + `chrome.sendMessage`.
- No third-party libraries.
- Do not change the existing download-management UI or interactions.

**Non-goals**

- No download-speed / resume optimizations.
- Do not refactor `bg.js`.

## Context

**Background**

The NDM extension uses MV3. `ct.js` (content script) intercepts download links; `bg.js` (service worker) handles network monitoring and cross-context communication. The user wants tighter interception rules for specific file types, but worries about affecting existing features.

**Key Decisions**

- Decision: put filtering logic in `ct.js`, not `bg.js` → Reason: interception happens at the content-script layer, so a local change is lower risk and matches "do not affect other features".
- Decision: cache the filter rule via `chrome.storage.session` → Reason: under MV3 the service worker may sleep; session storage is the most reliable cross-context option.

**Assumptions**

- The current `ct.js` concentrates interception in a single entry function (not yet confirmed line by line).

**Terminology**

- `ct.js`: content script that intercepts download links
- `bg.js`: service worker that monitors network and handles cross-context communication

## Progress

**Completed**

- Mapped the responsibilities and communication between `ct.js` and `bg.js`.
- Located the download-interception code path.

**In Progress**

- Analyzing the interception function in `ct.js` line by line.

**Findings**

- `ct.js` does route every interception through a single entry function, so the assumption holds and no wrapper is needed.
- The existing interception does not check file type at all, so adding a filter cannot break a prior type-based branch.

**Next Steps**

1. [priority 1] Confirm the location and line numbers of the interception entry function in `ct.js`.
2. [priority 2] Design the insertion point for file-type filtering.
3. [priority 3] Implement the filtering logic with minimal changes.

**Blockers**

- None.

**Risks**

- A filter-rule cache key-name collision with existing session data — avoid by using a dedicated namespace.

## Artifacts

**Workspace**

- Root: `F:\dev\ndm-extension`
- VCS: git, branch `main`, commit `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0`, remote `https://github.com/example/ndm-extension.git`, repo `F:\dev\ndm-extension`, working tree DIRTY at snapshot time
- Uncommitted: M ct.js (temporary tracing logs added while analysing)
- Excluded: `dist/` — build output; regenerate with npm run build
- Excluded: `node_modules/` — reinstall with npm ci

**Files**

- `F:\dev\ndm-extension\ct.js` — content script that intercepts download links; add filtering logic here.
- `F:\dev\ndm-extension\bg.js` — service worker; not changed in this task.
- `F:\dev\ndm-extension\manifest.json` — extension manifest; sync if new permissions are added.

**Dependencies**

- Chrome (with the NDM extension) — Install the latest stable Chrome and load the NDM extension for manual testing.

**Environment**

- Windows 11
- Chrome latest stable (MV3 support)

**Commands**

```bash
# Reload the extension in chrome://extensions to apply changes.
```

## Resume

**How to Resume**

Open `F:\dev\ndm-extension\ct.js` and find the interception entry function (roughly in the second half of the file), then continue from the first `next_steps` item.

1. Confirm the entry function's location and line numbers.
2. Run the existing interception once before changes to confirm baseline behavior.
3. Design the insertion point for file-type filtering.

**Contact**

Task owner (reachable via the original conversation / workbench).

**Handoff Notes**

- The user prefers detailed technical explanations: architecture diagrams, line-by-line code breakdown, file paths with line numbers, and comparison tables.
- For communication, `chrome.storage.session` is preferred over `chrome.sendMessage` (more reliable under MV3); new code should reuse the session approach.
