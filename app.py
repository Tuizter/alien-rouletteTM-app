# app.py (VERSÃO FINAL COM LOGS DE DEPURAÇÃO)
import re
import os
import psycopg2
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from functools import wraps
from collections import defaultdict
from itertools import groupby
import secrets

app = Flask(__name__)
app.secret_key = 'alien-roulette-secret-key-12345-muito-secreta'

# --- BANCO DE DADOS DE USUÁRIOS ---
USERS = {'team@aliendev.com': 'projeto22'}

# --- CONEXÃO COM O BANCO DE DADOS POSTGRESQL DA RENDER ---
DATABASE_URL = os.environ.get('DATABASE_URL')
print(f"[INFO] DATABASE_URL carregada: {'...' + DATABASE_URL[-10:] if DATABASE_URL else 'NÃO ENCONTRADA'}")

def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"[ERRO CRÍTICO] Falha ao conectar ao banco de dados: {e}")
        return None

def init_db():
    print("[INFO] Tentando inicializar o banco de dados...")
    try:
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cur:
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS active_sessions (
                        email TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        last_login TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
            conn.commit()
            conn.close()
            print("[SUCESSO] Tabela 'active_sessions' verificada/criada com sucesso.")
        else:
            print("[ERRO] Conexão com o DB falhou, não foi possível inicializar a tabela.")
    except Exception as e:
        print(f"[ERRO CRÍTICO] Falha ao executar init_db: {e}")


# ############################################################### #
# ### LÓGICA DE ANÁLISE AVANÇADA (SEM ALTERAÇÃO)              ### #
# ############################################################### #
ROULETTE_WHEEL = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26]
NUMEROS_PRETOS = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}
def get_vizinhos(numero, n_vizinhos=1):
    try: index = ROULETTE_WHEEL.index(numero)
    except ValueError: return []
    total_numeros = len(ROULETTE_WHEEL)
    vizinhos = []
    for i in range(1, n_vizinhos + 1):
        vizinhos.append(ROULETTE_WHEEL[(index - i) % total_numeros])
        vizinhos.append(ROULETTE_WHEEL[(index + i) % total_numeros])
    return vizinhos
def est_confirmacoes_baixos(timeline):
    sugestoes = set()
    for numero in timeline:
        if 10 <= numero <= 36:
            dezena, unidade = divmod(numero, 10)
            sugestoes.add(dezena + unidade); sugestoes.add(abs(dezena - unidade))
        if numero in [10, 30]:
            resultado_div = numero // 2
            if resultado_div == 15: sugestoes.add(6); sugestoes.add(4)
            else: sugestoes.add(resultado_div)
        elif numero == 12: sugestoes.add(6)
    return [s for s in sugestoes if 1 <= s <= 9]
def est_numeros_ocultos(timeline):
    sugestoes = []
    for numero in timeline:
        if 10 <= numero <= 36: sugestoes.append(sum(divmod(numero, 10)))
    return sugestoes
def est_numeros_invertidos(timeline):
    mapa = {12: 21, 21: 12, 13: 31, 31: 13, 23: 32, 32: 23}
    ultimo_numero = timeline[-1]
    if ultimo_numero in mapa: return [ultimo_numero, mapa[ultimo_numero]]
    return []
def est_numeros_que_se_puxam(timeline):
    mapa = {25: [5, 7], 5: [7], 13: [11, 15, 17, 20, 24], 15: [11, 13, 17, 20, 24], 34: [32, 1, 28], 32: [34], 22: [2, 4]}
    ultimo_numero = timeline[-1]
    return mapa.get(ultimo_numero, [])
def est_sequencia_pretos(timeline, tamanho_gatilho=5):
    if len(timeline) < tamanho_gatilho: return []
    if all(num in NUMEROS_PRETOS for num in timeline[-tamanho_gatilho:]): return [2, 4, 6, 8]
    return []
def est_a_falha(timeline):
    sugestoes = set()
    if len(timeline) < 4: return []
    for i in range(len(timeline) - 3):
        n1, n2, n3, n4 = timeline[i:i+4]
        alvo = n1 + n2 - n3 + n4
        sugestoes.update([alvo - 1, alvo, alvo + 1])
    return [s for s in sugestoes if 0 <= s <= 36]
def est_bateu_e_voltou(timeline):
    sugestoes = set()
    for i in range(len(timeline) - 2):
        if timeline[i] == timeline[i+2]: sugestoes.add(timeline[i])
    for i in range(len(timeline) - 3):
        if timeline[i] == timeline[i+3]: sugestoes.add(timeline[i])
    return list(sugestoes)
