# Source Policy

## Excluded directories (always)

node_modules, .git, .handoff, __pycache__, .next, dist, build, .venv, .env (dir), vendor

## Excluded file patterns (high-risk → default action:"exclude")

- .env, .env.*, .env.local, .env.production
- *private*.pem, *private*.key, *.p12, *.pfx
- id_rsa, id_dsa, id_ecdsa, id_ed25519 (and .pub counterparts flagged, not excluded)
- credentials.json, service-account.json
- Any filename matching /secret/i

## Credential pattern scan (text files < 300KB)

Scan content for: API key patterns (sk-*, pk-*, Bearer tokens), password= assignments, connection strings with credentials (postgresql://user:pass@), private key headers (-----BEGIN ... PRIVATE KEY-----).

## Size limits

- Files > 10MB: action:"reference" (noted in REFERENCES.md, not copied)
- Binary files: copied as-is, no content scan

## Bucket classification

| Bucket | Criteria |
|---|---|
| plans | Path contains plans/ or docs/; ext .md .txt .rst |
| code | Ext .js .mjs .ts .tsx .py .rb .go .rs .java .cs .cpp .c .h |
| artifacts | Ext .pdf .xlsx .docx .zip .tar .gz |
| inputs | Everything else |
