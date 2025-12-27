from flask import Flask, Response, abort
import os

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "audio")

print("✅ Flask Audio Server Started")
print("📁 Audio directory:", AUDIO_DIR)

@app.route("/audio/<filename>")
def serve_audio(filename):
    file_path = os.path.join(AUDIO_DIR, filename)

    print("🔊 Request for:", file_path)

    if not os.path.isfile(file_path):
        print("❌ File not found")
        abort(404)

    def generate():
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(4096)
                if not chunk:
                    break
                yield chunk

    return Response(
        generate(),
        mimetype="audio/mpeg",
        headers={
            "Content-Disposition": "inline; filename=" + filename,
            "Accept-Ranges": "bytes"
        }
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)