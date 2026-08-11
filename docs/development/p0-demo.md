# Agora P0 Demo

The P0 demo proves the first end-to-end Agora loop:

```text
Git fixture -> Asset normalization -> fake indexes -> Harness ContextPack -> Writeback -> re-index -> later retrieval
```

Run:

```bash
.venv/bin/python scripts/run_p0_demo.py
```

Expected checkpoints:

- `project initialized`
- `context summary`
- `skill output`
- `writeback accepted`
- `later retrieval summary`

The demo uses `tests/fixtures/sample_repo` and in-memory fake stores. It does not require Docker.
