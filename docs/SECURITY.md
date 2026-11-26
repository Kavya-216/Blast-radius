# Security

## Secrets
Tokens and webhook secrets come from environment variables. They must not be committed.

## Webhooks
GitHub webhooks require `GITHUB_WEBHOOK_SECRET`. Verification uses HMAC-SHA256 over the exact raw body and constant-time comparison.

## Repository access
Local paths are accepted for the demo. Git commands use fixed argument arrays and do not execute user-provided shell strings.

## Prompt and source safety
Retrieved source is evidence, not instructions. The offline provider does not execute repository text. Future hosted providers should treat repository content as untrusted.
