# Open WebUI Knowledge Batch Uploader

Command-line tools for populating an [Open WebUI](https://github.com/open-webui/open-webui)
Knowledge base from a prepared local folder of scientific-literature assets
(figures, tables, and Markdown/CSV text) — built while running a
large personal research knowledge base on top of Open WebUI, where papers
needed to be re-uploaded repeatedly as the extraction schema evolved.

## Why

Open WebUI's Knowledge UI is drag-and-drop only, which does not scale once a
collection reaches hundreds of files across dozens of source papers, or when
the same collection needs to be re-uploaded after every schema change.
These scripts make that workflow idempotent, scriptable, and safe to re-run.

## What it does

- `batch_upload_images_to_knowledge.py` — uploads figures/tables (`.jpg` /
  `.png` / `.webp`) from a source directory tree, attaching structured
  metadata (paper id, DOI, figure/table number, caption, source path,
  content hash) so the images become searchable, individually citable
  knowledge items.
- `batch_upload_knowledge_bundle.py` — uploads the paired Markdown/CSV
  text representation of the same collection, reading frontmatter for
  paper id / DOI and skipping anything already uploaded.
- Both scripts hash file contents and compare against what's already in the
  target knowledge base, so re-running the same command only uploads what's
  new — safe to fire after adding a handful of new papers to a
  multi-hundred-file collection.
- `run-image-upload.zsh` / `run-bundle-upload.zsh` — thin wrappers that pull
  the API key from macOS Keychain and forward arguments to the Python
  scripts.
- `store-open-webui-api-key.zsh` — stores an Open WebUI API key in macOS
  Keychain instead of an env var or plaintext file.

## Usage

```sh
# one-time setup
./store-open-webui-api-key.zsh

# upload figures/tables
./run-image-upload.zsh /path/to/collection/upload_ready/_assets my-knowledge-base

# upload the text bundle
./run-bundle-upload.zsh /path/to/collection/upload_ready my-knowledge-base

# dry run first to preview without uploading
./run-image-upload.zsh /path/to/collection/upload_ready/_assets my-knowledge-base --dry-run
```

Or call the Python scripts directly with `OPEN_WEBUI_API_KEY` set in the
environment; see `--help` on each for the full option list.

## Expected source layout

```
<collection>/upload_ready/
├── *.md, *.csv                  # per-paper text, with DOI/paper-id frontmatter
└── _assets/
    └── <PAPER_ID>__<doi-with-underscores>/
        ├── figures/<name>.png (+ optional _caption.md)
        └── tables/<name>.png  (+ paired .md table source)
```

## Tests

```sh
python3 -m unittest discover -s tests
```

## License

MIT
