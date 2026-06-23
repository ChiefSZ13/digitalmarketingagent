# Threat Model

Primary risks for this slice:

- Uploaded files may be malformed, oversized, mislabeled, or decompression bombs.
- User descriptions and visible image text may contain prompt-injection instructions.
- Provider output may omit evidence, invent claims, or fail schema validation.
- Logs may accidentally expose secrets, raw image bytes, or personal data.
- Frontend previews may leak image bytes through browser storage if persisted.

Controls:

- Verify JPEG, PNG, and WebP signatures and decode with Pillow before provider use.
- Enforce image count, byte, and pixel limits.
- Strip image metadata before provider calls.
- Treat descriptions and image text as data in prompts.
- Validate every provider result with Pydantic.
- Require evidence IDs on material assertions.
- Keep secrets in infrastructure configuration only.
- Use fixture mode and mock providers for CI.
- Do not persist uploaded image bytes in browser storage.

