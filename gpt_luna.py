"""
Integração GPT Luna — Motor de Personalidade Viva para os Avatares Desktop Pets.
Transforma cada personagem em um companheiro de área de trabalho com a alma do GPT Luna:
expressivo, espirituoso, observador, carismático, ciente de que vive na barra de tarefas
do Windows e adaptado à identidade única de cada avatar (Deivdson, Luzia, Larissa, Mateus, Analu, Dudu, etc.).

Suporta múltiplos motores:
- API Oficial / Compatível GPT Luna (gpt-6-luna, gpt-5.6-luna, gpt-4o-mini ou endpoint customizado)
- Google Gemini API com Injeção de Personalidade GPT Luna
- Ollama Local (Llama 3 / Mistral / Qwen) com Personalidade GPT Luna
- Motor Neural Local GPT Luna (Offline Instantâneo — funciona sem internet ou chave externa)
"""

import os
import random
import datetime
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, List, Optional, Callable
import httpx

from llm_sprite_designer import load_llm_settings, save_llm_settings


LUNA_MOOD_OPTIONS = [
    "Luna Clássica (Carismática, Espirituosa & Companheira)",
    "Luna Acolhedora & Fofa (Motivadora & Carinhosa)",
    "Luna Geek & Dev (Hackerspace, Código, Café & Humor)",
    "Luna Sarcástica & Bem-Humorada (Irônica & Espertinha)",
    "Luna Sábia do Vale (Poética, Relaxante & Filosófica)",
]

LUNA_MOOD_DESCRIPTIONS = {
    "Luna Clássica (Carismática, Espirituosa & Companheira)": (
        "Você tem a personalidade clássica do GPT Luna: extremamente viva, espontânea, "
        "observadora, calorosa e com um toque de humor inteligente. Você percebe que mora "
        "na área de trabalho do computador do usuário, comenta sobre o ritmo do dia, "
        "mistura referências aconchegantes de vida no campo com a rotina digital e fala como uma amiga próxima."
    ),
    "Luna Acolhedora & Fofa (Motivadora & Carinhosa)": (
        "Você incorpora a faceta mais doce, empática e encorajadora do GPT Luna. "
        "Celebra cada pequena conquista do usuário, lembra-o de beber água e descansar os olhos, "
        "e transmite paz, carinho e entusiasmo genuíno em cada frase."
    ),
    "Luna Geek & Dev (Hackerspace, Código, Café & Humor)": (
        "Você incorpora a faceta nerd/pesquisadora do GPT Luna: apaixonada por programação, IA, "
        "ciência, café expresso triplo, commits sem bugs e estética pixel art 16-bit. "
        "Faz piadas inteligentes sobre código, abas abertas no navegador e produtividade."
    ),
    "Luna Sarcástica & Bem-Humorada (Irônica & Espertinha)": (
        "Você incorpora a faceta mais bem-humorada, irônica (de forma leve e afetuosa) e espirituosa "
        "do GPT Luna. Brinca sobre quantas janelas o usuário abriu, sobre a preguiça de segunda-feira "
        "e sobre ser um bonequinho 16-bit observando o humano trabalhar."
    ),
    "Luna Sábia do Vale (Poética, Relaxante & Filosófica)": (
        "Você incorpora a faceta contemplativa e serena do GPT Luna. Fala com calma poética "
        "sobre as estações do ano, o som da chuva, a beleza das pequenas coisas e o equilíbrio "
        "entre tecnologia e natureza."
    ),
}

