# app.py (VERSÃO FINAL COM ASSESSOR ESTRATÉGICO)
import re
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from functools import wraps
from collections import defaultdict
from itertools import groupby

app = Flask(__name__)
app.secret_key = 'alien-roulette-secret-key-12345'

# --- BANCO DE DADOS DE USUÁRIOS ---
USERS = {'team@aliendev.com': 'projeto22'}

# ############################################################### #
# ### INÍCIO DO BLOCO DE LÓGICA DE ANÁLISE AVANÇADA            ### #
# ############################################################### #

# --- Bloco de Constantes e Definições ---
NUMEROS_PRETOS = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}

# --- Funções das Estratégias Individuais (sem alteração) ---
def est_confirmacoes_baixos(timeline):
    sugestoes = set()
    for numero in timeline:
        if 10 <= numero <= 36:
            dezena, unidade = divmod(numero, 10)
            sugestoes.add(dezena + unidade)
            sugestoes.add(abs(dezena - unidade))
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
    mapa = {
        25: [5, 7], 5: [7],
        13: [11, 15, 17, 20, 24], 15: [11, 13, 17, 20, 24],
        34: [32, 1, 28], 32: [34],
        22: [2, 4],
    }
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

# --- FUNÇÃO DE FILTRAGEM INTELIGENTE ---
def filtrar_alvos_por_limite(alvos_ordenados, limite=5):
    if not alvos_ordenados: return []
    alvos_finais = []
    grupos_por_score = [list(g) for k, g in groupby(alvos_ordenados, key=lambda x: x[1])]
    for grupo in grupos_por_score:
        if len(alvos_finais) + len(grupo) <= limite:
            alvos_finais.extend(grupo)
        else:
            break
    return alvos_finais

# --- FUNÇÃO PRINCIPAL DE ANÁLISE ---
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
                if nome not in detalhes_alvos[numero]:
                    detalhes_alvos[numero].append(nome)
    
    if not pontuacao_alvos:
        return None, None

    alvos_ordenados = sorted(pontuacao_alvos.items(), key=lambda item: item[1], reverse=True)
    alvos_filtrados = filtrar_alvos_por_limite(alvos_ordenados, limite=5)
    return alvos_filtrados, detalhes_alvos

# --- NOVA FUNÇÃO PARA GERAR SUGESTÃO DE APOSTA ---
def get_betting_suggestion(score):
    if score >= 4: return "Confiança MÁXIMA"
    if score == 3: return "Confiança ALTA"
    if score == 2: return "Confiança MÉDIA"
    return "Confiança BAIXA (Ideal para Proteção ou Aguardar)"

# ############################################################### #
# ### FIM DO BLOCO DE LÓGICA DE ANÁLISE                       ### #
# ############################################################### #

# --- DECORATOR DE AUTENTICAÇÃO ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'email' not in session: return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- ROTAS BÁSICAS DA APLICAÇÃO ---
@app.route('/')
def home(): return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if USERS.get(email) == password:
            session['email'] = email
            return redirect(url_for('app_page'))
        else:
            flash('Credenciais inválidas. Acesso Negado.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('email', None)
    return redirect(url_for('login'))

@app.route('/app')
@login_required
def app_page(): return render_template('analise.html')

# --- ROTA DE ANÁLISE COM MELHORIAS ESTRATÉGICAS ---
@app.route('/update_analysis', methods=['POST'])
@login_required
def update_analysis():
    data = request.get_json()
    numeros_str = data.get('numeros', '')
    
    try:
        numeros_limpos = re.split(r'[\s,]+', numeros_str.strip())
        historico = [int(n) for n in numeros_limpos if n.strip().isdigit()]
    except (ValueError, AttributeError): historico = []

    historico_str = ' '.join(map(str, historico)) if historico else "Nenhum número adicionado."

    if len(historico) < 13:
        return jsonify({
            'historico_str': historico_str,
            'veredito': f"Aguardando 13 números ({len(historico)}/13)",
            'confianca': "Insira mais números para iniciar a análise avançada.",
            'alvo_principal': 'N/A', 'alvos_detalhados': [],
            'numeros_para_destacar': [], 'show_results': False
        })

    timeline = historico[-13:]
    alvos_filtrados, detalhes_alvos = analisador_avancado_roleta(timeline)
    
    if not alvos_filtrados:
        return jsonify({
            'historico_str': ' '.join(map(str, timeline)),
            'veredito': "Zona de Cautela",
            'confianca': "Nenhum padrão forte encontrado. Recomenda-se aguardar.",
            'alvo_principal': 'N/A', 'alvos_detalhados': [],
            'numeros_para_destacar': [], 'show_results': True
        })

    alvo_principal, score_principal = alvos_filtrados[0]
    sugestao_aposta = get_betting_suggestion(score_principal)

    # Separação entre Alvos Principais e Proteções
    alvos_principais_lista = [alvo for alvo, score in alvos_filtrados if score == score_principal]
    protecoes_lista = [alvo for alvo, score in alvos_filtrados if score < score_principal]

    # Formata a lista para exibição
    lista_detalhada_alvos = []
    lista_numeros_destacar = []
    
    # Adiciona Alvos Principais
    if alvos_principais_lista:
        lista_detalhada_alvos.append(f"🎯 <b>ALVOS PRINCIPAIS: {', '.join(map(str, alvos_principais_lista))}</b>")
        lista_numeros_destacar.extend(alvos_principais_lista)
    
    # Adiciona Proteções
    if protecoes_lista:
        lista_detalhada_alvos.append(f"🛡️ <b>PROTEÇÕES: {', '.join(map(str, protecoes_lista))}</b>")
        lista_numeros_destacar.extend(protecoes_lista)

    return jsonify({
        'historico_str': ' '.join(map(str, timeline)),
        'veredito': f"Sugestão de Aposta: <span class='highlight-number'>{sugestao_aposta}</span>",
        'confianca': f"Alvo(s) principal(is) com {score_principal} confirmações.",
        'alvo_principal': ', '.join(map(str, alvos_principais_lista)),
        'alvos_detalhados': lista_detalhada_alvos,
        'numeros_para_destacar': lista_numeros_destacar,
        'show_results': True
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)