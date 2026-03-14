import os
from flask import (
    Flask, render_template, request, Response,
    stream_with_context, redirect, url_for, flash,
)
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
from models import db, User, Analysis
from utils.data_processor import process_uploaded_file
from utils.claude_client import stream_analysis

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///marketing_agent.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Trebuie să fii autentificat."
login_manager.login_message_category = "error"

with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            return redirect(url_for("index"))
        flash("Nume de utilizator sau parolă incorectă.", "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")
        if len(username) < 3:
            flash("Minim 3 caractere pentru nume de utilizator.", "error")
        elif len(password) < 6:
            flash("Parola trebuie să aibă minim 6 caractere.", "error")
        elif password != confirm:
            flash("Parolele nu coincid.", "error")
        elif User.query.filter_by(username=username).first():
            flash("Acest nume de utilizator există deja.", "error")
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user, remember=True)
            return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ── Main ──────────────────────────────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
@login_required
def analyze():
    product_info     = request.form.get("product_info", "").strip()
    competition_info = request.form.get("competition_info", "").strip()
    output_types     = request.form.getlist("output_types") or ["concepts", "scripts", "copy", "report"]

    ads_data, ads_filename = "", ""
    uploaded_file = request.files.get("ads_file")
    if uploaded_file and uploaded_file.filename:
        try:
            ads_filename = uploaded_file.filename
            ads_data = process_uploaded_file(uploaded_file)
        except Exception as e:
            return Response(f"Eroare la procesarea fișierului: {e}", status=400)

    if not product_info and not competition_info and not ads_data:
        return Response("Completează cel puțin un câmp cu informații.", status=400)

    title   = (product_info[:80] if product_info else ads_filename or "Analiză META")
    user_id = current_user.id

    def generate():
        chunks = []
        try:
            for chunk in stream_analysis(product_info, competition_info, ads_data, output_types):
                chunks.append(chunk)
                yield chunk
        except Exception as e:
            msg = f"\n\n**Eroare:** {e}"
            chunks.append(msg)
            yield msg
        finally:
            result_text = "".join(chunks)
            if result_text:
                try:
                    with app.app_context():
                        db.session.add(Analysis(
                            user_id=user_id,
                            title=title,
                            product_info=product_info,
                            competition_info=competition_info,
                            ads_filename=ads_filename,
                            output_types=",".join(output_types),
                            result=result_text,
                        ))
                        db.session.commit()
                except Exception:
                    pass  # don't break the stream if save fails

    return Response(
        stream_with_context(generate()),
        mimetype="text/plain",
        headers={"X-Accel-Buffering": "no"},
    )


# ── History ───────────────────────────────────────────────────────────────────

@app.route("/history")
@login_required
def history():
    analyses = (
        Analysis.query
        .filter_by(user_id=current_user.id)
        .order_by(Analysis.created_at.desc())
        .all()
    )
    return render_template("history.html", analyses=analyses)


@app.route("/history/<int:analysis_id>")
@login_required
def analysis_detail(analysis_id):
    analysis = Analysis.query.filter_by(id=analysis_id, user_id=current_user.id).first_or_404()
    return render_template("analysis_detail.html", analysis=analysis)


@app.route("/history/<int:analysis_id>/delete", methods=["POST"])
@login_required
def delete_analysis(analysis_id):
    analysis = Analysis.query.filter_by(id=analysis_id, user_id=current_user.id).first_or_404()
    db.session.delete(analysis)
    db.session.commit()
    return redirect(url_for("history"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
