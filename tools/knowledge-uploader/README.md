# Open WebUI Knowledge Batch Uploader

Command-line tools that upload a folder of files into an
[Open WebUI](https://github.com/open-webui/open-webui) Knowledge base.

## Why

Open WebUI's Knowledge page only supports drag-and-drop uploads. That is
slow and error-prone once you have hundreds of files, or need to upload the
same folder again after changing something upstream. These scripts do the
same job from the command line, and skip files that are already uploaded.

## What's included

- `batch_upload_images_to_knowledge.py` — uploads images (`.jpg` / `.png` /
  `.webp`) and attaches metadata (an id, a source label, a caption, the file
  path, and a content hash) so each image is searchable on its own.
- `batch_upload_knowledge_bundle.py` — uploads the matching Markdown/CSV
  text files for the same folder.
- Both scripts hash each file and check it against what's already in the
  target knowledge base, so running the same command twice only uploads
  what's new.
- `run-image-upload.zsh` / `run-bundle-upload.zsh` — wrapper scripts that
  read the API key from macOS Keychain and call the Python scripts.
- `store-open-webui-api-key.zsh` — saves an Open WebUI API key to macOS
  Keychain, so it isn't stored as plain text.

## Usage

```sh
# one-time setup
./store-open-webui-api-key.zsh

# upload images
./run-image-upload.zsh /path/to/folder/upload_ready/_assets my-knowledge-base

# upload the text files
./run-bundle-upload.zsh /path/to/folder/upload_ready my-knowledge-base

# preview without uploading
./run-image-upload.zsh /path/to/folder/upload_ready/_assets my-knowledge-base --dry-run
```

You can also call the Python scripts directly with `OPEN_WEBUI_API_KEY` set
in the environment. Run either script with `--help` for all options.

## Expected folder layout

```
<folder>/upload_ready/
├── *.md, *.csv                  # text files, with an id/DOI in the frontmatter
└── _assets/
    └── <ID>__<doi-with-underscores>/
        ├── figures/<name>.png (+ optional _caption.md)
        └── tables/<name>.png  (+ paired .md table source)
```

## Tests

```sh
python3 -m unittest discover -s tests
```

## License

MIT
