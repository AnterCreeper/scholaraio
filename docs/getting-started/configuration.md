# Configuration

ScholarAIO uses two config files:

| File | Tracked | Purpose |
|------|---------|---------|
| `config.yaml` | Yes | Default settings |
| `config.local.yaml` | No (git-ignored) | API keys and local overrides |

## API Keys

LLM API key lookup order:

1. `config.local.yaml` → `llm.api_key`
2. Environment variable `SCHOLARAIO_LLM_API_KEY`
3. Backend-specific environment variables, based on `llm.backend`:
   - `openai-compat`: `DEEPSEEK_API_KEY` → `OPENAI_API_KEY`
   - `anthropic`: `ANTHROPIC_API_KEY`
   - `google`: `GOOGLE_API_KEY` → `GEMINI_API_KEY`

### Example `config.local.yaml`

```yaml
llm:
  api_key: "sk-your-key-here"

ingest:
  mineru_api_key: "your-mineru-token"  # compatibility alias; MINERU_TOKEN is preferred
  s2_api_key: "your-semantic-scholar-key"  # optional

zotero:
  api_key: "your-zotero-key"  # optional
  library_id: "1234567"  # optional
```

You can also keep the token out of YAML entirely and set `MINERU_TOKEN` in the environment. `MINERU_API_KEY` is still accepted as a compatibility alias.

## Key Settings

### LLM Backend

Default: DeepSeek (`deepseek-chat`) via OpenAI-compatible protocol.

```yaml
llm:
  model: deepseek-chat
  base_url: https://api.deepseek.com
```

### Metadata Extraction

```yaml
ingest:
  extractor: robust  # regex + LLM (default)
  # Other options: auto, regex, llm
```

### Embedding Source

```yaml
embed:
  source: modelscope  # default (China)
  # source: huggingface  # for international users
```

### Backup Targets

ScholarAIO can sync its `data/` directory to a remote machine through `rsync`.
`scholaraio backup run` always invokes SSH in batch mode (`-o BatchMode=yes`), so password prompts and host-key confirmation prompts are intentionally disabled.

```yaml
backup:
  source_dir: data
  targets:
    lab:
      host: backup.example.com
      user: alice
      path: /srv/scholaraio
      port: 22
      identity_file: ~/.ssh/id_ed25519
      mode: default
      compress: true
      enabled: true
      exclude:
        - "*.tmp"
        - "metrics.db"
```

- `mode` supports `default`, `append`, and `append-verify`.
- Use `default` for the full ScholarAIO `data/` tree, especially when it includes mutable files such as SQLite databases.
- Reserve `append` / `append-verify` for append-only artifacts where the remote copy is expected to be a prefix of the local file.
- Keep host-specific secrets such as `identity_file` in `config.local.yaml` when possible.
- Prepare SSH key-based authentication and the target host's `known_hosts` entry ahead of time; otherwise `backup run` will fail fast instead of waiting for interactive input.

Recommended split:

```yaml
# config.yaml
backup:
  source_dir: data
  targets:
    lab:
      host: 192.168.31.229
      user: lzmo
      path: /srv/scholaraio
      port: 1393
      mode: default
      compress: true
      enabled: true
```

```yaml
# config.local.yaml
backup:
  targets:
    lab:
      identity_file: ~/.ssh/id_ed25519
      # password: your-ssh-password  # Optional fallback when the server does not accept your key
```

Recommended first-run checklist:

1. Add the target host to `known_hosts`:
   `ssh-keyscan -p 1393 192.168.31.229 >> ~/.ssh/known_hosts`
2. If the server accepts your SSH key, verify it first:
   `ssh -i ~/.ssh/id_ed25519 -p 1393 lzmo@192.168.31.229 true`
3. If the server is password-only, place `password` in `config.local.yaml`; ScholarAIO will switch to internal non-interactive askpass mode automatically.
4. Dry-run first:
   `scholaraio backup run lab --dry-run`
