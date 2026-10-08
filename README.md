# sp2rclone

Generate an [rclone](https://rclone.org) config that mounts **every document library of a SharePoint site** as one folder tree on Linux.

Microsoft does not provide a native file-system mount driver for Linux. rclone's `onedrive` backend can mount SharePoint, but it needs one `[section]` with a `drive_id` per document library, and a site can have dozens of libraries. `sp2rclone` removes that manual work:

1. It authenticates against Microsoft Graph with an Azure app registration (app-only, no interactive login).
2. It lists every document library on the site.
3. It writes one rclone remote per library, plus a single `sp-all` remote (rclone's [`combine`](https://rclone.org/combine/) backend) that exposes all libraries as sub-folders named after the real library names.

You then mount only `sp-all:`.

## Requirements

- Linux with [rclone](https://rclone.org/install/) and FUSE (`fuse3`)
- Python 3.12+ and [uv](https://docs.astral.sh/uv/) (or any way to install `requests`)
- An Azure AD app registration with the Microsoft Graph **application** permission `Sites.Read.All` (or `Sites.Selected`), with admin consent granted. App-only authentication cannot use delegated permissions.

## Setup

```bash
uv sync
```

Create a `config.ini` file in a directory of your choice. All paths in this README are only examples: you choose where `config.ini` lives (`-s`), where the generated `rclone.conf` is written (`-o`, for example `rclone/rclone.conf` or `/etc/rclone/sharepoint.conf`) and where the mount point is. See [Usage](#usage).

Example `config.ini`:

```ini
[azure]
tenant_id = <tenant id>
client_id = <app client id>
client_secret = <app client secret>

[sharepoint]
host_name = yourtenant.sharepoint.com
site_name = /sites/YourSite
```

`site_name` must be the full site path, including `/sites/`.

Create the (empty) `rclone.conf` once, at any path you like; the script refuses to run if the file does not exist. If you do not pass `-o`, it uses `<settings-dir>/rclone/rclone.conf`.

```bash
RCLONE_CONF=rclone/rclone.conf     # any path you choose
mkdir -p "$(dirname "$RCLONE_CONF")"
touch "$RCLONE_CONF"
chmod 600 "$RCLONE_CONF"
```

## Usage

```bash
uv run python main.py
```

| Option | Default | Description |
| --- | --- | --- |
| `-s`, `--settings-dir` | `~/sharepoint/config` | Directory containing `config.ini` |
| `-o`, `--output` | `<settings-dir>/rclone/rclone.conf` | rclone config file to write (any path; must already exist) |

Example with custom locations:

```bash
uv run python main.py -s /path/to/settings-dir -o /path/to/rclone.conf
```

The script writes:

- the rclone config: one `[sp-<library>]` section per library and the combined `[sp-all]` remote
- `rclone.conf.manifest.tsv`: a table mapping each section name to the library name and URL

Re-run it whenever libraries are added to the site, then remount.

## Mounting

Point rclone at the generated file, check the remote, then mount it:

```bash
export RCLONE_CONFIG=/path/to/rclone.conf     # the file you generated, or pass --config to rclone

rclone lsd sp-all:                     # should list every library
mkdir -p ~/sharepoint/sites/YourSite
rclone mount sp-all: ~/sharepoint/sites/YourSite --vfs-cache-mode writes
```

Run it in the foreground first to see errors; add `--daemon` once it works. Unmount with:

```bash
fusermount -u ~/sharepoint/sites/YourSite
```

Keep the mount point outside the directory that holds your config files, so the mount never hides them.

### Persistent mount (systemd user service)

`~/.config/systemd/user/sp2rclone.service`:

```ini
[Unit]
Description=Mount SharePoint libraries via rclone
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
ExecStart=/usr/bin/rclone mount sp-all: %h/sharepoint/sites/YourSite \
  --config=/path/to/rclone.conf \
  --vfs-cache-mode writes
ExecStop=/bin/fusermount -u %h/sharepoint/sites/YourSite
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now sp2rclone
```

## Notes and limitations

- The mount is on-demand with a local cache, not a full sync.
- Each library is a separate rclone remote, so a site with many libraries means many concurrent connections. Watch your open-file limit (`ulimit -n`) on large sites.
- If two libraries share the same display name, their remote names stay unique but they show up under the same folder name in `sp-all`, so one shadows the other.
- `ls` quotes names containing spaces or symbols (`'Fire safety'`). The quotes are not part of the folder name.

## Development

```bash
uv run ruff check
```

## Layout

| File | Purpose |
| --- | --- |
| `main.py` | Entry point: builds and writes the rclone config |
| `api.py` | Microsoft Graph calls (token, site ID, list drives) |
| `settings.py` | Command-line arguments and `config.ini` loading |