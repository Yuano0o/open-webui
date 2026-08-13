# Open WebUI Desktop Theme Patch

A small toolkit to apply a custom font and a ChatGPT-style reading theme to
the [Open WebUI](https://github.com/open-webui/open-webui) Desktop app.

## Why

Open WebUI Desktop is a signed Electron app, and its UI code is packed
inside an ASAR archive. There's no built-in way to theme the app shell, so
the only option is to edit the packed CSS file directly, then re-sign the
app so macOS still trusts it.

## What's included

- **`asar_font_patch.js`** — a small Node script (no dependencies) that reads
  and edits ASAR archives directly. It can:
  - `header-hash` — print a hash of the archive header, to compare versions
  - `compare` — list which files differ between two archives
  - `extract-file` — pull one file out of an archive
  - `replace-file` — swap one file inside an archive and repack it, fixing
    up the integrity hashes so Electron's checks still pass
- **`open-webui-custom.css`** — the theme itself: a system font stack, 17px
  text, 1.7 line height, a centered reading column, and ChatGPT-style
  styling for Markdown, tables, code blocks, and the message box. Plain
  CSS only — no fonts are bundled, no app behavior changes.

## How to use it

1. Find the CSS file inside `app.asar` (the exact path depends on the app
   version — use `extract-file` after listing the archive to locate it).
2. Add the contents of `open-webui-custom.css` to that file, or use it as a
   starting point for your own theme.
3. Repack the archive:
   `node asar_font_patch.js replace-file app.asar <path-in-archive> <local-file> app.asar.patched`
4. Replace the app's `app.asar` with the patched copy, then re-sign it
   locally with `codesign --force --deep --sign -` (any change to the app's
   files invalidates the original signature).
5. Keep the original `app.asar` and CSS file as a backup — undoing the
   patch is just copying them back.

If Open WebUI Desktop is connected to a locally running Open WebUI server,
note that the chat page itself loads a separate `/static/custom.css` file
from the server. That one's a plain file swap and doesn't need the ASAR
steps above.

## License

MIT