def filtrar_alvos_por_limite(alvos_ordenados, limite=5):
    if not alvos_ordenados: return []
    alvos_finais = []
    grupos_por_score = [list(g) for k, g in groupby(alvos_ordenados, key=lambda x: x[1])]
    for grupo in grupos_por_score:
        if len(alvos_finais) + len(grupo) <= limite: alvos_finais.extend(grupo)
        else: break
    return alvos_finais
def analisador_avancado_roleta(timeline):
    pontuacao_alvos = defaultdict(int)
    detalhes_alvos = defaultdict(list)
    estrategias = {
        "Confirmações Baixos": est_confirmacoes_baixos, "Números Ocultos": est_numeros_ocultos,
        "Números Invertidos": est_numeros_invertidos, "Números que se Puxam": est_numeros_que_se_puxam,
        "Sequência de Pretos": est_sequencia_pretos, "A Falha": est_a_falha,
        "Bateu e Voltou": est_bateu_e_voltou,
    }
    for nome, funcao in estrategias.items():
        sugestoes = funcao(timeline)
        if sugestoes:
            for numero in sugestoes:
                pontuacao_alvos[numero] += 1
                if nome not in detalhes_alvos[numero]: detalhes_alvos[numero].append(nome)
    if not pontuacao_alvos: return None, None
    alvos_ordenados = sorted(pontuacao_alvos.items(), key=lambda item: item[1], reverse=True)
    alvos_filtrados = filtrar_alvos_por_limite(alvos_ordenados, limite=5)
    return alvos_filtrados, detalhes_alvos
def get_betting_suggestion(score):
    if score >= 4: return "Confiança MÁXIMA"
    if score == 3: return "Confiança ALTA"
    if score == 2: return "Confiança MÉDIA"
    return "Confiança BAIXA (Ideal para Proteção ou Aguardar)"


# --- SISTEMA DE VERIFICAÇÃO DE SESSÃO GLOBAL COM LOGS ---
@app.before_request
def check_session_validity():
    if request.endpoint in ['login', 'home', 'static', 'logout']:
        return
    
    if 'email' in session and 'session_id' in session:
        print(f"\n[DEBUG] Verificando sessão para o endpoint: {request.endpoint}")
        print(f"[DEBUG] Sessão do navegador: Email='{session['email']}', ID='{session['session_id']}'")
        
        conn = get_db_connection()
        if not conn:
            print("[ERRO] Não foi possível verificar a sessão, falha na conexão com o DB.")
            return redirect(url_for('login'))
        
        db_session_id = None
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT session_id FROM active_sessions WHERE email = %s", (session['email'],))
                result = cur.fetchone()
                if result:
                    db_session_id = result[0]
            conn.close()
            print(f"[DEBUG] Sessão encontrada no DB: ID='{db_session_id}'")
        except Exception as e:
            print(f"[ERRO] Falha ao ler do banco de dados durante a verificação: {e}")
            if conn: conn.close()
            return redirect(url_for('login'))

        if not db_session_id or db_session_id != session['session_id']:
            print(f"[ALERTA] Sessão inválida! Navegador='{session['session_id']}', DB='{db_session_id}'. Desconectando usuário.")
            flash("Sua conta foi acessada de outro local. Por segurança, você foi desconectado.", "error")
            session.clear()
            return redirect(url_for('login'))
        
        print("[DEBUG] Sessão VÁLIDA. Acesso permitido.")
    else:
        # Se não há sessão, mas a rota é protegida, redireciona para o login
        return redirect(url_for('login'))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

