# Troubleshooting

Start with deterministic facts:

```bash
mos status . --json
mos doctor . --json
```

If a runtime skill is missing or stale, preview synchronization before applying it:

```bash
mos skills sync . --runtime all --plan --json
mos skills sync . --runtime all --yes --json
```

Synchronization never overwrites an unrecognized skill directory. Remove or relocate the
conflicting directory yourself after reviewing it, then run synchronization again.
