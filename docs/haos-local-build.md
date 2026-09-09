# Home Assistant OS local build

This fork publishes a controlled multi-architecture image for the Home Assistant App:

```text
ghcr.io/gtassistant-sys/home-assistant-baby-monitor:0.4.0-local.7
```

The GitHub Actions workflow builds from the repository root using `baby_monitor/Dockerfile` and publishes `linux/amd64` plus `linux/arm64`. The App manifest points to the fork GHCR image; Supervisor therefore pulls the published image instead of attempting to build with `baby_monitor/` as an isolated context.

## HAOS data permissions

HAOS supplies the persistent App data mount at `/data` at runtime. The image does not assume a host UID/GID and does not chmod the bind mount. The container remains root because no `USER` is declared. The AppArmor profile grants the minimum verified access required by the bootstrap and runtime, including `/usr/bin/mkdir`, the Python virtualenv under `/opt/venv`, and `/data/** rwk,`; it does not use world-writable permissions.

## HAOS go2rtc endpoint

On HAOS, Baby Monitor must reach go2rtc through the HAOS `hassio` bridge rather than loopback. In the verified setup go2rtc listens on:

```text
http://172.30.32.1:1984
```

The App manifest sets:

```yaml
BABY_MONITOR_GO2RTC_URL: http://172.30.32.1:1984
```

Do not replace this with a `172.30.33.x` container address. The endpoint is the stable HAOS bridge address verified from both the host and the Baby Monitor container.

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
