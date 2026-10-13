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

```bash
python autofile.py               # dry run: print the plan, change nothing
python autofile.py --apply       # execute with per-file y/n/all/quit prompts
python autofile.py --watch       # watch the folder; asks before each new file
python autofile.py --watch --yes # watch unattended (auto-approve)
python autofile.py --help
```

Example dry run:

```
plan for C:\Users\Sayantan\Desktop\Developer  (11 loose file(s))

  documents  open code 2.txt  ->  _sorted\documents\open code 2.txt
  images     shot.png         ->  _sorted\images\shot.png
  other      unknown.bin      ->  _sorted\other\unknown.bin

(dry run - nothing was moved. use --apply to execute.)
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
