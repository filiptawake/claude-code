import os
from flask import Flask, render_template, request, Response, stream_with_context
from dotenv import load_dotenv
from utils.data_processor import process_uploaded_file
from utils.claude_client import stream_analysis

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max upload


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    product_info = request.form.get("product_info", "").strip()
    competition_info = request.form.get("competition_info", "").strip()
    output_types = request.form.getlist("output_types")

    if not output_types:
        output_types = ["concepts", "scripts", "copy", "report"]

    # Process uploaded file if present
    ads_data = ""
    uploaded_file = request.files.get("ads_file")
    if uploaded_file and uploaded_file.filename:
        try:
            ads_data = process_uploaded_file(uploaded_file)
        except Exception as e:
            return Response(f"Eroare la procesarea fișierului: {e}", status=400)

    if not product_info and not competition_info and not ads_data:
        return Response("Completează cel puțin un câmp cu informații.", status=400)

    def generate():
        try:
            for chunk in stream_analysis(product_info, competition_info, ads_data, output_types):
                yield chunk
        except Exception as e:
            yield f"\n\n**Eroare:** {e}"

    return Response(
        stream_with_context(generate()),
        mimetype="text/plain",
        headers={"X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
