import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO
from datetime import datetime
import pytz
from flask_migrate import Migrate

# Inicializa a aplicação
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "chave_secreta")

# Configuração do Banco de Dados (Neon via variável de ambiente)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///meus_chamados.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Inicializa Migrate
migrate = Migrate(app, db)

# ===========================
# Modelos
# ===========================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default="user")

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="Pendente")
    setor = db.Column(db.String(100), nullable=False)
    prioridade = db.Column(db.String(20), nullable=False, default="Média")
    data_hora = db.Column(db.DateTime, default=datetime.now(pytz.timezone('America/Sao_Paulo')))

class ResetToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(100), unique=True)
    username = db.Column(db.String(50))

# ===========================
# Inicialização do banco
# ===========================
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username="Matheus").first():
        admin = User(
            username="Matheus",
            password=generate_password_hash("Vi2310"),
            role="admin"
        )
        db.session.add(admin)
        db.session.commit()

# ===========================
# Rotas
# ===========================
@app.route("/")
def home():
    if "username" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session["username"] = username
            session["role"] = user.role
            flash("Login realizado com sucesso!", "success")
            return redirect(url_for("dashboard"))
        flash("Usuário ou senha inválidos", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Você saiu do sistema.", "info")
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if "username" not in session or session["role"] != "admin":
        flash("Apenas administradores podem cadastrar novos usuários.", "danger")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if User.query.filter_by(username=username).first():
            flash("Usuário já existe.", "warning")
        else:
            new_user = User(username=username, password=generate_password_hash(password))
            db.session.add(new_user)
            db.session.commit()
            flash("Usuário cadastrado com sucesso!", "success")
            return redirect(url_for("dashboard"))
    return render_template("register.html")

@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    status = request.args.get("status")

    query = Ticket.query

    if status in ("Pendente", "Resolvido"):
        query = query.filter_by(status=status)

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=pytz.timezone('America/Sao_Paulo'))
            query = query.filter(Ticket.data_hora >= start_dt)
        except ValueError:
            flash("Formato de data inválido.", "danger")
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=pytz.timezone('America/Sao_Paulo'))
            query = query.filter(Ticket.data_hora <= end_dt)
        except ValueError:
            flash("Formato de data inválido.", "danger")

    tickets = query.order_by(Ticket.id.desc()).all()
    return render_template("dashboard.html", tickets=tickets)

@app.route('/create_ticket', methods=['POST'])
def create_ticket():
    setor = request.form['setor']
    descricao = request.form['descricao']
    prioridade = request.form['prioridade']
    status = request.form.get('status', 'Pendente')

    new_ticket = Ticket(
        setor=setor,
        descricao=descricao,
        prioridade=prioridade,
        status=status,
        data_hora=datetime.now(pytz.timezone('America/Sao_Paulo'))
    )
    db.session.add(new_ticket)
    db.session.commit()

    flash("Chamado criado com sucesso!", "success")
    return redirect(url_for("dashboard"))

@app.route("/mark_resolved/<int:ticket_id>")
def mark_resolved(ticket_id):
    if "username" not in session:
        return redirect(url_for("login"))
    ticket = Ticket.query.get(ticket_id)
    if ticket:
        ticket.status = "Resolvido"
        db.session.commit()
        flash("Chamado marcado como resolvido.", "info")
    return redirect(url_for("dashboard"))

@app.route("/delete_ticket/<int:ticket_id>")
def delete_ticket(ticket_id):
    if "username" not in session:
        return redirect(url_for("login"))
    ticket = Ticket.query.get(ticket_id)
    if ticket:
        db.session.delete(ticket)
        db.session.commit()
        flash("Chamado excluído.", "warning")
    return redirect(url_for("dashboard"))

@app.route("/recover_password", methods=["GET", "POST"])
def recover_password():
    if request.method == "POST":
        username = request.form["username"]
        user = User.query.filter_by(username=username).first()
        if user:
            token_str = f"token_{username}_{datetime.now().timestamp()}"
            token = ResetToken(token=token_str, username=username)
            db.session.add(token)
            db.session.commit()
            flash(f"Link de redefinição: /reset_password/{token_str}", "info")
        else:
            flash("Usuário não encontrado.", "warning")
    return render_template("recover_password.html")

@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    token_entry = ResetToken.query.filter_by(token=token).first()
    if not token_entry:
        flash("Token inválido ou expirado.", "danger")
        return redirect(url_for("login"))
    if request.method == "POST":
        new_password = request.form["password"]
        user = User.query.filter_by(username=token_entry.username).first()
        if user:
            user.password = generate_password_hash(new_password)
            db.session.delete(token_entry)
            db.session.commit()
            flash("Senha redefinida com sucesso!", "success")
            return redirect(url_for("login"))
    return render_template("reset_password.html", token=token)

# ===========================
# Exportação PDF
# ===========================
@app.route("/export_pdf")
def export_pdf():
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 7)
    page_width, page_height = A4
    y = page_height - 50

    p.drawString(50, y, "Lista de Chamados")
    y -= 30

    tickets = Ticket.query.order_by(Ticket.id).all()
    for t in tickets:
        data_str = t.data_hora.astimezone(pytz.timezone('America/Sao_Paulo')).strftime("%d/%m/%Y %H:%M:%S")
        text = f"ID: {t.id} | Setor: {t.setor} | Prioridade: {t.prioridade} | Status: {t.status} | Descrição: {t.descricao} | Data/Hora: {data_str}"
        if y < 50:
            p.showPage()
            p.setFont("Helvetica", 7)
            y = page_height - 50
        p.drawString(50, y, text)
        y -= 12

    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="chamados.pdf", mimetype='application/pdf')

@app.route("/export_pdf_status/<status>")
def export_pdf_status(status):
    if status not in ("Pendente", "Resolvido"):
        flash("Status inválido!", "danger")
        return redirect(url_for("dashboard"))

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 7)
    page_width, page_height = A4
    y = page_height - 50

    p.drawString(50, y, f"Lista de Chamados - {status}")
    y -= 30

    tickets = Ticket.query.filter_by(status=status).order_by(Ticket.id).all()
    if not tickets:
        p.drawString(50, y, "Nenhum chamado encontrado.")
    else:
        for t in tickets:
            data_str = t.data_hora.astimezone(pytz.timezone('America/Sao_Paulo')).strftime("%d/%m/%Y %H:%M:%S")
            text = f"ID: {t.id} | Setor: {t.setor} | Prioridade: {t.prioridade} | Status: {t.status} | Descrição: {t.descricao} | Data/Hora: {data_str}"
            if y < 50:
                p.showPage()
                p.setFont("Helvetica", 7)
                y = page_height - 50
            p.drawString(50, y, text)
            y -= 12

    p.save()
    buffer.seek(0)
    filename = f"chamados_{status.lower()}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype="application/pdf")

# ===========================
# Configuração para o Vercel
# ===========================
# O Vercel vai procurar por "app"
app = app
