# Docker execution

The image uses Python 3.15.2 and installs pinned dependencies during build.
Each container downloads data once, writes results and exits. No .env is needed.

```sh
docker build --pull -t mz-extractor .
docker run --rm --user "$(id -u):$(id -g)" --mount "type=bind,source=$(pwd),target=/data" mz-extractor
```

PowerShell:

```powershell
docker build --pull -t mz-extractor .
docker run --rm --mount "type=bind,source=$($PWD.Path),target=/data" mz-extractor
```

The mounted directory retains docs/last_data.csv, dated CSV snapshots,
docs/7days.svg, docs/index.html and README.md after the container exits.
Existing docs snapshots are used for comparison. README.md is generated and overwritten.
Logs go to stdout/stderr; failures return a nonzero exit code.

GitHub Actions builds and runs this same image, mounts its checkout and uses the
runner UID/GID. Commit and Pages publication happen on the runner only after success.
The workflow retains its existing daily schedule and manual trigger.
