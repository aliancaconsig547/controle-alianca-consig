import os
import io
import base64
from flask import Flask, render_template, request, url_for, redirect, flash, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, func
from dotenv import load_dotenv
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from weasyprint import HTML
from datetime import datetime

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

app = Flask(__name__)

# --- CONFIGURAÇÕES GERAIS E DO BANCO DE DADOS ---
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///local_test.db')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- CONFIGURAÇÃO DO SISTEMA DE LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, faça o login para acessar esta página."
login_manager.login_message_category = "info"


# --- MODELO DO BANCO DE DADOS (TABELA 'registros') ---
class Registro(db.Model):
    __tablename__ = 'registros'
    id = db.Column(db.Integer, primary_key=True)
    nome_cliente = db.Column(db.String(150), nullable=False)
    cpf = db.Column(db.String(14), nullable=False)
    valor_quitado = db.Column(db.Float, nullable=True)
    data_quitacao = db.Column(db.String(10), nullable=False)
    supervisor = db.Column(db.String(100), nullable=False)
    vendedor = db.Column(db.String(100), nullable=False)
    investidor = db.Column(db.String(100), nullable=True)
    percentual_investidor = db.Column(db.Integer, nullable=True)
    percentual_comissao = db.Column(db.Integer, nullable=False)
    investidor_fora = db.Column(db.Boolean, default=False, nullable=False)
    criado_em = db.Column(db.DateTime(timezone=True), server_default=func.now())
    valor_contrato = db.Column(db.Float, nullable=False)
    custo_produto = db.Column(db.Float, nullable=False)
    liquido_empresa = db.Column(db.Float, nullable=False)

    # --- NOVOS CAMPOS ADICIONADOS ---
    bancos_quitados = db.Column(db.String(200), nullable=True)
    banco_contrato = db.Column(db.String(200), nullable=True)
    agencia = db.Column(db.String(100), nullable=True)

# --- MODELO DE USUÁRIO E AUTENTICAÇÃO ---
class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

admin_user = User(id='1', username=os.environ.get('ADMIN_USERNAME'), password_hash=os.environ.get('ADMIN_PASSWORD_HASH'))

@login_manager.user_loader
def load_user(user_id):
    if user_id == '1': return admin_user
    return None

with app.app_context():
    db.create_all()

# --- ROTAS DE AUTENTICAÇÃO ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('index'))
    if request.method == 'POST':
        username, password = request.form['username'], request.form['password']
        if username == admin_user.username and admin_user.check_password(password):
            login_user(admin_user, remember=True)
            return redirect(url_for('index'))
        else:
            flash('Usuário ou senha inválidos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi desconectado com sucesso.', 'success')
    return redirect(url_for('login'))

# --- ROTAS DA APLICAÇÃO ---

# ROTA PRINCIPAL (CADASTRAR NOVA OPERAÇÃO)
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        valor_contrato = float(request.form.get('valor_contrato', 0))
        valor_quitado = float(request.form.get('valor_quitado', 0))
        custo_produto = float(request.form.get('custo_produto', 0))
        percentual_comissao = int(request.form.get('percentual_comissao', 0))
        
        valor_comissao = valor_contrato * (percentual_comissao / 100)
        liquido_empresa = valor_contrato - valor_quitado - valor_comissao - custo_produto

        novo_registro = Registro(
            valor_contrato=valor_contrato,
            custo_produto=custo_produto,
            liquido_empresa=liquido_empresa,
            nome_cliente=request.form['nome_cliente'],
            cpf=request.form['cpf'],
            valor_quitado=valor_quitado,
            data_quitacao=request.form['data_quitacao'],
            supervisor=request.form['supervisor'],
            vendedor=request.form['vendedor'],
            investidor=request.form.get('investidor'),
            percentual_investidor=int(request.form.get('percentual_investidor') or 0),
            percentual_comissao=percentual_comissao,
            investidor_fora='investidor_fora' in request.form,
            
            # --- LÓGICA PARA NOVOS CAMPOS ---
            bancos_quitados=request.form.get('bancos_quitados'),
            banco_contrato=request.form.get('banco_contrato'),
            agencia=request.form.get('agencia')
        )
        db.session.add(novo_registro)
        db.session.commit()
        flash('Operação cadastrada com sucesso!', 'success')
        return redirect(url_for('registros'))
    return render_template('index.html')

