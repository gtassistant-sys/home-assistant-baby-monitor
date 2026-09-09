# Home Assistant OS local build

This fork is packaged for a local Home Assistant App build. `baby_monitor/config.yaml` deliberately has no `image:` field, so Supervisor builds `baby_monitor/Dockerfile` from the repository instead of pulling the upstream GHCR image.

The local App version is `0.4.0-local.1`; it is intentionally distinct from upstream release `0.4.0`.

## HAOS data permissions

HAOS supplies the persistent App data mount at `/data` at runtime. The image does not assume a host UID/GID and does not chmod the bind mount. The container remains root because no `USER` is declared, while the AppArmor profile grants only the directory traversal, creation, read/write, and locking permissions required below `/data`. The application and bootstrap retain `umask 077` and create private subdirectories with mode `0700`.

The previous AppArmor rule allowed read/write but not directory traversal (`x`), which can make `mkdir /data/...` fail on a mounted directory. The corrected rules are narrowly scoped to `/data` and do not use world-writable permissions.

## Upstream sync

```text
git fetch upstream
git log --oneline HEAD..upstream/main
git diff --name-status HEAD..upstream/main
git merge upstream/main       # resolve and test; never blind reset --hard
git push origin main          # only after tests pass
```

Before removing a local patch, verify the upstream change fixes the same HAOS behavior and record that decision in the commit message or review notes.

## Read-only update monitor

`tools/check_upstream.py` fetches upstream, counts commits since the merge base, checks critical paths, checks upstream tags/releases, and probes the public GHCR tag list. It never merges, changes branches, or pushes. Hermes runs it daily; output is delivered only when there is something to review.
