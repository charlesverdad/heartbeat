# Pulse v2 deploy

`deploy.sh` deploys a prebuilt pulse-v2 bundle with this directory's `wrangler.jsonc`:

```bash
CONFIRM=yes manifests/pulse-v2/deploy.sh --release vX.Y.Z
```

The full runbook (access, deploy, smoke test, rollback, secrets) is in
[`terraform/pulse-v2/README.md`](../../terraform/pulse-v2/README.md).
