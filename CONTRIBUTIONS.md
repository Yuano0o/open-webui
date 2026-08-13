# Contribution Boundary

This repository is a fork of
[Open WebUI](https://github.com/open-webui/open-webui). It retains the upstream
project structure so changes remain reviewable and can be rebased or proposed
upstream with minimal unrelated diff.

## Upstream functionality

Open WebUI supplies the application platform, including its chat interface,
model integrations, authentication and access-control system, file storage,
knowledge bases, retrieval pipeline, vector-database integrations, and general
frontend/backend build infrastructure.

Those capabilities are not presented here as original work by the fork author.
The upstream license, notices, branding requirements, and contributor terms
remain in the repository.

## Fork-author modifications

The current development branch adds the following engineering work.

### Scientific image ingestion

- Accept JPEG, PNG, and WebP knowledge files through the existing upload flow.
- Validate MIME type against the file signature and enforce an image-size cap.
- Preserve the original image in Open WebUI storage.
- Send the image to a local vision-loader service and index a validated textual
  representation containing OCR, caption, panels, axes, trends, labels,
  blot/gel lanes, interpretation, and uncertainties.
- Store structured analysis in the relational file record while keeping vector
  metadata scalar and portable across supported vector databases.

### Retrieval-time source inspection

- Carry authorized figure metadata through normal RAG source results.
- Deduplicate and rank retrieved image references.
- Recheck file access before reading original pixels.
- Attach a bounded number and total size of original images only when the answer
  model declares vision capability.
- Reject non-image data URLs, keep internal file IDs out of model instructions,
  and normalize untrusted metadata labels before adding them to context.

### Knowledge interface

- Preview a knowledge-base image beside its searchable text representation in
  source builds.
- Manage browser object-URL lifecycle when switching or closing previews.

### Retrieval identity

- Preserve the source filename and stable paper/Figure identifiers in every
  vector chunk so they remain searchable after long documents are split.

### Local operations

- Provide a standalone FastAPI vision-loader with Open WebUI-model support and
  Anthropic fallback.
- Keep credentials outside the repository through environment variables and a
  macOS Keychain helper.
- Provide version-checked install, LaunchAgent, backup, and restore scripts for
  local Open WebUI Desktop development.
- Add focused unit tests and GitHub Actions coverage for fork-specific code.

## Known limitations

- The Desktop overlay targets Open WebUI `0.10.2` and installs backend files
  only. The image-preview UI requires a source build.
- Image retrieval currently uses text embeddings over generated descriptions;
  there is no CLIP/SigLIP image-vector index.
- Vision output is model-generated evidence extraction and must not be treated
  as ground truth without checking the original figure and paper context.
- Provider availability, model identifiers, API pricing, and data-retention
  policies remain deployment-specific.
- The feature has focused unit coverage but still requires broader cross-model,
  cross-storage, and end-to-end evaluation.

## Future work (not pursued — branch archived)

This branch is archived and no further updates are planned. The items below
were under consideration while the branch was active and are kept for
reference, not as a roadmap:

- Add container-first deployment for the vision-loader service.
- Add integration tests covering upload, indexing, retrieval, access denial,
  and original-pixel attachment.
- Evaluate multilingual embedding models for Chinese queries over English
  literature.
- Add optional image-vector retrieval after the text-first workflow is stable.
- Rebase each independent change onto newer upstream releases.

## Pull-request strategy (not pursued — branch archived)

This section documents the review-friendly workflow that would have been used
had the fork-specific work been proposed upstream. It was not carried out and
is kept for reference:

1. Update local `main` from the fork/upstream baseline.
2. Create a new branch from `main` for one independently reviewable concern.
3. Cherry-pick or recreate only the relevant commit(s).
4. Keep UI, backend ingestion, retrieval behavior, service tooling, and generic
   chunking changes in separate PRs where practical.
5. Run the upstream checks and the focused feature tests before opening a PR.

This repository intentionally avoids broad formatting changes and unnecessary
file moves so each modification remains easy to compare with upstream.