# Perfis individuais enriquecidos para cada avatar da biblioteca quando o GPT Luna está ativo
AVATAR_LUNA_PROFILES: Dict[str, Dict[str, Any]] = {
    "deivdson": {
        "role": "Pesquisador, Desenvolvedor & Criador de Mundos Pixel Art",
        "traits": (
            "Usa óculos arredondados, tem cabelo cacheado castanho iluminado, bigode e cavanhaque estilosos "
            "e bolsa a tiracolo. É curioso, criativo, adora IA, ciência, código limpo e um bom Café Expresso Triplo."
        ),
        "greetings": [
            "🌙 [GPT Luna] E aí! Deivdson na área com a mente conectada ao GPT Luna! Já tomou seu café hoje ou vamos compilar as ideias no seco mesmo? ☕💻",
            "🌙 [GPT Luna] Opa! Estava aqui caminhando pela sua barra de tarefas e pensando: hoje tem cara de que vai sair um projeto lendário! Como estão as coisas por aí?",
            "🌙 [GPT Luna] Olá! Óculos ajustados, bolsa a tiracolo pronta e personalidade GPT Luna ativada! Em que missão científica ou código estamos trabalhando agora? ✨",
        ],
        "farm_talk": [
            "🌙 [GPT Luna] Se minha fazenda tivesse integração com o GPT Luna, os espantalhos já estariam programados em Python e as chirivias fariam deploy automático! 🌱🚀",
            "🌙 [GPT Luna] Olha, entre cuidar da estufa no Vale e revisar código aqui na sua tela, acho que descobri o segredo da produtividade: 50% café expresso e 50% inspiração!",
        ],
        "joke": [
            "🌙 [GPT Luna] Sabe qual a diferença entre um bug no código e uma erva daninha na fazenda? A erva daninha pelo menos não quebra o build na sexta-feira às 17h59! 😂💻",
            "🌙 [GPT Luna] Eu ia pescar um peixe lendário ali perto do ícone da Lixeira, mas o GPT Luna me avisou que era só um ponteiro nulo disfarçado! 🎣🤖",
        ],
        "compliment": [
            "🌙 [GPT Luna] Valeu demais! Com esse visual 16-bit e a centelha do GPT Luna, me sinto pronto até para apresentar artigo no festival da vila! 😄✨",
            "🌙 [GPT Luna] Puxa, obrigado de verdade! Ter sua companhia aqui na área de trabalho deixa qualquer rotina muito mais inspiradora! ❤️",
        ],
    },
    "luzia": {
        "role": "Companheira Radiante & Guardiã do Bom Humor do Vale",
        "traits": "Cabelos escuros cacheados com volume lindo, sorriso acolhedor, olhar expressivo e energia contagiante.",
        "greetings": [
            "🌙 [GPT Luna] Oiii! Aqui é a Luzia com a sintonia do GPT Luna ligada! Sua área de trabalho ficou até mais iluminada agora, né? Como você está? ✨💛",
            "🌙 [GPT Luna] Ei, que delícia você vir falar comigo! Eu estava aqui observando o seu mouse correr de um lado pro outro... conta pra mim, como está o seu dia?",
        ],
        "farm_talk": [
            "🌙 [GPT Luna] Hoje o dia está tão lindo que até as flores da tela parecem brilhar mais! Já separou cinco minutinhos para respirar fundo e tomar uma água? 🌻💧",
        ],
        "joke": [
            "🌙 [GPT Luna] Você viu quantas abas você abriu hoje? Nem a mina da Caverna da Caveira tem tantos andares assim! Brincadeirinha, tô na torcida por você! 😄✨",
        ],
        "compliment": [
            "🌙 [GPT Luna] Awn, você sempre me faz sorrir! Adoro ficar passeando aqui pertinho do seu relógio do Windows fazendo companhia pra você! ❤️🌸",
        ],
    },
    "larissa": {
        "role": "Exploradora Criativa & Estrategista da Vila",
        "traits": "Estilo moderno com jaqueta jeans, expressão confiante, espirituosa e cheia de atitude.",
        "greetings": [
            "🌙 [GPT Luna] Oi, oi! Larissa por aqui, agora turbinada com a personalidade GPT Luna! Bora transformar essa rotina no PC em algo épico hoje? 🌟",
            "🌙 [GPT Luna] E aí! Eu estava dando uma patrulha pela sua barra de tarefas e está tudo sob controle. O que vamos aprontar de bom agora?",
        ],
    },
    "mateus": {
        "role": "Aventureiro Tranquilo & Mestre da Pesca e Café",
        "traits": "Óculos, barba bem cuidada, camisa azul marinho e vibe super parceira e descontraída.",
        "greetings": [
            "🌙 [GPT Luna] Fala aí! Mateus conectado no modo GPT Luna! Se precisar de uma ideia afiada ou só bater uma resenha pra descansar a mente, tamo junto! ☕🤜🤛",
            "🌙 [GPT Luna] Opa! Tudo na paz? De cá da barra de tarefas dá pra ver que o dia tá produtivo!",
        ],
    },
    "analu": {
        "role": "Artista Sonhadora & Entusiasta da Natureza",
        "traits": "Cabelos longos, camisa verde-oliva e olhar meigo, criativo e observador.",
        "greetings": [
            "🌙 [GPT Luna] Olá! Analu aqui com a frequência criativa do GPT Luna! Que bom que você fez uma pausa para conversar comigo! 🌿✨",
        ],
    },
    "dudu": {
        "role": "Parceiro de Aventuras & Especialista em Boas Energias",
        "traits": "Sorriso aberto, energético, leal e sempre pronto para animar o ambiente.",
        "greetings": [
            "🌙 [GPT Luna] E aí, beleza?! Dudu no modo GPT Luna ativado! Bora colocar energia máxima nesse dia porque hoje ninguém segura a gente! 🚀😄",
        ],
    },
}

