import os
import errno
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from flask import Flask, request, redirect, flash, render_template_string, url_for, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key-change-later")  # needed for flash messages
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB cap

UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

STORAGE_MSG = "Storage is temporarily unavailable. Please try again in a moment."

# os.listdir hits the NFS mount and can block for ~40s if the NAS drops (the
# kernel's TCP timeout, which mount options can't shorten much). We run it in a
# worker thread and give up after LIST_TIMEOUT so a stalled mount never hangs
# the request. Stuck threads free themselves once the NFS call finally errors.
_io_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="fs")
LIST_TIMEOUT = 3.0  # seconds to wait for a directory listing before degrading


def list_files():
    # Retry once on a stale handle: an NFS blip usually throws ESTALE/EIO on
    # the first touch, then succeeds on the next as the client refreshes.
    for attempt in range(2):
        future = _io_pool.submit(os.listdir, UPLOAD_FOLDER)
        try:
            return future.result(timeout=LIST_TIMEOUT)
        except OSError as e:
            if attempt == 0 and getattr(e, "errno", None) in (errno.ESTALE, errno.EIO):
                continue
            raise


@app.errorhandler(413)
def too_large(e):
    flash("File too large.")
    return redirect(url_for("home"))


@app.errorhandler(OSError)
def storage_error(e):
    # App-wide safety net: any storage error that a route didn't handle
    # (e.g. a download during an outage) lands here instead of a raw 500.
    flash(STORAGE_MSG)
    return redirect(url_for("home"))


@app.route("/")
def home():
    try:
        files = list_files()
        storage_ok = True
    except (OSError, FuturesTimeout):
        files, storage_ok = [], False
    return render_template_string("""
        <h1>File Drop</h1>
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for msg in messages %}
                    <p>{{ msg }}</p>
                {% endfor %}
            {% endif %}
        {% endwith %}
        {% if not storage_ok %}
            <p><strong>Storage temporarily unavailable</strong> — the file list may be incomplete. Try refreshing in a moment.</p>
        {% endif %}
        <form method="POST" action="/upload" enctype="multipart/form-data">
            <input type=file name=file>
            <button type="Submit">Upload File</button>
        </form>
        <h2>Files</h2>
        {% if files %}
          <ul>
            {% for name in files %}
              <li><a href="{{ url_for('download', filename=name) }}">{{ name }}</a></li>
            {% endfor %}
          </ul>
        {% elif storage_ok %}
          <p>No files yet.</p>
        {% endif %}
    """, files=files, storage_ok=storage_ok)


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]

    if file.filename == "":
        return redirect(url_for("home"))

    filename = secure_filename(file.filename)
    if filename == "":
        flash("Invalid file name.")
        return redirect(url_for("home"))

    save_path = os.path.join(UPLOAD_FOLDER, filename)
    try:
        if os.path.exists(save_path):
            flash(f"A file named '{filename}' already exists.")
            return redirect(url_for("home"))
        file.save(save_path)
    except OSError:
        # A blip mid-save can leave a truncated file behind — clean it up.
        try:
            if os.path.exists(save_path):
                os.remove(save_path)
        except OSError:
            pass
        flash(STORAGE_MSG)
        return redirect(url_for("home"))

    flash(f"Uploaded {file.filename}")
    return redirect(url_for("home"))


@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)


if __name__ == "__main__":
    # threaded so one slow request (e.g. a stalled NFS write) can't block
    # every other client on the single-threaded dev server.
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
