import os
import io
import base64
from flask import Flask, render_template, request, url_for, redirect, flash, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, func, text
from dotenv import load_dotenv
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from weasyprint import HTML
from datetime import datetime

# --- IMPORTAÇÕES DE SEGURANÇA ---
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, FloatField, IntegerField, BooleanField, PasswordField, SelectField
from wtforms.validators import DataRequired, Length, Optional

# Carrega as variáveis de ambiente
load_dotenv()

app = Flask(__name__)

# --- CONFIGURAÇÕES ---
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chave_padrao_desenvolvimento')
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///local_test.db')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicialização de Extensões
db = SQLAlchemy(app)
csrf = CSRFProtect(app) 

# --- LOGIN MANAGER ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, faça o login para acessar esta página."
login_manager.login_message_category = "info"

# --- FUNÇÃO AUXILIAR PARA LIMPAR DINHEIRO (TEXTO -> FLOAT) ---
def parse_brl(valor_str):
    """
    Transforma 'R$ 1.500,50' em 1500.50
    """
    if not valor_str:
        return 0.0
    if isinstance(valor_str, float) or isinstance(valor_str, int):
        return float(valor_str)
        
    # Remove R$, espaços e pontos de milhar
    limpo = valor_str.replace('R$', '').replace('.', '').replace(' ', '')
    # Troca a vírgula decimal por ponto
    limpo = limpo.replace(',', '.')
    
    try:
        return float(limpo)
    except ValueError:
        return 0.0

# --- MODELO DO BANCO DE DADOS ---
class Registro(db.Model):
    __tablename__ = 'registros'
    id = db.Column(db.Integer, primary_key=True)
    nome_cliente = db.Column(db.String(150), nullable=False)
    cpf = db.Column(db.String(14), nullable=False)
    
    # Valores Financeiros
    valor_contrato = db.Column(db.Float, nullable=False)
    valor_quitado = db.Column(db.Float, nullable=True)
    custo_produto = db.Column(db.Float, nullable=False)
    percentual_comissao = db.Column(db.Integer, nullable=False)
    
    # Novos Campos Solicitados
    custos_contrato = db.Column(db.Float, nullable=True) # Gasolina, cartório etc
    valor_devolvido = db.Column(db.Float, nullable=True)
    data_devolucao = db.Column(db.String(10), nullable=True)
    
    # Investidor
    investidor = db.Column(db.String(100), nullable=True)
    percentual_investidor = db.Column(db.Integer, nullable=True)
    investidor_fora = db.Column(db.Boolean, default=False, nullable=False)
    
    # Detalhes Operacionais
    bancos_quitados = db.Column(db.String(200), nullable=True)
    banco_contrato = db.Column(db.String(200), nullable=True)
    agencia = db.Column(db.String(100), nullable=True)
    supervisor = db.Column(db.String(100), nullable=False)
    vendedor = db.Column(db.String(100), nullable=False)
    data_quitacao = db.Column(db.String(10), nullable=False)
    
    # Resultado Calculado
    liquido_empresa = db.Column(db.Float, nullable=False)
    criado_em = db.Column(db.DateTime(timezone=True), server_default=func.now())

# --- USER MOCK ---
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

# --- FORMS (Flask-WTF) ---
class LoginForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired()])
    password = PasswordField('Senha', validators=[DataRequired()])

class OperacaoForm(FlaskForm):
    nome_cliente = StringField('Nome Cliente', validators=[Optional()])
    cpf = StringField('CPF', validators=[Optional()])
    
    # Campos Monetários (String para aceitar máscara R$)
    valor_contrato = StringField('Valor Contrato', validators=[Optional()])
    custo_produto = StringField('Custo Produto (Banco)', validators=[Optional()])
    valor_quitado = StringField('Valor Quitado', validators=[Optional()])
    
    # Novos inputs financeiros
    custos_contrato = StringField('Custos Extras (Gasolina/Cartório)', validators=[Optional()])
    valor_devolvido = StringField('Valor Devolvido', validators=[Optional()])
    data_devolucao = StringField('Data Devolução', validators=[Optional()])
    
    percentual_comissao = SelectField('% Comissão', choices=[('20', '20%'), ('30', '30%')], coerce=int, validators=[Optional()])
    
    investidor = StringField('Investidor', validators=[Optional()])
    percentual_investidor = SelectField('% Investidor', choices=[('0', '0%'), ('7', '7%'), ('8', '8%'), ('9', '9%'), ('10', '10%')], coerce=int, default=0)
    investidor_fora = BooleanField('Investidor de Fora')
    
    bancos_quitados = StringField('Bancos Quitados')
    banco_contrato = StringField('Banco Contrato')
    agencia = StringField('Agência')
    
    supervisor = StringField('Supervisor', validators=[Optional()])
    vendedor = StringField('Vendedor', validators=[Optional()])
    data_quitacao = StringField('Data de Quitação', validators=[Optional()]) 

with app.app_context():
    db.create_all()

# --- FUNÇÃO DE CÁLCULO CENTRALIZADA ---
def calcular_liquido_empresa(form):
    v_contrato = parse_brl(form.valor_contrato.data)
    v_quitado = parse_brl(form.valor_quitado.data)
    v_custo_prod = parse_brl(form.custo_produto.data)
    v_custos_extras = parse_brl(form.custos_contrato.data) # Novo
    v_devolvido = parse_brl(form.valor_devolvido.data)     # Novo
    
    p_comissao = form.percentual_comissao.data or 0
    
    valor_comissao = v_contrato * (p_comissao / 100)
    
    # FÓRMULA ATUALIZADA:
    # Liquido = Contrato - Quitado - Comissão - CustoProduto - CustosExtras - Devolvido
    liquido = v_contrato - v_quitado - valor_comissao - v_custo_prod - v_custos_extras - v_devolvido
    return liquido