# ROTA PARA EDITAR UMA OPERAÇÃO
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    registro = Registro.query.get_or_404(id)
    if request.method == 'POST':
        registro.nome_cliente = request.form['nome_cliente']
        registro.cpf = request.form['cpf']
        registro.data_quitacao = request.form['data_quitacao']
        registro.supervisor = request.form['supervisor']
        registro.vendedor = request.form['vendedor']
        registro.investidor = request.form.get('investidor')
        registro.percentual_investidor = int(request.form.get('percentual_investidor') or 0)
        registro.investidor_fora = 'investidor_fora' in request.form
        
        # --- LÓGICA PARA NOVOS CAMPOS ---
        registro.bancos_quitados = request.form.get('bancos_quitados')
        registro.banco_contrato = request.form.get('banco_contrato')
        registro.agencia = request.form.get('agencia')
        
        registro.valor_contrato = float(request.form.get('valor_contrato', 0))
        registro.valor_quitado = float(request.form.get('valor_quitado', 0))
        registro.custo_produto = float(request.form.get('custo_produto', 0))
        registro.percentual_comissao = int(request.form.get('percentual_comissao', 0))

        valor_comissao = registro.valor_contrato * (registro.percentual_comissao / 100)
        registro.liquido_empresa = registro.valor_contrato - registro.valor_quitado - valor_comissao - registro.custo_produto
        
        db.session.commit()
        flash('Operação atualizada com sucesso!', 'success')
        return redirect(url_for('registros'))
    
    return render_template('edit.html', registro=registro)

# ROTA PARA EXCLUIR UMA OPERAÇÃO
@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    registro_para_excluir = Registro.query.get_or_404(id)
    try:
        db.session.delete(registro_para_excluir)
        db.session.commit()
        flash('Registro excluído com sucesso!', 'success')
    except:
        db.session.rollback()
        flash('Erro ao excluir o registro.', 'danger')
    return redirect(url_for('registros'))

# FUNÇÃO AUXILIAR PARA APLICAR FILTROS
def get_filtered_query(args):
    query = Registro.query
    search_query = args.get('q')
    start_date = args.get('start_date')
    end_date = args.get('end_date')
    supervisor_filter = args.get('supervisor')

    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.filter(or_(Registro.nome_cliente.ilike(search_pattern), Registro.cpf.ilike(search_pattern), Registro.vendedor.ilike(search_pattern)))
    if start_date:
        query = query.filter(Registro.data_quitacao >= start_date)
    if end_date:
        query = query.filter(Registro.data_quitacao <= end_date)
    if supervisor_filter:
        query = query.filter(Registro.supervisor == supervisor_filter)
    
    return query

# ROTA DE RELATÓRIOS (VISUALIZAR REGISTROS)
@app.route('/registros')
@login_required
def registros():
    query = get_filtered_query(request.args)
    
    total_liquido = query.with_entities(func.sum(Registro.liquido_empresa)).scalar() or 0.0
    registros_db = query.order_by(Registro.criado_em.desc()).all()
    supervisores = db.session.query(Registro.supervisor).distinct().order_by(Registro.supervisor).all()
    
    return render_template('registros.html', 
                           registros=registros_db, 
                           supervisores=supervisores,
                           total_liquido=total_liquido,
                           request_args=request.args)

# ROTA PARA DOWNLOAD DO RELATÓRIO EM PDF
@app.route('/download_pdf')
@login_required
def download_pdf():
    query = get_filtered_query(request.args)
    registros = query.order_by(Registro.data_quitacao.asc()).all()
    total_liquido = query.with_entities(func.sum(Registro.liquido_empresa)).scalar() or 0.0

    logo_data_uri = None
    try:
        with open('static/images/logoheader.png', 'rb') as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            logo_data_uri = f'data:image/png;base64,{encoded_string}'
    except FileNotFoundError:
        logo_data_uri = ''

    html_renderizado = render_template(
        'report_template.html', 
        registros=registros,
        total_liquido=total_liquido,
        data_hoje=datetime.now().strftime('%d/%m/%Y'),
        request_args=request.args,
        logo_data_uri=logo_data_uri
    )
    
    pdf = HTML(string=html_renderizado, base_url=request.base_url).write_pdf()

    return Response(
        pdf,
        mimetype='application/pdf',
        headers={'Content-Disposition': 'attachment;filename=relatorio_operacoes.pdf'}
    )

# --- EXECUÇÃO DA APLICAÇÃO ---
if __name__ == '__main__':
    app.run(debug=True)