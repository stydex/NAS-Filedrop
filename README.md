# File Drop

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Flask](https://img.shields.io/badge/Flask-3.0+-green)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

A small self-hosted web app for sharing files over a local network. Open the page in a browser, upload a file, and anyone else on the same network can see and download it.

Runs anywhere Python runs essentially. A regular computer is enough (an optional guide for running it 24/7 on a Raspberry Pi with network storage is at the end).

## Features

- Upload and download files through a browser, no client software
- Sanitizes filenames and won't overwrite existing files
- Configurable upload size limit (200 MB default)
- deployment-agnostic application, so the same code works with different environments (environment variables are used)

## Requirements

- Python 3.8+
- Flask

## Setup

```
git clone <repository-url>
cd <repository-folder>
python -m venv .venv
```
---
Activate the virtual environment.
Windows:

```
.venv\Scripts\activate
```
macOS/Linux:
```
source .venv/bin/activate
```

Install and run:
```
pip install Flask
python main.py
```

Open `http://127.0.0.1:5000`. To reach it from other devices, use the machine's local IP instead (e.g. `http://192.168.1.50:5000`) — the app already listens on all interfaces.

## Configuration

Two optional environment variables, with defaults if unset:

- `UPLOAD_FOLDER` — where files are saved. Defaults to a local `uploads/` folder.
- `SECRET_KEY` — signs the cookie behind the on-screen status messages. Set a real random value for long-running setups.

```
UPLOAD_FOLDER=/path/to/storage SECRET_KEY=your-random-value python main.py
```

With nothing set, `main.py` saves to `uploads/`. Replace the placeholder `your-random-value` with your generated secret key.

## Optional: running it in a Raspberry Pi & NAS

The preferable setup for keeping it always on: a Raspberry Pi running the app continuously, saving uploads to a NAS. None of this is app-specific or required, it is purely just the ideal place for a Flask app of this scale to live in. NAS application is also accessible since `UPLOAD_FOLDER` could be pointed to any network mount.

Replace placeholders with your own: `<NAS-IP>`, `<NAS-EXPORT-PATH>`, `<PI-USER>`, `<PROJECT-DIR>`.

---
## On the Raspberry Pi do the following:

### Mount the NAS

```
sudo apt install nfs-common
sudo mkdir -p /mnt/filedrop
sudo mount -t nfs <NAS-IP>:<NAS-EXPORT-PATH> /mnt/filedrop
```

Make it permanent by adding this to `/etc/fstab`, then run `sudo mount -a` to test:
```
<NAS-IP>:<NAS-EXPORT-PATH>  /mnt/filedrop  nfs  defaults,_netdev  0  0
```

### Install the app

```
git clone <repository-url>
cd <PROJECT-DIR>
python3 -m venv .venv
source .venv/bin/activate
pip install Flask
```

### Run as a service

Create `/etc/systemd/system/filedrop.service`:

```ini
[Unit]
Description=File Drop Flask app
After=network-online.target
Wants=network-online.target

[Service]
User=<PI-USER>
WorkingDirectory=/home/<PI-USER>/<PROJECT-DIR>
Environment="UPLOAD_FOLDER=/mnt/filedrop"
Environment="SECRET_KEY=<your-random-value>"
ExecStart=/home/<PI-USER>/<PROJECT-DIR>/.venv/bin/python /home/<PI-USER>/<PROJECT-DIR>/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Generate a key with `python3 -c "import secrets; print(secrets.token_hex(32))"`, then enable it:

```
sudo systemctl daemon-reload
sudo systemctl enable filedrop
sudo systemctl start filedrop
```
---
### Optional: cleaner address with nginx

Puts the app on a normal web port so the URL needs no `:5000`. Use a different port (e.g. 8080) if port 80 is taken.

```
sudo apt install nginx
```

Create `/etc/nginx/sites-available/filedrop`:
```nginx
server {
    listen 8080;
    server_name _;
    client_max_body_size 200M;
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Enable it:
```
sudo ln -s /etc/nginx/sites-available/filedrop /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

On most networks the Pi answers to `<hostname>.local`, so `http://raspberrypi.local:8080` works without an IP.

## Notes

- For trusted local networks only. No login; don't expose it to the public internet as is.
- Uses Flask's built-in server, fine for home use.

## Planned

- Deleting files functionality on the web page
- A nicer interface

## License

MIT
