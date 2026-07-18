# Scientific Figure Knowledge Extension

This experimental extension implements two-stage visual retrieval for Open
WebUI `0.10.2`.

During ingestion, JPEG, PNG, and WebP files remain in Open WebUI storage while a
local service generates a validated textual description. The description can
include OCR, a literal caption, panels, axes, trends, labels, blot or gel lanes,
scientific interpretation, and uncertainty notes. Existing text embeddings are
used for retrieval.

When a visual description is retrieved, the backend checks access to the source
file again. If the selected answer model declares `capabilities.vision=true`, a
bounded set of original images is attached to the final user message so the
model can inspect pixels instead of merely repeating the ingestion description.

## Scope and non-goals

- No CLIP, SigLIP, or other image-vector index is added.
- No database migration is required.
- Structured analysis is stored in `file.data.vision_analysis`.
- Portable scalar metadata includes fields such as `paper_id`, `figure_no`,
  `doi`, and `image_file_id`.
- Existing Open WebUI ownership, administrator, and explicit read-grant checks
  protect retrieval-time access to original files.
- Generated descriptions are retrieval aids, not experimental ground truth.

## Data flow

```text
image upload
  -> Open WebUI storage
  -> local image-vision-loader
  -> Open WebUI vision model (preferred when configured)
     or Anthropic API (fallback)
  -> validated description + metadata
  -> existing text vector database
  -> retrieval hit
  -> source-file access check
  -> original pixels attached to a vision-capable answer model
```

## Credentials and provider selection

The service never requires a key to be written to a repository file.

On macOS, store an Anthropic key in Keychain:

```zsh
./services/image-vision-loader/store-key-in-keychain.zsh
```

`run-local.zsh` also looks for an existing Open WebUI API key under the Keychain
service name `open-webui-batch-uploader`. If both providers are configured, the
service tries the Open WebUI model first and falls back to Anthropic when that
call fails.

Relevant variables:

| Variable                           | Default                     | Purpose                                              |
| ---------------------------------- | --------------------------- | ---------------------------------------------------- |
| `OPEN_WEBUI_API_KEY`               | empty                       | Use an existing Open WebUI model connection.         |
| `OPEN_WEBUI_BASE_URL`              | `http://127.0.0.1:8080`     | Open WebUI API base URL.                             |
| `OPEN_WEBUI_VISION_MODEL`          | `claude-sonnet-5`           | Locally configured vision model identifier.          |
| `ANTHROPIC_API_KEY`                | empty                       | Direct Anthropic API fallback.                       |
| `ANTHROPIC_VISION_MODEL`           | `claude-sonnet-4-6`         | Direct Anthropic model identifier.                   |
| `ANTHROPIC_BASE_URL`               | `https://api.anthropic.com` | Anthropic-compatible API endpoint.                   |
| `VISION_LOADER_API_KEY`            | empty                       | Optional bearer token accepted by the local service. |
| `IMAGE_VISION_LOADER_API_KEY`      | empty                       | Matching token sent by Open WebUI to the service.    |
| `VISION_MAX_IMAGE_BYTES`           | 10 MiB                      | Ingestion-service request limit.                     |
| `IMAGE_VISION_MAX_BYTES`           | 10 MiB                      | Open WebUI loader-side file limit.                   |
| `VISION_RETRIEVAL_MAX_IMAGES`      | `3`                         | Maximum source images attached after retrieval.      |
| `VISION_RETRIEVAL_MAX_TOTAL_BYTES` | 15 MiB                      | Maximum decoded image bytes attached per answer.     |

Setting either retrieval limit to `0` disables retrieval-time image attachment.

The local service binds to `127.0.0.1`. For a shared workstation or any
non-local deployment, configure matching service tokens and an appropriate
secret manager.

## Run locally

```zsh
./services/image-vision-loader/run-local.zsh
curl --fail http://127.0.0.1:8765/health
```

Optional macOS LaunchAgent:

```zsh
./scripts/install-vision-loader-launch-agent.zsh
```

Remove it with:

```zsh
./scripts/remove-vision-loader-launch-agent.zsh
```

## Reversible Desktop backend overlay

The overlay is a development convenience for Open WebUI Desktop `0.10.2`. It
checks the installed version, backs up every Python module it replaces, installs
the backend extension, and copies the local vision service into Application
Support.

```zsh
./scripts/install-vision-knowledge-overlay.zsh
```

The latest backup location is recorded at:

```text
~/Library/Application Support/open-webui/vision-knowledge-current-backup
```

Restore it with:

```zsh
./scripts/restore-vision-knowledge-overlay.zsh
```

The overlay does not rebuild Electron/Svelte assets. The image-preview UI in
`KnowledgeBase.svelte` is available only in a normal source build. Do not force
the overlay onto another Open WebUI version; rebase and retest instead.

## Privacy and operational limits

- The original image is transmitted to the configured ingestion provider.
- A retrieved original image may be transmitted again to the selected answer
  model.
- API charges and provider retention policies depend on the deployment.
- Do not process confidential, regulated, or unpublished figures without an
  appropriate provider agreement and local security review.
- Base64 images increase request size; image count and aggregate decoded bytes
  are bounded by configuration.
- Only JPEG, PNG, and WebP data URLs are accepted for retrieval-time attachment.
  Internal Open WebUI file IDs are used server-side and omitted from model
  instructions; metadata labels are normalized and treated as untrusted text.
- If neither provider is configured, or both calls fail, image processing fails
  explicitly rather than indexing an empty description.

## Validation sequence

1. Confirm `/health` returns `{"ok":true}`.
2. Restart Open WebUI and verify ordinary text chat.
3. Upload one JPEG, PNG, or WebP knowledge file.
4. Confirm the file reaches `completed` and has a searchable description.
5. Query a visible label or trend with a vision-capable model.
6. Confirm the answer cites the retrieved source and distinguishes visible
   evidence from uncertainty.
7. Repeat with a user who lacks file access and confirm no image is attached.
