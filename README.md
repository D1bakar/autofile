# autofile

![CI](https://github.com/D1bakar/autofile/actions/workflows/ci.yml/badge.svg)

Watch a folder, sort loose files by type. **Dry-run by default — nothing moves
until you say so.**

Files get dumped into a folder and just sit there. autofile classifies them by
extension and files them into `_sorted/` bins. It stops at the top level:
project folders are never entered, never moved, never touched.

## Install

```bash
git clone https://github.com/D1bakar/autofile.git
cd autofile
pip install -r requirements.txt   # watchdog + pytest
```

Requires Python 3.10+.

## Usage

Run it — it asks you what to do. No flags to remember:

```bash
python autofile.py
```

```
------------------------------------------------------------
  AUTOFILE  -  sorts loose files into folders by type
------------------------------------------------------------
  folder : C:\Users\Sayantan\Desktop\Developer
  found  : 10 loose file(s)
           (project folders are never touched)

  1) Preview   - show what would happen (nothing moves)
  2) Sort all  - move every file now
  3) Review    - ask me about each file
  4) Watch     - sort new files as they land (Ctrl+C stops it)
  5) Quit

  Your choice [1]:
```

- **1** shows the plan and moves nothing (safe default)
- **2** asks one confirmation, then sorts everything
- **3** asks one plain-English question per file:
  `Move "notes.txt" into the documents folder?  [Y]es / [N]o / [A]ll / [Q]uit`
- **4** watches the folder while you work; Ctrl+C stops it and returns to the menu

### For powers (scripting)

```bash
python autofile.py --apply            # skip menu, go straight to per-file prompts
python autofile.py --apply --yes      # skip menu and prompts (unattended)
python autofile.py --watch --yes      # unattended watch
python autofile.py --help
```

## Safety model

| Rule | Why |
|---|---|
| Top-level loose files only | Projects (directories) are never entered or moved. |
| Dry run by default | `--apply` is required for anything to happen. |
| Per-file confirmation | `y` / `n` / `a`ll / `q`uit — decline and the file stays put. |
| Conflict-safe | Existing files are never overwritten; new arrivals get `name (2).ext`. |
| Full action log | Every move/skip is appended to `autofile.log`. |
| Hidden / ignored names | Dotfiles, `node_modules`, the tool's own folders are skipped. |
| Settle window (watch) | 2s debounce so half-finished downloads aren't sorted mid-write. |

## Configuration

`config.json`:

```json
{
  "watch_path": "C:\\Users\\Sayantan\\Desktop\\Developer",
  "output_dir": "_sorted",
  "settle_seconds": 2,
  "rules": {
    "images": [".jpg", ".png"],
    "documents": [".pdf", ".txt"]
  },
  "ignore_names": ["autofile", "_sorted", ".git", "node_modules"]
}
```

- `rules` — category → extensions. Anything unmatched goes to `other`.
- `ignore_names` — directories and files the tool must never consider
  (matched case-insensitively).
- `output_dir` — bin root; created on first real run, always ignored by the
  scanner and watcher.

## Development

```bash
pip install -r requirements.txt
python -m pytest tests/ -q
```

Workflow: feature branches off `main`, PRs, merge commits, CI on every push.

## License

[MIT](LICENSE) © D1bakar
