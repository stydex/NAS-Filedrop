import os
from flask import Flask, request, redirect, flash, render_template_string, url_for, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "dev-key-change-later"  # needed for flash messages

UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/")
def home():
    files = os.listdir(UPLOAD_FOLDER)
    return render_template_string("""
        <h1>File Drop</h1>
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for msg in messages %}
                    <p>{{ msg }}</p>
                {% endfor %}
            {% endif %}
        {% endwith %}
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
        {% else %}
          <p>No files yet.</p>
        {% endif %}
    """, files=files)


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]

    if file.filename == "":
        return redirect(url_for("home"))

    filename = secure_filename(file.filename)

    save_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(save_path):
        flash(f"A file named '{filename}' already exists.")
        return redirect(url_for("home"))

    file.save(save_path)
    flash(f"Uploaded {file.filename}")
    return redirect(url_for("home"))


@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)