# --- ROTAS ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        if form.username.data == admin_user.username and admin_user.check_password(form.password.data):
            login_user(admin_user, remember=True)
            return redirect(url_for('index'))
        else:
            flash('Usuário ou senha inválidos.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi desconectado.', 'success')
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    form = OperacaoForm()
    
    if form.validate_on_submit():
        liquido_final = calcular_liquido_empresa(form)

        novo_registro = Registro(
            nome_cliente=form.nome_cliente.data or "Sem Nome",
            cpf=form.cpf.data or "",
            valor_contrato=parse_brl(form.valor_contrato.data),
            custo_produto=parse_brl(form.custo_produto.data),
            valor_quitado=parse_brl(form.valor_quitado.data),
            
            # Novos campos salvando no banco
            custos_contrato=parse_brl(form.custos_contrato.data),
            valor_devolvido=parse_brl(form.valor_devolvido.data),
            data_devolucao=form.data_devolucao.data or "",

            percentual_comissao=form.percentual_comissao.data or 0,
            investidor=form.investidor.data,
            percentual_investidor=form.percentual_investidor.data,
            investidor_fora=form.investidor_fora.data,
            bancos_quitados=form.bancos_quitados.data,
            banco_contrato=form.banco_contrato.data,
            agencia=form.agencia.data,
            supervisor=form.supervisor.data or "Não Informado",
            vendedor=form.vendedor.data or "Não Informado",
            data_quitacao=form.data_quitacao.data or datetime.now().strftime('%Y-%m-%d'),
            
            liquido_empresa=liquido_final
        )
        db.session.add(novo_registro)
        db.session.commit()
        flash('Operação cadastrada com sucesso!', 'success')
        return redirect(url_for('registros'))
        
    if form.errors:
        for err_msg in form.errors.values():
            flash(f'Erro no formulário: {err_msg}', 'danger')

    return render_template('index.html', form=form)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    registro = Registro.query.get_or_404(id)
    form = OperacaoForm(obj=registro) 
    
    if form.validate_on_submit():
        form.populate_obj(registro) 
        
        # Conversão manual dos campos monetários
        registro.valor_contrato = parse_brl(form.valor_contrato.data)
        registro.valor_quitado = parse_brl(form.valor_quitado.data)
        registro.custo_produto = parse_brl(form.custo_produto.data)
        registro.custos_contrato = parse_brl(form.custos_contrato.data)
        registro.valor_devolvido = parse_brl(form.valor_devolvido.data)
        
        # Recalcula o líquido na edição
        registro.liquido_empresa = calcular_liquido_empresa(form)
        
        db.session.commit()
        flash('Operação atualizada com sucesso!', 'success')
        return redirect(url_for('registros'))
    
    # Formata valores para exibir R$ no input ao abrir edição
    if request.method == 'GET':
        campos_moeda = ['valor_contrato', 'custo_produto', 'valor_quitado', 'custos_contrato', 'valor_devolvido']
        for campo in campos_moeda:
            valor = getattr(registro, campo)
            if valor:
                getattr(form, campo).data = f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    return render_template('edit.html', form=form, registro=registro)

@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    registro = Registro.query.get_or_404(id)
    try:
        db.session.delete(registro)
        db.session.commit()
        flash('Registro excluído.', 'success')
    except:
        db.session.rollback()
        flash('Erro ao excluir.', 'danger')
    return redirect(url_for('registros'))

# --- FILTROS E RELATÓRIOS ---
def get_filtered_query(args):
    query = Registro.query
    search = args.get('q')
    start = args.get('start_date')
    end = args.get('end_date')
    sup = args.get('supervisor')

    if search:
        patt = f"%{search}%"
        query = query.filter(or_(Registro.nome_cliente.ilike(patt), Registro.cpf.ilike(patt), Registro.vendedor.ilike(patt)))
    if start: query = query.filter(Registro.data_quitacao >= start)
    if end: query = query.filter(Registro.data_quitacao <= end)
    if sup: query = query.filter(Registro.supervisor == sup)
    return query

@app.route('/registros')
@login_required
def registros():
    query = get_filtered_query(request.args)
    total_liquido = query.with_entities(func.sum(Registro.liquido_empresa)).scalar() or 0.0
    registros_db = query.order_by(Registro.criado_em.desc()).all()
    supervisores = db.session.query(Registro.supervisor).distinct().order_by(Registro.supervisor).all()
    form = OperacaoForm() 
    return render_template('registros.html', registros=registros_db, supervisores=supervisores, total_liquido=total_liquido, request_args=request.args, form=form)

@app.route('/download_pdf')
@login_required
def download_pdf():
    query = get_filtered_query(request.args)
    registros = query.order_by(Registro.data_quitacao.asc()).all()
    total_liquido = query.with_entities(func.sum(Registro.liquido_empresa)).scalar() or 0.0

    logo_data_uri = ''
    try:
        with open('static/images/logoheader.png', 'rb') as img:
            encoded = base64.b64encode(img.read()).decode('utf-8')
            logo_data_uri = f'data:image/png;base64,{encoded}'
    except: pass

    html = render_template('report_template.html', registros=registros, total_liquido=total_liquido, data_hoje=datetime.now().strftime('%d/%m/%Y'), request_args=request.args, logo_data_uri=logo_data_uri)
    pdf = HTML(string=html, base_url=request.base_url).write_pdf()
    return Response(pdf, mimetype='application/pdf', headers={'Content-Disposition': 'attachment;filename=relatorio.pdf'})

@app.route('/keep-alive')
def keep_alive():
    try:
        db.session.execute(text('SELECT 1'))
        return "OK", 200
    except Exception as e:
        return f"Erro: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)