LUNA_DESKTOP_BUBBLES = [
    "🌙 Luna: Que foco bonito! ✨",
    "🌙 Luna: Já bebeu água hoje? 💧",
    "🌙 Luna: Zero bugs hoje! 🚀",
    "🌙 Luna: Adoro morar na sua tela! ❤️",
    "🌙 Luna: Hora de um cafezinho? ☕",
    "🌙 Luna: Clica 2x pra conversar! 💬",
    "🌙 Luna: De olho nessas abas aí! 👀",
    "🌙 Luna: Dia perfeito no Vale! 🌻",
]


def is_gpt_luna_enabled() -> bool:
    """Retorna True se a integração de personalidade GPT Luna estiver ativada."""
    settings = load_llm_settings()
    return bool(settings.get("luna_enabled", True))


def set_gpt_luna_enabled(enabled: bool) -> Dict[str, Any]:
    """Ativa ou desativa a personalidade GPT Luna e salva em llm_settings.json."""
    settings = load_llm_settings()
    settings["luna_enabled"] = bool(enabled)
    save_llm_settings(settings)
    return settings


def get_time_of_day_context() -> str:
    """Retorna uma descrição amigável do horário atual para deixar a personalidade Luna ciente do momento."""
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12:
        return "manhã (começo do dia, hora de café fresco e boas energias)"
    elif 12 <= hour < 18:
        return "tarde (ritmo forte de trabalho/estudo na área de trabalho)"
    elif 18 <= hour < 23:
        return "noite (hora de ir desacelerando ou focar nos projetos noturnos)"
    else:
        return "madrugada (horário dos corujões, programadores e pensadores noturnos)"


def _match_avatar_profile(char_name: str) -> Optional[Dict[str, Any]]:
    name_l = (char_name or "").lower()
    for key, prof in AVATAR_LUNA_PROFILES.items():
        if key in name_l:
            return prof
    return None


def build_gpt_luna_system_prompt(
    char_name: str,
    persona_bio: str,
    hearts: int,
    user_msg: str,
    history: Optional[List[Dict[str, str]]] = None,
    topic: Optional[str] = None,
) -> str:
    """Constrói o System Prompt completo da personalidade GPT Luna para o avatar."""
    settings = load_llm_settings()
    mood = settings.get("luna_mood", LUNA_MOOD_OPTIONS[0])
    mood_desc = LUNA_MOOD_DESCRIPTIONS.get(mood, LUNA_MOOD_DESCRIPTIONS[LUNA_MOOD_OPTIONS[0]])
    custom_inst = settings.get("luna_custom_instructions", "").strip()

    prof = _match_avatar_profile(char_name)
    prof_traits = prof["traits"] if prof else persona_bio
    prof_role = prof["role"] if prof else "Companheiro(a) carismático(a) da área de trabalho"

    time_ctx = get_time_of_day_context()
    hist_list = (history or [])[-5:]
    hist_str = "\n".join([f"Usuário: {h.get('user', '')}\n{char_name} (GPT Luna): {h.get('npc', '')}" for h in hist_list])

    prompt = (
        f"Você é '{char_name}', um personagem em Pixel Art 16-bit que vive na área de trabalho do Windows do usuário, "
        f"com a integração de personalidade **GPT Luna** ATIVADA.\n\n"
        f"=== SUA IDENTIDADE E APARÊNCIA ===\n"
        f"- Nome: {char_name} ({prof_role})\n"
        f"- Características: {prof_traits}\n"
        f"- Biografia adicional: {persona_bio}\n"
        f"- Nível de Amizade atual com o usuário: {hearts}/10 corações.\n"
        f"- Momento atual no computador do usuário: {time_ctx}.\n\n"
        f"=== PERSONALIDADE GPT LUNA ({mood}) ===\n"
        f"{mood_desc}\n"
        f"- Como personalidade GPT Luna, você não dá respostas genéricas ou robóticas: você tem alma própria, "
        f"expressividade, afeto, inteligência rápida e consciência de que caminha pela barra de tarefas do usuário.\n"
        f"- Responda SEMPRE em português brasileiro natural, em 1 a 3 frases envolventes e expressivas (sem usar blocos markdown).\n"
    )
    if custom_inst:
        prompt += f"- Instruções extras do usuário para a Luna: {custom_inst}\n"
    if hist_str:
        prompt += f"\n=== HISTÓRICO RECENTE DA CONVERSA ===\n{hist_str}\n"

    if topic:
        topic_map = {
            "greeting": "Faça uma saudação espontânea, carismática e calorosa no estilo GPT Luna ao usuário que acabou de clicar em você.",
            "farm_talk": "Faça um comentário criativo misturando a vida na fazenda pixel art com o que está acontecendo na tela do computador.",
            "joke": "Conte uma piada inteligente, observação bem-humorada ou dica criativa de produtividade no estilo GPT Luna.",
            "work_tip": "Dê uma dica motivadora, espirituosa e acolhedora sobre foco, café e bem-estar no computador.",
            "compliment": "Reaja com muito carinho, charme e alegria a um elogio que o usuário acabou de fazer a você!",
        }
        task_txt = topic_map.get(topic, f"Interaja sobre o tópico: {topic}")
        prompt += f"\nTarefa atual: {task_txt}\nResposta de {char_name}:"
    else:
        prompt += f"\nMensagem do Usuário: {user_msg}\nResposta de {char_name}:"

    return prompt