# --- ROTAS DA APLICAÇÃO ---
@app.route('/')
def home(): return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if USERS.get(email) == password:
            new_session_id = secrets.token_hex(16)
            print(f"\n[DEBUG] Usuário '{email}' fez login. Gerando novo ID de sessão: '{new_session_id}'")
            
            conn = get_db_connection()
            if not conn:
                flash("Erro interno do servidor, não foi possível iniciar a sessão. Tente novamente.", "error")
                return render_template('login.html')

            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO active_sessions (email, session_id) VALUES (%s, %s)
                        ON CONFLICT (email) DO UPDATE SET session_id = EXCLUDED.session_id, last_login = CURRENT_TIMESTAMP
                    """, (email, new_session_id))
                conn.commit()
                conn.close()
                print(f"[DEBUG] ID de sessão '{new_session_id}' salvo no DB para '{email}'.")
            except Exception as e:
                print(f"[ERRO] Falha ao salvar a sessão no DB: {e}")
                if conn: conn.close()
                flash("Erro interno do servidor ao salvar a sessão.", "error")
                return render_template('login.html')

            session['email'] = email
            session['session_id'] = new_session_id
            return redirect(url_for('app_page'))
        else:
            flash('Credenciais inválidas. Acesso Negado.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    if 'email' in session:
        print(f"\n[DEBUG] Usuário '{session['email']}' fazendo logout.")
        conn = get_db_connection()
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM active_sessions WHERE email = %s", (session['email'],))
                conn.commit()
                conn.close()
                print(f"[DEBUG] Sessão de '{session['email']}' removida do DB.")
            except Exception as e:
                print(f"[ERRO] Falha ao remover sessão do DB no logout: {e}")
                if conn: conn.close()
    
    session.clear()
    return redirect(url_for('login'))

@app.route('/app')
@login_required
def app_page(): return render_template('analise.html')

@app.route('/update_analysis', methods=['POST'])
@login_required
def update_analysis():
    # A lógica de análise não precisa de alterações
    data = request.get_json()
    numeros_str = data.get('numeros', '')
    try:
        numeros_limpos = re.split(r'[\s,]+', numeros_str.strip())
        historico = [int(n) for n in numeros_limpos if n.strip().isdigit()]
    except (ValueError, AttributeError): historico = []
    historico_str = ' '.join(map(str, historico)) if historico else "Nenhum número adicionado."
    if len(historico) < 13:
        return jsonify({
            'historico_str': historico_str, 'veredito': f"Aguardando 13 números ({len(historico)}/13)",
            'confianca': "Insira mais números para iniciar a análise avançada.", 'alvo_principal': 'N/A',
            'alvos_detalhados': [], 'numeros_para_destacar': [], 'numeros_vizinhos_destacar': [], 'show_results': False
        })
    timeline = historico[-13:]
    alvos_filtrados, detalhes_alvos = analisador_avancado_roleta(timeline)
    if not alvos_filtrados:
        return jsonify({
            'historico_str': ' '.join(map(str, timeline)), 'veredito': "Zona de Cautela",
            'confianca': "Nenhum padrão forte encontrado. Recomenda-se aguardar.", 'alvo_principal': 'N/A',
            'alvos_detalhados': [], 'numeros_para_destacar': [], 'numeros_vizinhos_destacar': [], 'show_results': True
        })
    alvo_principal, score_principal = alvos_filtrados[0]
    sugestao_aposta = get_betting_suggestion(score_principal)
    alvos_principais_lista = [alvo for alvo, score in alvos_filtrados if score == score_principal]
    protecoes_lista = [alvo for alvo, score in alvos_filtrados if score < score_principal]
    vizinhos_set = set()
    for alvo in alvos_principais_lista:
        vizinhos_set.update(get_vizinhos(alvo, n_vizinhos=1))
    numeros_ja_destacados = set(alvos_principais_lista + protecoes_lista)
    vizinhos_para_destacar = list(vizinhos_set - numeros_ja_destacados)
    lista_detalhada_alvos = []
    lista_numeros_destacar = alvos_principais_lista + protecoes_lista
    if alvos_principais_lista:
        lista_detalhada_alvos.append(f"🎯 <b>ALVOS PRINCIPAIS: {', '.join(map(str, alvos_principais_lista))}</b>")
    if protecoes_lista:
        lista_detalhada_alvos.append(f"🛡️ <b>PROTEÇÕES: {', '.join(map(str, protecoes_lista))}</b>")
    return jsonify({
        'historico_str': ' '.join(map(str, timeline)),
        'veredito': f"Sugestão de Aposta: <span class='highlight-number'>{sugestao_aposta}</span>",
        'confianca': f"Alvo(s) principal(is) com {score_principal} confirmações.",
        'alvo_principal': ', '.join(map(str, alvos_principais_lista)),
        'alvos_detalhados': lista_detalhada_alvos,
        'numeros_para_destacar': lista_numeros_destacar,
        'numeros_vizinhos_destacar': vizinhos_para_destacar,
        'show_results': True
    })

# Roda o init_db uma vez quando o aplicativo é iniciado no servidor
# Isso é mais robusto que o comando no Procfile
with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(debug=True, port=5000)