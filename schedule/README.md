# Scheduled audits

`run_sites.sh` runs `audit.py` once for every site in `sites.txt`, one after the other, with `--no-psi` and a 30-minute timeout per site. A site that fails or times out is logged and the loop moves on. If a previous run is still going, the new one skips (lock in `logs/.run_sites.lock`).

## Outputs

- `out/<host>/`: the latest report, same files as a manual run.
- `out/<host>/history/<YYYY-MM-DD>/`: a copy of that run, without `crawl.pkl` and the `openseo/` cache. One folder per day; a second run on the same day overwrites it.
- `out/<host>/history/<date>/diff.md`: what changed since the previous snapshot.
- `schedule/logs/<host>-<YYYYMMDD-HHMM>.log`: full audit output per site per run.
- `schedule/logs/summary.log`: one line per site per run, e.g. `cumberlandheights.org: +1 new, -2 resolved, 3 changed`.

## What the diff shows

`diff_runs.py <host>` compares the two latest snapshots (or the only snapshot with the current `findings.json`): new findings, resolved findings, findings whose impact moved by 20% or more, and the top 5 before and after. Run it by hand any time.

## Add a site

Add a line `url|brand|city` to `sites.txt`, e.g. `https://www.example.org|Example Recovery|Austin, TX`.

## Install

- **macOS (launchd):** edit the paths in `launchd/com.treatment-seo-audit.plist`, copy it to `~/Library/LaunchAgents/`, then `launchctl load ~/Library/LaunchAgents/com.treatment-seo-audit.plist`. Runs daily at 03:15 if the Mac is awake.
- **Linux VPS (systemd):** edit `User=` and the paths in `systemd/*.service`, copy both files to `/etc/systemd/system/`, then `systemctl daemon-reload && systemctl enable --now treatment-seo-audit.timer`. Daily at 03:15 plus up to 15 minutes; a missed run catches up at boot.
- **Linux VPS (cron):** copy the lines from `crontab.example` into `crontab -e` and fix the paths and `MAILTO`.

Test first with `schedule/run_sites.sh` from a terminal and read `schedule/logs/summary.log`.

## Options and cost

Every run spends DataForSEO credits through OpenSEO, roughly 300-600 per site, so a daily schedule for five sites adds up. To run without that spend, set `AUDIT_EXTRA_ARGS="--skip openseo"` (crawler-only audit). `AUDIT_PSI=1` turns PageSpeed Insights back on; `AUDIT_TIMEOUT` changes the per-site timeout in seconds.

Keys come from `.env` as usual; nothing extra to set.