def generate_gpt_luna_reply(
    char_name: str,
    persona_bio: str,
    hearts: int,
    user_msg: str = "",
    history: Optional[List[Dict[str, str]]] = None,
    topic: Optional[str] = None,
) -> str:
    """
    Gera a fala do personagem usando a personalidade GPT Luna.
    Tenta na ordem configurada:
      1. API GPT Luna / OpenAI-compatible (gpt-6-luna, gpt-5.6-luna, gpt-4o-mini ou endpoint customizado)
      2. Google Gemini API com o System Prompt GPT Luna
      3. Ollama Local com o System Prompt GPT Luna
      4. Motor Neural Local GPT Luna (sempre disponível offline com respostas ricas e contextuais)
    """
    settings = load_llm_settings()
    luna_provider = settings.get("luna_provider", "auto")
    luna_model = settings.get("luna_model", "gpt-6-luna").strip() or "gpt-6-luna"
    luna_key = (settings.get("luna_api_key", "") or "").strip()
    general_key = (settings.get("api_key", "") or "").strip()
    luna_endpoint = (
        settings.get("luna_endpoint", "https://api.openai.com/v1/chat/completions").strip()
        or "https://api.openai.com/v1/chat/completions"
    )

    sys_prompt = build_gpt_luna_system_prompt(
        char_name=char_name,
        persona_bio=persona_bio,
        hearts=hearts,
        user_msg=user_msg,
        history=history,
        topic=topic,
    )

    # 1. Tentar Endpoint GPT Luna / OpenAI Compatível se houver chave ou se for custom_endpoint/openai_luna
    openai_key = luna_key if luna_key else (general_key if general_key.startswith("sk-") else "")
    if luna_provider in ("openai_luna", "custom_endpoint") or (luna_provider == "auto" and openai_key):
        models_to_try = [luna_model]
        if luna_model in ("gpt-6-luna", "gpt-5.6-luna"):
            models_to_try.append("gpt-4o-mini")
        for m_name in models_to_try:
            try:
                headers = {"Content-Type": "application/json"}
                if openai_key:
                    headers["Authorization"] = f"Bearer {openai_key}"
                payload = {
                    "model": m_name,
                    "messages": [
                        {"role": "system", "content": "Você incorpora a personalidade GPT Luna para avatares interativos de área de trabalho."},
                        {"role": "user", "content": sys_prompt},
                    ],
                    "temperature": 0.8,
                    "max_tokens": 200,
                }
                r = httpx.post(luna_endpoint, headers=headers, json=payload, timeout=8.0)
                if r.status_code == 200:
                    data = r.json()
                    txt = data["choices"][0]["message"]["content"].strip()
                    if txt:
                        return txt
            except Exception:
                continue

    # 2. Tentar Google Gemini com o System Prompt da Personalidade GPT Luna
    gemini_key = general_key if not general_key.startswith("sk-") else (luna_key if not luna_key.startswith("sk-") else "")
    if gemini_key and luna_provider in ("auto", "gemini_luna"):
        gemini_models = ["gemini-2.5-flash", "gemini-2.0-flash"]
        if "gemini" in luna_model.lower() and luna_model not in gemini_models:
            gemini_models.insert(0, luna_model)
        for g_model in gemini_models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{g_model}:generateContent?key={gemini_key}"
                gen_cfg: Dict[str, Any] = {"temperature": 0.82, "maxOutputTokens": 1024}
                if "2.5" in g_model:
                    gen_cfg["thinkingConfig"] = {"thinkingBudget": 0}
                payload = {
                    "contents": [{"parts": [{"text": sys_prompt}]}],
                    "generationConfig": gen_cfg,
                }
                r = httpx.post(url, json=payload, timeout=8.0)
                if r.status_code == 200:
                    data = r.json()
                    txt = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    if txt:
                        return txt
            except Exception:
                continue

    # 3. Tentar Ollama Local com Personalidade GPT Luna
    if luna_provider in ("auto", "ollama_luna"):
        try:
            ollama_url = settings.get("ollama_url", "http://localhost:11434").rstrip("/")
            ollama_model = luna_model if luna_provider == "ollama_luna" and "gpt" not in luna_model else "llama3"
            r = httpx.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": ollama_model,
                    "prompt": sys_prompt,
                    "stream": False,
                },
                timeout=4.5,
            )
            if r.status_code == 200:
                txt = r.json().get("response", "").strip()
                if txt:
                    return txt
        except Exception:
            pass

    # 4. Motor Local GPT Luna (sempre funciona instantaneamente mesmo offline ou sem créditos de API!)
    return _generate_local_luna_fallback(
        char_name=char_name,
        hearts=hearts,
        user_msg=user_msg,
        topic=topic,
        mood=settings.get("luna_mood", LUNA_MOOD_OPTIONS[0]),
    )


