# horshmon

[![by horshmarny](https://img.shields.io/badge/by-horshmarny-1f6feb)](https://github.com/horshmarny200)
[![ci](https://github.com/horshmarny200/horshmon/actions/workflows/ci.yml/badge.svg)](https://github.com/horshmarny200/horshmon/actions/workflows/ci.yml)
![python](https://img.shields.io/badge/python-3.9%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)

Lightweight uptime, SSL certificate and server health monitor with Telegram alerts. **by horshmarny**

## What is this?

horshmon watches your websites and servers so you don't have to. It checks that your sites respond, that SSL certificates are not about to expire, that ports are open, and that the machine itself is not running out of disk, RAM or CPU. The moment something breaks, you get a message in Telegram. When it recovers, you get another one. Nothing in between — no spam.

No web UI, no database, no Docker. One small command and a single YAML file.

## What it checks

- **HTTP/HTTPS** — status code, response time, optional keyword in the page body
- **SSL certificates** — days until expiry, warning before it's too late
- **TCP ports** — Postgres, Redis, SMTP, game servers, anything
- **Local machine** — disk, RAM, CPU usage against your thresholds

## Requirements

- Python 3.9 or newer — check with `python --version` (or `python3 --version`)
- pip (comes with Python)
- git is optional — you can download a ZIP instead, see below

## Install and run, step by step

### 1. Get the code

With git:

```bash
git clone https://github.com/horshmarny200/horshmon.git
cd horshmon
```

Without git: on this page click the green **Code** button, then **Download ZIP**. Unzip the archive, open a terminal inside the unzipped folder (`cd horshmon`).

### 2. Install

```bash
pip install .
```

On Windows, if `pip` is not recognized:

```bash
py -m pip install .
```

On recent Ubuntu/Debian, if pip complains about an externally managed environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

Check that it works:

```bash
horshmon --version
```

If the `horshmon` command is not found, use `python -m horshmon` instead — it does exactly the same thing.

### 3. Create your config

```bash
horshmon init
```

This creates `config.yml` in the current folder. Open it in any text editor and replace the example targets with your own sites and servers (full format below).

### 4. Run it

```bash
horshmon check
```

Runs every check once, prints a table, exits. Exit code `0` means everything is up, `1` means something is down.

```
                horshmon by horshmarny
┏━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┓
┃ target      ┃ kind ┃ status ┃ detail                ┃
┡━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━┩
│ example     │ http │ OK     │ 200 in 231 ms         │
│ example     │ ssl  │ OK     │ expires in 214 days   │
│ google-dns  │ tcp  │ OK     │ port 53 open in 18 ms │
│ local       │ disk │ OK     │ 61% used              │
│ local       │ ram  │ OK     │ 43% used              │
│ local       │ cpu  │ OK     │ 7% used               │
└─────────────┴──────┴────────┴───────────────────────┘
```

To keep it running and get alerts:

```bash
horshmon watch
```

It loops forever (default every 60 seconds) and sends a Telegram message only when a state changes: down, recovered, or a certificate nearing expiry. Stop it with Ctrl+C.

To see the last results without re-checking:

```bash
horshmon status
```

### 5. Connect Telegram (optional but recommended)

1. In Telegram, open [@BotFather](https://t.me/BotFather) and send `/newbot`. Pick a name and a username, it gives you a token like `123456:ABC-DEF...`.
2. Open a chat with your new bot and send it any message (this is required, otherwise the bot can't message you first).
3. In a browser open `https://api.telegram.org/bot<TOKEN>/getUpdates` (replace `<TOKEN>` with your token). Find `"chat":{"id":123456789,...}` — that number is your chat id.
4. Put both values into `config.yml`:

```yaml
telegram:
  token: "123456:ABC-DEF..."
  chat_id: "123456789"
```

Done. The next time something goes down, the alert lands in your Telegram:

```
[DOWN] example (http)
status 503

-- horshmon 1.0.0 by horshmarny
```

```
[RECOVERED] example (http)
200 in 214 ms

-- horshmon 1.0.0 by horshmarny
```

State is saved in `state.json`, so restarting the tool does not re-send old alerts.

## Configuration

Full `config.yml` format:

```yaml
interval: 60          # seconds between rounds in watch mode
timeout: 10           # per-check network timeout, seconds
ssl_warn_days: 14     # warn when a certificate has this many days left

telegram:
  token: ""           # bot token from @BotFather, empty = alerts disabled
  chat_id: ""

local:
  disk: 90            # alert when disk usage goes above 90%
  ram: 90             # same for RAM
  cpu: 90             # same for CPU; set any of the three to false to disable

targets:
  - name: example
    url: https://example.com
    keyword: Example Domain   # optional: this text must appear in the page
  - name: api
    url: https://api.example.com/health
    expect: 200               # optional: require this exact status code
  - name: postgres
    host: 10.0.0.5
    port: 5432
  - name: mail
    host: mail.example.com
    port: 465
    ssl: true                 # optional: also check the certificate on a TCP target
```

Every `https://` URL target automatically gets an SSL expiry check — no extra config needed.

You can point the tool at any config and state file:

```bash
horshmon check -c /etc/horshmon/config.yml -s /var/lib/horshmon/state.json
```

`config.yml` contains your bot token and is gitignored. Don't commit it.

## Run it forever

### cron (simplest)

```cron
*/5 * * * * cd /opt/horshmon && horshmon check -c config.yml -s state.json >> /var/log/horshmon.log 2>&1
```

### systemd

```ini
[Unit]
Description=horshmon
After=network-online.target

[Service]
ExecStart=/usr/local/bin/horshmon watch -c /etc/horshmon/config.yml -s /var/lib/horshmon/state.json
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now horshmon
```

## Development

```bash
pip install -e . pytest
pytest -q
```

## License

MIT, Copyright (c) 2026 horshmarny. Keep the copyright notice intact.

horshmon is authored **by horshmarny**. If you fork it, credit stays.