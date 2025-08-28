from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.pdfgen import canvas
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO
from datetime import datetime
import pytz  # Importando a biblioteca pytz
from flask_migrate import Migrate
from dotenv import load_dotenv
import os

app = Flask(__name__)
app.secret_key = "chave_secreta"

# Carrega variáveis de ambiente do .env
load_dotenv()

# Configuração do SQLite
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Inicialize o Migrate
migrate = Migrate(app, db)

# Modelos
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default="user")

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="Pendente")
    setor = db.Column(db.String(100), nullable=False)  # Novo campo 'setor'
    prioridade = db.Column(db.String(20), nullable=False, default="Média")  # Novo campo 'prioridade'
    data_hora = db.Column(db.DateTime, default=datetime.now(pytz.timezone('America/Sao_Paulo')))  # Usando horário de Brasília

class ResetToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(100), unique=True)
    username = db.Column(db.String(50))

# Cria as tabelas se não existirem
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
    if request.method == 'POST':
        setor = request.form['setor']
        descricao = request.form['descricao']
        prioridade = request.form['prioridade']
        
        # Use 'get' para evitar o KeyError caso o campo 'status' não seja enviado
        status = request.form.get('status', 'Pendente')  # valor padrão 'Pendente'

        # Criando o novo ticket sem o campo 'loja'
        new_ticket = Ticket(
            setor=setor,
            descricao=descricao,
            prioridade=prioridade,
            status=status,
            data_hora=datetime.now(pytz.timezone('America/Sao_Paulo'))  # Usando horário de Brasília
        )

        # Adiciona o novo ticket à sessão do banco de dados
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

@app.route("/export_pdf")
def export_pdf():
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.setFont("Helvetica", 7)
    y = 800

    p.drawString(50, y, "Lista de Chamados")
    y -= 30

    tickets = Ticket.query.order_by(Ticket.id).all()
    for t in tickets:
        data_str = t.data_hora.astimezone(pytz.timezone('America/Sao_Paulo')).strftime("%d/%m/%Y %H:%M:%S")
        p.drawString(
            50, y,
            f"ID: {t.id} | Setor: {t.setor} | Prioridade: {t.prioridade} | Status: {t.status} | Descrição: {t.descricao} | Data/Hora: {data_str}"
        )
        y -= 20
        if y < 50:
            p.showPage()
            y = 800

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
    p.setFont("Helvetica", 7)  # Usando uma fonte menor para evitar corte
    page_width, page_height = A4  # Pega o tamanho da página A4

    y = page_height - 50  # Começar um pouco abaixo do topo
    line_height = 12  # Defina a altura de cada linha de texto
    p.drawString(50, y, f"Lista de Chamados - {status}")
    y -= 30  # Espaço abaixo do título

    tickets = Ticket.query.filter_by(status=status).order_by(Ticket.id).all()
    
    if not tickets:
        p.drawString(50, y, "Nenhum chamado encontrado.")
    else:
        for t in tickets:
            data_str = t.data_hora.astimezone(pytz.timezone('America/Sao_Paulo')).strftime("%d/%m/%Y %H:%M:%S")
            text = f"ID: {t.id} | Setor: {t.setor} | Prioridade: {t.prioridade} | Status: {t.status} | Descrição: {t.descricao} | Data/Hora: {data_str}"

            text_width = p.stringWidth(text, "Helvetica", 8)

            # Verifica se a linha cabe na página
            if y - line_height < 50:  # Se não couber, cria uma nova página
                p.showPage()
                p.setFont("Helvetica", 8)
                y = page_height - 50  # Reinicia a posição no topo da página

            p.drawString(50, y, text)  # Desenha o texto
            y -= line_height  # Desce para a próxima linha

    p.save()
    buffer.seek(0)

    # Envia o PDF gerado para download
    filename = f"chamados_{status.lower()}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype="application/pdf")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)