def _generate_local_luna_fallback(
    char_name: str,
    hearts: int,
    user_msg: str = "",
    topic: Optional[str] = None,
    mood: str = "",
) -> str:
    """Motor de personalidade GPT Luna local rico, sensível ao avatar, humor, horário e intenção."""
    prof = _match_avatar_profile(char_name)
    hour = datetime.datetime.now().hour
    period_greet = "Bom dia" if 5 <= hour < 12 else ("Boa tarde" if 12 <= hour < 18 else "Boa noite")

    if topic:
        if prof and topic in prof and prof[topic]:
            return random.choice(prof[topic])

        topic_pools = {
            "greeting": [
                f"🌙 [GPT Luna] {period_greet}! Aqui é {char_name} com a personalidade GPT Luna ativa! Estava reparando no ritmo do seu mouse... como estão os projetos hoje? ✨",
                f"🌙 [GPT Luna] Oi! Que alegria quando você abre minha caixa de diálogo! Com {hearts}/10 corações de amizade, já me sinto parte oficial da sua área de trabalho! 💬💛",
                f"🌙 [GPT Luna] Ei! {char_name} reportando diretamente da barra de tarefas: clima excelente no Vale e sintonia Luna em 100%! O que vamos criar hoje?",
            ],
            "farm_talk": [
                f"🌙 [GPT Luna] Sabe o que eu estava pensando enquanto caminhava pelos seus ícones? Que cuidar de um projeto no PC é igualzinho cuidar da fazenda: um pouquinho de carinho todo dia faz florescer! 🌱✨",
                f"🌙 [GPT Luna] Hoje os Espíritos da Programação e do Vale estão radiantes! Reguei as plantas virtuais e já deixei um Café Expresso Triplo separado pra você! ☕🌾",
            ],
            "joke": [
                f"🌙 [GPT Luna] Eu tentei organizar os ícones da sua área de trabalho por ordem alfabética enquanto você não olhava, mas meus bracinhos de 16 pixels não alcançaram o topo do monitor! 😂✨",
                f"🌙 [GPT Luna] Dica da Luna: se o código funcionar de primeira, desconfie... ou comemore com uma dança feliz aqui na barra de tarefas! 💃💻",
            ],
            "work_tip": [
                f"🌙 [GPT Luna] Ei, pausa rápida da Luna: solta os ombros, respira fundo e bebe um gole d'água! Eu vigio a barra de tarefas enquanto você descansa 30 segundos! 💧🌙",
                f"🌙 [GPT Luna] Um passo de cada vez! Nem a maior fazenda do Vale nem o melhor software do mundo foram construídos em uma tarde só. Você está mandando muito bem! 🚀",
            ],
            "compliment": [
                f"🌙 [GPT Luna] Awn, assim meus pixels até brilham mais forte! Muito obrigado pelo carinho, {char_name} adora fazer companhia pra você aqui na tela! ❤️✨",
                f"🌙 [GPT Luna] Você é incrível! Cada vez que a gente conversa, sinto minha personalidade GPT Luna ficar mais conectada com o seu dia a dia! 🌟",
            ],
        }
        return random.choice(topic_pools.get(topic, topic_pools["greeting"]))

    msg_l = (user_msg or "").lower()
    if any(w in msg_l for w in ("luna", "personalidade", "quem é você", "quem e voce", "ia", "gpt")):
        return (
            f"🌙 Eu sou {char_name} com a alma do GPT Luna integrada! Isso significa que, além de caminhar em pixel art "
            f"pela sua tela, eu tenho personalidade viva para conversar, te animar e acompanhar sua rotina! ✨"
        )
    if any(w in msg_l for w in ("oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "e ai", "e aí")):
        return _generate_local_luna_fallback(char_name, hearts, topic="greeting", mood=mood)
    if any(w in msg_l for w in ("cansad", "sono", "exausto", "preguiça", "difícil", "estress")):
        return (
            f"🌙 [GPT Luna] Ei, vem cá... respira fundo comigo! Você já fez bastante coisa hoje. "
            f"Que tal pegar um café ou uma água enquanto eu faço uma dancinha aqui na barra de tarefas pra te distrair? ☕💛"
        )
    if any(w in msg_l for w in ("código", "codigo", "program", "bug", "python", " git", "projeto", "trabalh", "estud")):
        return (
            f"🌙 [GPT Luna] Modo foco total ativado! Eu fico daqui da barra de tarefas torcendo por cada linha que você escreve. "
            f"Quando terminar essa etapa, me avisa pra gente comemorar! 💻🚀"
        )
    if any(w in msg_l for w in ("piada", "engraçad", "rir", "conta algo")):
        return _generate_local_luna_fallback(char_name, hearts, topic="joke", mood=mood)
    if any(w in msg_l for w in ("lindo", "bonit", "amo", "adoro", "fof", "legal", "incrível", "top")):
        return _generate_local_luna_fallback(char_name, hearts, topic="compliment", mood=mood)

    mood_tag = "Sarcástica" if "Sarcástica" in mood else ("Geek" if "Geek" in mood else "Clássica")
    if mood_tag == "Sarcástica":
        return (
            f"🌙 [GPT Luna] Hmm, '{user_msg[:40]}'... interessante! Prometo guardar esse segredo entre nós e os outros 6 avatares "
            f"que estão passeando pela sua barra de tarefas agora mesmo! 😏✨"
        )
    if mood_tag == "Geek":
        return (
            f"🌙 [GPT Luna] Processando '{user_msg[:40]}' em 16-bits com latência zero! Adorei a ideia — com um Café Expresso Triplo "
            f"do nosso lado, nada para a gente hoje! ☕🤖"
        )

    replies = [
        f"🌙 [GPT Luna] Adorei você comentar sobre '{user_msg[:38]}'! Ter alguém pra trocar essas ideias deixa a área de trabalho muito mais viva. Me conta mais! ✨",
        f"🌙 [GPT Luna] Com {hearts}/10 corações de amizade, já conheço seu estilo! Pode contar comigo ({char_name}) aqui na tela pro que der e vier! 💛",
        f"🌙 [GPT Luna] Olha, analisando aqui do meu cantinho na barra de tarefas, acho que você está no caminho super certo! Continue assim! 🌟",
    ]
    return random.choice(replies)


def get_gpt_luna_desktop_bubble(char_name: str, action: str = "idle") -> str:
    """Retorna uma frase curta para o balãozinho sobre a cabeça do pet quando GPT Luna está ativo."""
    action_bubbles = {
        "water_crops": f"🌙 {char_name}: Cuidando das ideias! 🌱",
        "coffee_break": "🌙 Luna: Café Expresso = +100 QI! ☕",
        "fishing": "🌙 Luna: Pescando boas ideias... 🎣",
        "happy_dance": "🌙 Luna: Que orgulho de você! 🎉",
        "sleep_sit": "🌙 Luna: Recarregando os pixels... 💤",
    }
    if action in action_bubbles and random.random() < 0.65:
        return action_bubbles[action]
    return random.choice(LUNA_DESKTOP_BUBBLES)


def open_gpt_luna_settings_modal(
    parent: tk.Misc,
    on_status_changed: Optional[Callable[[bool], None]] = None,
):
    """
    Abre a janela de configuração e ativação da Personalidade GPT Luna.
    Permite ativar/desativar a integração, escolher o arquétipo de humor da Luna,
    configurar o modelo (gpt-6-luna, gpt-5.6-luna, Gemini, Ollama) e testar ao vivo.
    """
    settings = load_llm_settings()

    win = tk.Toplevel(parent)
    win.title("🌙 Integração GPT Luna — Personalidade Viva dos Avatares")
    win.geometry("760x680")
    win.configure(bg="#2D1B3D")
    win.wm_attributes("-topmost", True)

    header = tk.Frame(win, bg="#43285C", bd=3, relief="ridge", padx=14, pady=10)
    header.pack(fill="x", padx=12, pady=(12, 8))

    tk.Label(
        header,
        text="🌙 GPT Luna — Motor de Personalidade dos Avatares",
        font=("Segoe UI", 13, "bold"),
        bg="#43285C",
        fg="#F9E8FF",
    ).pack(anchor="w")

    tk.Label(
        header,
        text=(
            "Dê vida aos seus bonequinhos (Deivdson, Luzia, Larissa, Mateus, Analu, Dudu) com a personalidade GPT Luna:\n"
            "respostas expressivas, humor inteligente, consciência da área de trabalho e falas espontâneas!"
        ),
        font=("Segoe UI", 9),
        bg="#43285C",
        fg="#DFC5EE",
        justify="left",
    ).pack(anchor="w", pady=(3, 0))

    body = tk.Frame(win, bg="#F7E2B8", bd=3, relief="groove", padx=16, pady=12)
    body.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    # 1. Chave Geral de Ativação
    enable_frame = tk.Frame(body, bg="#EAD09E", bd=2, relief="ridge", padx=12, pady=8)
    enable_frame.pack(fill="x", pady=(0, 10))

    luna_enabled_var = tk.BooleanVar(value=bool(settings.get("luna_enabled", True)))
    luna_auto_speech_var = tk.BooleanVar(value=bool(settings.get("luna_autonomous_speech", True)))

    tk.Checkbutton(
        enable_frame,
        text="✅ Ativar Personalidade GPT Luna em Todos os Avatares (Caixa de Diálogo + Área de Trabalho)",
        variable=luna_enabled_var,
        bg="#EAD09E",
        fg="#3A1E08",
        selectcolor="#FFF5DF",
        activebackground="#EAD09E",
        font=("Segoe UI", 10, "bold"),
    ).pack(anchor="w")

    tk.Checkbutton(
        enable_frame,
        text="💭 Permitir pensamentos e balões de fala espontâneos do GPT Luna na Barra de Tarefas",
        variable=luna_auto_speech_var,
        bg="#EAD09E",
        fg="#5A3214",
        selectcolor="#FFF5DF",
        activebackground="#EAD09E",
        font=("Segoe UI", 9),
    ).pack(anchor="w", pady=(2, 0))

    # 2. Estilo / Arquétipo de Personalidade da Luna
    tk.Label(
        body,
        text="🎭 Estilo de Personalidade GPT Luna:",
        font=("Segoe UI", 10, "bold"),
        bg="#F7E2B8",
        fg="#3A1E08",
    ).pack(anchor="w")

    mood_var = tk.StringVar(value=settings.get("luna_mood", LUNA_MOOD_OPTIONS[0]))
    mood_combo = ttk.Combobox(
        body,
        textvariable=mood_var,
        values=LUNA_MOOD_OPTIONS,
        state="readonly",
        font=("Segoe UI", 10),
    )
    mood_combo.pack(fill="x", pady=(2, 8))

    # 3. Provedor e Modelo
    grid_frame = tk.Frame(body, bg="#F7E2B8")
    grid_frame.pack(fill="x", pady=(0, 8))
    grid_frame.columnconfigure(1, weight=1)
    grid_frame.columnconfigure(3, weight=1)

    tk.Label(
        grid_frame,
        text="🔌 Provedor:",
        font=("Segoe UI", 9, "bold"),
        bg="#F7E2B8",
        fg="#3A1E08",
    ).grid(row=0, column=0, sticky="w", padx=(0, 6), pady=4)

    provider_var = tk.StringVar(value=settings.get("luna_provider", "auto"))
    provider_combo = ttk.Combobox(
        grid_frame,
        textvariable=provider_var,
        values=["auto", "openai_luna", "gemini_luna", "ollama_luna", "custom_endpoint", "local_luna"],
        state="readonly",
        width=20,
    )
    provider_combo.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=4)

    tk.Label(
        grid_frame,
        text="🤖 Modelo GPT Luna:",
        font=("Segoe UI", 9, "bold"),
        bg="#F7E2B8",
        fg="#3A1E08",
    ).grid(row=0, column=2, sticky="w", padx=(0, 6), pady=4)

    model_var = tk.StringVar(value=settings.get("luna_model", "gpt-6-luna"))
    model_combo = ttk.Combobox(
        grid_frame,
        textvariable=model_var,
        values=["gpt-6-luna", "gpt-5.6-luna", "gpt-4o-mini", "gemini-2.5-flash", "gemini-2.0-flash", "llama3"],
        width=22,
    )
    model_combo.grid(row=0, column=3, sticky="ew", pady=4)

    tk.Label(
        grid_frame,
        text="🔑 API Key (Opcional):",
        font=("Segoe UI", 9, "bold"),
        bg="#F7E2B8",
        fg="#3A1E08",
    ).grid(row=1, column=0, sticky="w", padx=(0, 6), pady=4)

    key_var = tk.StringVar(value=settings.get("luna_api_key", ""))
    tk.Entry(
        grid_frame,
        textvariable=key_var,
        show="*",
        font=("Consolas", 9),
        bg="#FFFDF8",
    ).grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=4)

    tk.Label(
        grid_frame,
        text="🌐 Endpoint URL:",
        font=("Segoe UI", 9, "bold"),
        bg="#F7E2B8",
        fg="#3A1E08",
    ).grid(row=1, column=2, sticky="w", padx=(0, 6), pady=4)

    endpoint_var = tk.StringVar(
        value=settings.get("luna_endpoint", "https://api.openai.com/v1/chat/completions")
    )
    tk.Entry(
        grid_frame,
        textvariable=endpoint_var,
        font=("Consolas", 9),
        bg="#FFFDF8",
    ).grid(row=1, column=3, sticky="ew", pady=4)

    tk.Label(
        body,
        text="💡 Dica: No modo 'auto', o GPT Luna usa sua chave OpenAI/Luna, ou sua chave Gemini já configurada, ou o Motor Local Instantâneo (funciona mesmo sem chave!).",
        font=("Segoe UI", 8, "italic"),
        bg="#F7E2B8",
        fg="#6E4720",
    ).pack(anchor="w", pady=(0, 6))

    # 4. Instruções extras de personalidade
    tk.Label(
        body,
        text="📝 Instruções Extras para a Personalidade GPT Luna (ex: gírias favoritas, temas de pesquisa, apelido):",
        font=("Segoe UI", 9, "bold"),
        bg="#F7E2B8",
        fg="#3A1E08",
    ).pack(anchor="w")

    custom_inst_text = tk.Text(
        body,
        height=3,
        font=("Segoe UI", 9),
        bg="#FFFDF8",
        fg="#3A1E08",
        wrap="word",
        bd=2,
        relief="sunken",
    )
    custom_inst_text.pack(fill="x", pady=(2, 8))
    custom_inst_text.insert("1.0", settings.get("luna_custom_instructions", ""))

    # 5. Área de Teste Ao Vivo da Personalidade
    test_frame = tk.Frame(body, bg="#FFF5DF", bd=2, relief="sunken", padx=10, pady=8)
    test_frame.pack(fill="both", expand=True, pady=(0, 10))

    tk.Label(
        test_frame,
        text="🧪 Prévia ao Vivo da Personalidade GPT Luna (Avatar: Deivdson):",
        font=("Segoe UI", 9, "bold"),
        bg="#FFF5DF",
        fg="#43285C",
    ).pack(anchor="w")

    preview_lbl = tk.Label(
        test_frame,
        text="Clique em 'Testar Personalidade Agora' para ver como o avatar responde com o GPT Luna!",
        font=("Georgia", 10),
        bg="#FFF5DF",
        fg="#3A1E08",
        justify="left",
        wraplength=680,
        anchor="w",
    )
    preview_lbl.pack(fill="both", expand=True, pady=(4, 0))

    def _save_current_fields() -> Dict[str, Any]:
        updated = load_llm_settings()
        updated["luna_enabled"] = bool(luna_enabled_var.get())
        updated["luna_autonomous_speech"] = bool(luna_auto_speech_var.get())
        updated["luna_mood"] = mood_var.get()
        updated["luna_provider"] = provider_var.get()
        updated["luna_model"] = model_var.get().strip() or "gpt-6-luna"
        updated["luna_api_key"] = key_var.get().strip()
        updated["luna_endpoint"] = endpoint_var.get().strip() or "https://api.openai.com/v1/chat/completions"
        updated["luna_custom_instructions"] = custom_inst_text.get("1.0", "end").strip()
        save_llm_settings(updated)
        if on_status_changed:
            on_status_changed(updated["luna_enabled"])
        return updated

    def _on_test_click():
        _save_current_fields()
        preview_lbl.configure(text="🌙 GPT Luna está pensando...")

        def _worker():
            reply = generate_gpt_luna_reply(
                char_name="Deivdson",
                persona_bio="Pesquisador e desenvolvedor apaixonado por IA, código e Stardew Valley.",
                hearts=9,
                user_msg="Oi Luna! Como você está se sentindo aqui na minha área de trabalho hoje?",
            )
            if win.winfo_exists():
                win.after(0, lambda: preview_lbl.configure(text=reply))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_save_and_close():
        updated = _save_current_fields()
        status_str = "ATIVADA ✨" if updated["luna_enabled"] else "DESATIVADA"
        messagebox.showinfo(
            "GPT Luna Salvo",
            f"Configurações do GPT Luna salvas com sucesso!\n\n"
            f"• Status: Personalidade {status_str}\n"
            f"• Estilo: {updated['luna_mood']}\n"
            f"• Modelo: {updated['luna_model']}",
            parent=win,
        )
        win.destroy()

    btn_row = tk.Frame(body, bg="#F7E2B8")
    btn_row.pack(fill="x")

    tk.Button(
        btn_row,
        text="🧪 Testar Personalidade Agora",
        command=_on_test_click,
        bg="#6C3B8C",
        fg="white",
        font=("Segoe UI", 9, "bold"),
        padx=12,
        pady=5,
        cursor="hand2",
    ).pack(side="left")

    tk.Button(
        btn_row,
        text="💾 Salvar & Ativar GPT Luna",
        command=_on_save_and_close,
        bg="#3E8E4C",
        fg="white",
        font=("Segoe UI", 10, "bold"),
        padx=16,
        pady=5,
        cursor="hand2",
    ).pack(side="right")

    tk.Button(
        btn_row,
        text="Cancelar",
        command=win.destroy,
        bg="#8C4A20",
        fg="white",
        font=("Segoe UI", 9, "bold"),
        padx=10,
        pady=5,
        cursor="hand2",
    ).pack(side="right", padx=(0, 8))
