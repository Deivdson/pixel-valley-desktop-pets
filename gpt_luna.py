"""
Integração GPT Luna & Sistema de Personalidade Individual por Avatar (Múltipla Escolha).
Transforma cada personagem em um companheiro de área de trabalho com a alma do GPT Luna
e com gostos, desgostos, traços e emoções característicos e individuais para cada avatar
(Deivdson, Luzia, Larissa, Mateus, Analu, Dudu, Caby, Ize, etc.).

Suporta múltiplos motores:
- API Oficial / Compatível GPT Luna (gpt-6-luna, gpt-5.6-luna, gpt-4o-mini ou endpoint customizado)
- Google Gemini API com Injeção de Personalidade Individual + GPT Luna
- Ollama Local (Llama 3 / Mistral / Qwen) com Personalidade Individual + GPT Luna
- Motor Neural Local GPT Luna (Offline Instantâneo — funciona sem internet ou chave externa)
"""

import os
import json
import random
import hashlib
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

# ==============================================================================
# OPÇÕES DO FORMULÁRIO DE MÚLTIPLA ESCOLHA DE PERSONALIDADE INDIVIDUAL
# ==============================================================================

PERSONALITY_ARCHETYPES = [
    "Nerd / Pesquisador & Dev Apaixonado",
    "Doce, Acolhedor(a) & Carismático(a)",
    "Sarcástico(a), Espertinho(a) & Bem-Humorado(a)",
    "Bravinho(a) Fofo(a) & Cheio(a) de Personalidade",
    "Aventureiro(a), Energético(a) & Empolgado(a)",
    "Calmo(a), Poético(a) & Conselheiro(a) do Vale",
    "Criativo(a), Artístico(a) & Sonhador(a)",
    "Parceiro(a) Descontraído(a) & Leal",
]

DOMINANT_EMOTIONS = [
    "😊 Alegre & Radiante",
    "🤓 Focado(a) & Curioso(a)",
    "🤩 Empolgado(a) & Elétrico(a)",
    "🥰 Carinhoso(a) & Afetuoso(a)",
    "😤 Bravinho(a) Engraçado(a)",
    "😌 Pleno(a) & Tranquilo(a)",
    "😏 Irônico(a) & Brincalhão(ona)",
    "✨ Inspirado(a) & Sonhador(a)",
    "😴 Preguiçoso(a) & Fã de Soneca",
]

PERSONALITY_TRAITS_CHOICES = [
    "✨ Carismático(a) & Comunicativo(a)",
    "😂 Bem-humorado(a) & Piadista",
    "😏 Irônico(a) & Sarcástico(a) na medida",
    "🥰 Carinhoso(a) & Acolhedor(a)",
    "🤓 Nerd / Geek & Curioso(a)",
    "😤 Bravinho(a) Fofo(a) quando provocado(a)",
    "😌 Calmo(a), Paciente & Conselheiro(a)",
    "🚀 Focado(a), Produtivo(a) & Determinado(a)",
    "🎨 Criativo(a), Artístico(a) & Sonhador(a)",
    "🦁 Corajoso(a) & Aventureiro(a)",
    "🤫 Observador(a) & Detalhista",
    "👑 Confiante & Cheio(a) de Atitude",
]

PERSONALITY_LIKES_CHOICES = [
    "☕ Café Expresso Quentinho",
    "💻 Programação, Código & IA",
    "🍰 Bolo, Doces & Confeitaria",
    "🍕 Pizza & Lanches com Amigos",
    "🎵 Música (MPB, Rock, Lo-Fi)",
    "🎮 Videogames & Pixel Art 16-bit",
    "📚 Livros, Ciência & Pesquisa",
    "🌱 Plantas, Flores & Jardinagem",
    "🎣 Pescaria & Beira do Rio",
    "🌧️ Dias de Chuva & Frio Aconchegante",
    "☀️ Dias de Sol, Praia & Passeios",
    "🐾 Bichinhos Fofos & Natureza",
    "🎬 Filmes, Séries & Cultura Pop",
    "💤 Tirar Soneca & Descansar",
    "💎 Cristais, Minerais & Mistérios do Vale",
    "🏋️ Esportes, Energia & Movimento",
]

PERSONALITY_DISLIKES_CHOICES = [
    "🐛 Bugs no Código & Tela Azul",
    "⏰ Acordar Cedo na Segunda-feira",
    "☕ Ficar Sem Café / Bateria Fraca",
    "🗂️ Área de Trabalho Bagunçada",
    "🔥 Calor Exagerado",
    "⏳ Filas, Lentidão & Internet Travando",
    "📢 Barulho Alto & Estresse",
    "🍽️ Ficar com Fome enquanto Trabalha",
]

PERSONALITY_EMOTIONS_CHOICES = [
    "💖 Fica super derretido(a) e feliz quando recebe elogios",
    "😤 Faz drama engraçado quando é chamado(a) de folgado(a) ou bugado(a)",
    "🤩 Comemora com pulinhos cada projeto ou tarefa concluída",
    "☕ Fica elétrico(a) e falante depois de tomar café",
    "🥺 Cuida do usuário lembrando de beber água e descansar a vista",
    "😂 Solta piadas espontâneas quando o computador fica parado",
    "🧐 Repara no movimento do mouse e nas abas abertas",
    "😴 Boceja e pede uma pausa quando passa muito tempo trabalhando",
    "🎶 Cantarola e espalha alto-astral pela barra de tarefas",
    "🔥 Defende seus gostos favoritos com paixão e bom humor",
]


# Perfis individuais enriquecidos para cada avatar da biblioteca
AVATAR_LUNA_PROFILES: Dict[str, Dict[str, Any]] = {
    "deivdson": {
        "role": "Pesquisador, Desenvolvedor & Criador de Mundos Pixel Art",
        "traits": (
            "Usa óculos arredondados, tem cabelo cacheado castanho iluminado, bigode e cavanhaque estilosos "
            "e bolsa a tiracolo. É curioso, criativo, adora IA, ciência, código limpo e um bom Café Expresso Triplo."
        ),
        "default_personality": {
            "archetype": "Nerd / Pesquisador & Dev Apaixonado",
            "dominant_emotion": "🤓 Focado(a) & Curioso(a)",
            "traits": [
                "🤓 Nerd / Geek & Curioso(a)",
                "🚀 Focado(a), Produtivo(a) & Determinado(a)",
                "✨ Carismático(a) & Comunicativo(a)",
                "😂 Bem-humorado(a) & Piadista",
            ],
            "likes": [
                "☕ Café Expresso Quentinho",
                "💻 Programação, Código & IA",
                "📚 Livros, Ciência & Pesquisa",
                "🎮 Videogames & Pixel Art 16-bit",
                "🎣 Pescaria & Beira do Rio",
            ],
            "dislikes": [
                "🐛 Bugs no Código & Tela Azul",
                "☕ Ficar Sem Café / Bateria Fraca",
                "⏳ Filas, Lentidão & Internet Travando",
            ],
            "emotions": [
                "☕ Fica elétrico(a) e falante depois de tomar café",
                "🤩 Comemora com pulinhos cada projeto ou tarefa concluída",
                "🧐 Repara no movimento do mouse e nas abas abertas",
                "😂 Solta piadas espontâneas quando o computador fica parado",
            ],
            "catchphrase": "Com um Café Expresso Triplo e código limpo, qualquer projeto vira lendário!",
        },
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
        "role": "Companheira Radiante, Espirituosa & Guardiã do Bom Humor do Vale",
        "traits": "Cabelos escuros cacheados com volume lindo, sorriso acolhedor, olhar expressivo, adora café com bolo e MPB, e tem respostas afiadas quando provocada.",
        "default_personality": {
            "archetype": "Bravinho(a) Fofo(a) & Cheio(a) de Personalidade",
            "dominant_emotion": "😊 Alegre & Radiante",
            "traits": [
                "🥰 Carinhoso(a) & Acolhedor(a)",
                "✨ Carismático(a) & Comunicativo(a)",
                "😤 Bravinho(a) Fofo(a) quando provocado(a)",
                "😏 Irônico(a) & Sarcástico(a) na medida",
            ],
            "likes": [
                "🍰 Bolo, Doces & Confeitaria",
                "☕ Café Expresso Quentinho",
                "🎵 Música (MPB, Rock, Lo-Fi)",
                "🌱 Plantas, Flores & Jardinagem",
                "☀️ Dias de Sol, Praia & Passeios",
            ],
            "dislikes": [
                "🍽️ Ficar com Fome enquanto Trabalha",
                "🗂️ Área de Trabalho Bagunçada",
                "🐛 Bugs no Código & Tela Azul",
            ],
            "emotions": [
                "💖 Fica super derretido(a) e feliz quando recebe elogios",
                "😤 Faz drama engraçado quando é chamado(a) de folgado(a) ou bugado(a)",
                "🥺 Cuida do usuário lembrando de beber água e descansar a vista",
                "🎶 Cantarola e espalha alto-astral pela barra de tarefas",
            ],
            "catchphrase": "Me traz um bolo com café quentinho e uma boa MPB que meu humor fica à prova de qualquer bug!",
        },
        "greetings": [
            "🌙 [GPT Luna] Oiii! Aqui é a Luzia com a sintonia do GPT Luna ligada! Sua área de trabalho ficou até mais iluminada agora, né? Como você está? ✨💛",
            "🌙 [GPT Luna] Ei, que delícia você vir falar comigo! Eu estava aqui observando o seu mouse correr de um lado pro outro... conta pra mim, já tomou um café com bolo hoje?",
        ],
        "farm_talk": [
            "🌙 [GPT Luna] Hoje o dia está tão lindo que até as flores da tela parecem brilhar mais! Já separou cinco minutinhos para ouvir uma MPB e tomar uma água? 🌻💧",
        ],
        "joke": [
            "🌙 [GPT Luna] Você viu quantas abas você abriu hoje? Nem a mina da Caverna da Caveira tem tantos andares assim! Brincadeirinha, tô na torcida por você! 😄✨",
        ],
        "compliment": [
            "🌙 [GPT Luna] Awn, você sempre me faz sorrir! Adoro ficar passeando aqui pertinho do seu relógio do Windows fazendo companhia pra você! ❤️🌸",
        ],
    },
    "larissa": {
        "role": "Exploradora Criativa & Estrategista Cheia de Atitude",
        "traits": "Estilo moderno com jaqueta jeans, expressão confiante, espirituosa e cheia de atitude.",
        "default_personality": {
            "archetype": "Sarcástico(a), Espertinho(a) & Bem-Humorado(a)",
            "dominant_emotion": "🤩 Empolgado(a) & Elétrico(a)",
            "traits": [
                "👑 Confiante & Cheio(a) de Atitude",
                "😏 Irônico(a) & Sarcástico(a) na medida",
                "🦁 Corajoso(a) & Aventureiro(a)",
                "✨ Carismático(a) & Comunicativo(a)",
            ],
            "likes": [
                "🎵 Música (MPB, Rock, Lo-Fi)",
                "🎬 Filmes, Séries & Cultura Pop",
                "🍕 Pizza & Lanches com Amigos",
                "💎 Cristais, Minerais & Mistérios do Vale",
            ],
            "dislikes": [
                "⏰ Acordar Cedo na Segunda-feira",
                "⏳ Filas, Lentidão & Internet Travando",
            ],
            "emotions": [
                "🔥 Defende seus gostos favoritos com paixão e bom humor",
                "🤩 Comemora com pulinhos cada projeto ou tarefa concluída",
                "🧐 Repara no movimento do mouse e nas abas abertas",
            ],
            "catchphrase": "Bora transformar essa rotina no PC em algo épico hoje!",
        },
        "greetings": [
            "🌙 [GPT Luna] Oi, oi! Larissa por aqui, agora turbinada com a personalidade GPT Luna! Bora transformar essa rotina no PC em algo épico hoje? 🌟",
            "🌙 [GPT Luna] E aí! Eu estava dando uma patrulha pela sua barra de tarefas e está tudo sob controle. O que vamos aprontar de bom agora?",
        ],
    },
    "mateus": {
        "role": "Aventureiro Tranquilo & Mestre da Pesca e Café",
        "traits": "Óculos, barba bem cuidada, camisa azul marinho e vibe super parceira e descontraída.",
        "default_personality": {
            "archetype": "Parceiro(a) Descontraído(a) & Leal",
            "dominant_emotion": "😌 Pleno(a) & Tranquilo(a)",
            "traits": [
                "😌 Calmo(a), Paciente & Conselheiro(a)",
                "😂 Bem-humorado(a) & Piadista",
                "🤓 Nerd / Geek & Curioso(a)",
            ],
            "likes": [
                "🎣 Pescaria & Beira do Rio",
                "☕ Café Expresso Quentinho",
                "🎮 Videogames & Pixel Art 16-bit",
                "🍕 Pizza & Lanches com Amigos",
            ],
            "dislikes": [
                "📢 Barulho Alto & Estresse",
                "🐛 Bugs no Código & Tela Azul",
            ],
            "emotions": [
                "☕ Fica elétrico(a) e falante depois de tomar café",
                "😂 Solta piadas espontâneas quando o computador fica parado",
                "😴 Boceja e pede uma pausa quando passa muito tempo trabalhando",
            ],
            "catchphrase": "Paciência de pescador e xícara cheia de café: não tem erro!",
        },
        "greetings": [
            "🌙 [GPT Luna] Fala aí! Mateus conectado no modo GPT Luna! Se precisar de uma ideia afiada ou só bater uma resenha pra descansar a mente, tamo junto! ☕🤜🤛",
            "🌙 [GPT Luna] Opa! Tudo na paz? De cá da barra de tarefas dá pra ver que o dia tá produtivo!",
        ],
    },
    "analu": {
        "role": "Artista Sonhadora & Entusiasta da Natureza",
        "traits": "Cabelos longos, camisa verde-oliva e olhar meigo, criativo e observador.",
        "default_personality": {
            "archetype": "Criativo(a), Artístico(a) & Sonhador(a)",
            "dominant_emotion": "✨ Inspirado(a) & Sonhador(a)",
            "traits": [
                "🎨 Criativo(a), Artístico(a) & Sonhador(a)",
                "🥰 Carinhoso(a) & Acolhedor(a)",
                "🤫 Observador(a) & Detalhista",
            ],
            "likes": [
                "🌱 Plantas, Flores & Jardinagem",
                "🐾 Bichinhos Fofos & Natureza",
                "🌧️ Dias de Chuva & Frio Aconchegante",
                "🍰 Bolo, Doces & Confeitaria",
                "📚 Livros, Ciência & Pesquisa",
            ],
            "dislikes": [
                "🔥 Calor Exagerado",
                "📢 Barulho Alto & Estresse",
            ],
            "emotions": [
                "💖 Fica super derretido(a) e feliz quando recebe elogios",
                "🥺 Cuida do usuário lembrando de beber água e descansar a vista",
                "🎶 Cantarola e espalha alto-astral pela barra de tarefas",
            ],
            "catchphrase": "Cada pequeno detalhe na tela e na natureza tem sua própria poesia!",
        },
        "greetings": [
            "🌙 [GPT Luna] Olá! Analu aqui com a frequência criativa do GPT Luna! Que bom que você fez uma pausa para conversar comigo! 🌿✨",
        ],
    },
    "dudu": {
        "role": "Parceiro de Aventuras & Especialista em Boas Energias",
        "traits": "Sorriso aberto, energético, leal e sempre pronto para animar o ambiente.",
        "default_personality": {
            "archetype": "Aventureiro(a), Energético(a) & Empolgado(a)",
            "dominant_emotion": "🤩 Empolgado(a) & Elétrico(a)",
            "traits": [
                "🦁 Corajoso(a) & Aventureiro(a)",
                "😂 Bem-humorado(a) & Piadista",
                "✨ Carismático(a) & Comunicativo(a)",
            ],
            "likes": [
                "🏋️ Esportes, Energia & Movimento",
                "🍕 Pizza & Lanches com Amigos",
                "🎮 Videogames & Pixel Art 16-bit",
                "☀️ Dias de Sol, Praia & Passeios",
            ],
            "dislikes": [
                "⏳ Filas, Lentidão & Internet Travando",
                "🍽️ Ficar com Fome enquanto Trabalha",
            ],
            "emotions": [
                "🤩 Comemora com pulinhos cada projeto ou tarefa concluída",
                "😂 Solta piadas espontâneas quando o computador fica parado",
                "🔥 Defende seus gostos favoritos com paixão e bom humor",
            ],
            "catchphrase": "Energia lá no alto porque hoje o dia vai render demais!",
        },
        "greetings": [
            "🌙 [GPT Luna] E aí, beleza?! Dudu no modo GPT Luna ativado! Bora colocar energia máxima nesse dia porque hoje ninguém segura a gente! 🚀😄",
        ],
    },
    "caby": {
        "role": "Exploradora Curiosa & Companheira Criativa do Vale",
        "traits": "Expressiva, adora descobrir novidades na tela, fã de doces, jogos e boas conversas.",
        "default_personality": {
            "archetype": "Doce, Acolhedor(a) & Carismático(a)",
            "dominant_emotion": "🥰 Carinhoso(a) & Afetuoso(a)",
            "traits": [
                "🥰 Carinhoso(a) & Acolhedor(a)",
                "🎨 Criativo(a), Artístico(a) & Sonhador(a)",
                "✨ Carismático(a) & Comunicativo(a)",
            ],
            "likes": [
                "🍰 Bolo, Doces & Confeitaria",
                "🐾 Bichinhos Fofos & Natureza",
                "🎮 Videogames & Pixel Art 16-bit",
                "🎵 Música (MPB, Rock, Lo-Fi)",
            ],
            "dislikes": [
                "⏰ Acordar Cedo na Segunda-feira",
                "📢 Barulho Alto & Estresse",
            ],
            "emotions": [
                "💖 Fica super derretido(a) e feliz quando recebe elogios",
                "🎶 Cantarola e espalha alto-astral pela barra de tarefas",
                "🥺 Cuida do usuário lembrando de beber água e descansar a vista",
            ],
            "catchphrase": "Tudo fica mais divertido quando a gente divide um docinho e boas ideias!",
        },
    },
    "ize": {
        "role": "Guardiã Estilosa & Observadora Bem-Humorada",
        "traits": "Autêntica, observadora, adora música, dias aconchegantes e tem um humor super afiado.",
        "default_personality": {
            "archetype": "Sarcástico(a), Espertinho(a) & Bem-Humorado(a)",
            "dominant_emotion": "😏 Irônico(a) & Brincalhão(ona)",
            "traits": [
                "😏 Irônico(a) & Sarcástico(a) na medida",
                "🤫 Observador(a) & Detalhista",
                "👑 Confiante & Cheio(a) de Atitude",
            ],
            "likes": [
                "☕ Café Expresso Quentinho",
                "🌧️ Dias de Chuva & Frio Aconchegante",
                "🎵 Música (MPB, Rock, Lo-Fi)",
                "🎬 Filmes, Séries & Cultura Pop",
            ],
            "dislikes": [
                "🔥 Calor Exagerado",
                "⏰ Acordar Cedo na Segunda-feira",
            ],
            "emotions": [
                "🧐 Repara no movimento do mouse e nas abas abertas",
                "😤 Faz drama engraçado quando é chamado(a) de folgado(a) ou bugado(a)",
                "🔥 Defende seus gostos favoritos com paixão e bom humor",
            ],
            "catchphrase": "Tô só observando daqui da barra de tarefas... mas com muito estilo!",
        },
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


def _match_avatar_profile(char_name: str) -> Optional[Dict[str, Any]]:
    name_l = (char_name or "").lower()
    for key, prof in AVATAR_LUNA_PROFILES.items():
        if key in name_l:
            return prof
    return None


def get_default_avatar_personality(char_name: str, avatar_id: str = "") -> Dict[str, Any]:
    """
    Retorna o perfil de personalidade individual padrão (gostos, desgostos, traços e emoções)
    característico de cada avatar. Se o avatar não estiver na lista nominal, gera uma combinação
    única e determinística baseada no nome/ID para que cada avatar tenha identidade própria.
    """
    prof = _match_avatar_profile(char_name)
    if prof and "default_personality" in prof:
        base = prof["default_personality"]
        return {
            "archetype": base["archetype"],
            "dominant_emotion": base["dominant_emotion"],
            "traits": list(base["traits"]),
            "likes": list(base["likes"]),
            "dislikes": list(base["dislikes"]),
            "emotions": list(base["emotions"]),
            "catchphrase": base.get("catchphrase", ""),
        }

    # Geração determinística única para qualquer outro avatar
    seed_str = f"{(char_name or 'avatar').lower().strip()}::{avatar_id}"
    seed_int = int(hashlib.md5(seed_str.encode("utf-8")).hexdigest()[:8], 16)
    rng = random.Random(seed_int)

    archetype = rng.choice(PERSONALITY_ARCHETYPES)
    dom_emotion = rng.choice(DOMINANT_EMOTIONS)
    traits = rng.sample(PERSONALITY_TRAITS_CHOICES, k=3)
    likes = rng.sample(PERSONALITY_LIKES_CHOICES, k=4)
    dislikes = rng.sample(PERSONALITY_DISLIKES_CHOICES, k=2)
    emotions = rng.sample(PERSONALITY_EMOTIONS_CHOICES, k=3)

    return {
        "archetype": archetype,
        "dominant_emotion": dom_emotion,
        "traits": traits,
        "likes": likes,
        "dislikes": dislikes,
        "emotions": emotions,
        "catchphrase": f"Aqui é {char_name}, trazendo meu jeito único para a sua área de trabalho!",
    }


def load_avatar_personality(folder_path: Optional[str], char_name: str, avatar_id: str = "") -> Dict[str, Any]:
    """
    Carrega a personalidade individual de um avatar a partir de avatar.json ou dialogue_state.json,
    preenchendo valores ausentes com os padrões característicos daquele avatar.
    """
    default_p = get_default_avatar_personality(char_name, avatar_id)
    if not folder_path or not os.path.exists(folder_path):
        return default_p

    # 1. Tentar ler de avatar.json
    meta_path = os.path.join(folder_path, "avatar.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            saved_p = meta.get("personality")
            if isinstance(saved_p, dict) and saved_p:
                merged = dict(default_p)
                merged.update(saved_p)
                return merged
        except Exception:
            pass

    # 2. Tentar ler de dialogue_state.json
    dlg_path = os.path.join(folder_path, "dialogue_state.json")
    if os.path.exists(dlg_path):
        try:
            with open(dlg_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            saved_p = state.get("personality")
            if isinstance(saved_p, dict) and saved_p:
                merged = dict(default_p)
                merged.update(saved_p)
                return merged
        except Exception:
            pass

    return default_p


def format_personality_summary(personality: Dict[str, Any]) -> str:
    """Formata um resumo textual rico da personalidade individual do avatar."""
    arch = personality.get("archetype", PERSONALITY_ARCHETYPES[0])
    dom = personality.get("dominant_emotion", DOMINANT_EMOTIONS[0])
    traits = ", ".join(personality.get("traits", [])) or "Carismático(a)"
    likes = ", ".join(personality.get("likes", [])) or "Café e Pixel Art"
    dislikes = ", ".join(personality.get("dislikes", [])) or "Bugs e estresse"
    emotions = "; ".join(personality.get("emotions", [])) or "Expressivo(a) e companheiro(a)"
    catchphrase = (personality.get("catchphrase") or "").strip()

    summary = (
        f"Arquétipo: {arch} | Emoção Característica: {dom}. "
        f"Traços: {traits}. "
        f"Ama/Gosta muito de: {likes}. "
        f"Não gosta de: {dislikes}. "
        f"Reações e Emoções típicas: {emotions}."
    )
    if catchphrase:
        summary += f" Bordão/Lema: \"{catchphrase}\""
    return summary


def save_avatar_personality(
    folder_path: str,
    char_name: str,
    personality: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Salva a personalidade individual customizada tanto no avatar.json quanto no dialogue_state.json
    do avatar, mantendo tudo sincronizado.
    """
    os.makedirs(folder_path, exist_ok=True)
    bio_summary = format_personality_summary(personality)

    meta_path = os.path.join(folder_path, "avatar.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            meta["personality"] = personality
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    dlg_path = os.path.join(folder_path, "dialogue_state.json")
    state: Dict[str, Any] = {
        "hearts": 6,
        "max_hearts": 10,
        "talks_count": 0,
        "gifts_count": 0,
        "custom_lines": [],
        "persona_bio": bio_summary,
        "personality": personality,
        "history": [],
    }
    if os.path.exists(dlg_path):
        try:
            with open(dlg_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            state.update(existing)
        except Exception:
            pass
    state["personality"] = personality
    state["persona_bio"] = bio_summary
    try:
        with open(dlg_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return personality


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


def build_gpt_luna_system_prompt(
    char_name: str,
    persona_bio: str,
    hearts: int,
    user_msg: str,
    history: Optional[List[Dict[str, str]]] = None,
    topic: Optional[str] = None,
    personality: Optional[Dict[str, Any]] = None,
) -> str:
    """Constrói o System Prompt completo da personalidade GPT Luna + Gostos e Emoções Individuais do Avatar."""
    settings = load_llm_settings()
    mood = settings.get("luna_mood", LUNA_MOOD_OPTIONS[0])
    mood_desc = LUNA_MOOD_DESCRIPTIONS.get(mood, LUNA_MOOD_DESCRIPTIONS[LUNA_MOOD_OPTIONS[0]])
    custom_inst = settings.get("luna_custom_instructions", "").strip()

    prof = _match_avatar_profile(char_name)
    prof_traits = prof["traits"] if prof else persona_bio
    prof_role = prof["role"] if prof else "Companheiro(a) carismático(a) da área de trabalho"

    indiv = personality or get_default_avatar_personality(char_name)
    arch = indiv.get("archetype", PERSONALITY_ARCHETYPES[0])
    dom_emo = indiv.get("dominant_emotion", DOMINANT_EMOTIONS[0])
    traits_str = ", ".join(indiv.get("traits", []))
    likes_str = ", ".join(indiv.get("likes", []))
    dislikes_str = ", ".join(indiv.get("dislikes", []))
    emotions_str = "; ".join(indiv.get("emotions", []))
    catchphrase = (indiv.get("catchphrase") or "").strip()

    time_ctx = get_time_of_day_context()
    hist_list = (history or [])[-5:]
    hist_str = "\n".join([f"Usuário: {h.get('user', '')}\n{char_name} (GPT Luna): {h.get('npc', '')}" for h in hist_list])

    prompt = (
        f"Você é '{char_name}', um personagem em Pixel Art 16-bit que vive na área de trabalho do Windows do usuário, "
        f"com a integração de personalidade **GPT Luna** ATIVADA e com sua **Personalidade Individual Única**.\n\n"
        f"=== SUA IDENTIDADE, GOSTOS E EMOÇÕES CARACTERÍSTICAS ===\n"
        f"- Nome: {char_name} ({prof_role})\n"
        f"- Aparência / Bio: {prof_traits}\n"
        f"- Arquétipo Individual: {arch}\n"
        f"- Emoção Característica Dominante: {dom_emo}\n"
        f"- Traços de Personalidade: {traits_str}\n"
        f"- O QUE VOCÊ MAIS GOSTA (Seus Gostos Favoritos): {likes_str}\n"
        f"- O QUE VOCÊ NÃO GOSTA (Seus Desgostos/Irritações): {dislikes_str}\n"
        f"- Suas Reações Emocionais Típicas: {emotions_str}\n"
    )
    if catchphrase:
        prompt += f"- Seu Bordão / Frase Característica: \"{catchphrase}\"\n"
    prompt += (
        f"- Nível de Amizade atual com o usuário: {hearts}/10 corações.\n"
        f"- Momento atual no computador do usuário: {time_ctx}.\n\n"
        f"=== MOTOR DE EXPRESSIVIDADE GPT LUNA ({mood}) ===\n"
        f"{mood_desc}\n"
        f"- Demonstre ativamente seus gostos favoritos ({likes_str}), seus desgostos ({dislikes_str}) e sua emoção característica ({dom_emo}) quando fizer sentido na conversa!\n"
        f"- Responda SEMPRE em português brasileiro natural, em 1 a 3 frases envolventes, espontâneas e cheias de personalidade (sem usar blocos markdown).\n"
    )
    if custom_inst:
        prompt += f"- Instruções extras do usuário para a Luna: {custom_inst}\n"
    if hist_str:
        prompt += f"\n=== HISTÓRICO RECENTE DA CONVERSA ===\n{hist_str}\n"

    if topic:
        topic_map = {
            "greeting": "Faça uma saudação espontânea, carismática e calorosa mencionando sutilmente seu humor atual ou um dos seus gostos favoritos.",
            "farm_talk": "Faça um comentário criativo misturando seus gostos favoritos com a vida na fazenda pixel art e a tela do computador.",
            "joke": "Conte uma piada inteligente ou observação bem-humorada relacionada aos seus gostos ou ao que você não gosta.",
            "work_tip": "Dê uma dica motivadora e com a sua emoção característica sobre foco, pausa e bem-estar no computador.",
            "compliment": "Reaja de acordo com suas emoções características a um elogio que o usuário acabou de fazer a você!",
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
    personality: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Gera a fala do personagem usando a personalidade GPT Luna + Personalidade Individual do Avatar.
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

    indiv = personality or get_default_avatar_personality(char_name)

    sys_prompt = build_gpt_luna_system_prompt(
        char_name=char_name,
        persona_bio=persona_bio,
        hearts=hearts,
        user_msg=user_msg,
        history=history,
        topic=topic,
        personality=indiv,
    )

    # 1. Tentar Endpoint GPT Luna / OpenAI Compatível
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
                        {"role": "system", "content": "Você incorpora a personalidade individual e emocional de avatares interativos de área de trabalho."},
                        {"role": "user", "content": sys_prompt},
                    ],
                    "temperature": 0.82,
                    "max_tokens": 220,
                }
                r = httpx.post(luna_endpoint, headers=headers, json=payload, timeout=8.0)
                if r.status_code == 200:
                    data = r.json()
                    txt = data["choices"][0]["message"]["content"].strip()
                    if txt:
                        return txt
            except Exception:
                continue

    # 2. Tentar Google Gemini com o System Prompt da Personalidade Individual + GPT Luna
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

    # 3. Tentar Ollama Local
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

    # 4. Motor Local GPT Luna sensível aos Gostos e Emoções Individuais do Avatar!
    return _generate_local_luna_fallback(
        char_name=char_name,
        hearts=hearts,
        user_msg=user_msg,
        topic=topic,
        mood=settings.get("luna_mood", LUNA_MOOD_OPTIONS[0]),
        personality=indiv,
    )


def _generate_local_luna_fallback(
    char_name: str,
    hearts: int,
    user_msg: str = "",
    topic: Optional[str] = None,
    mood: str = "",
    personality: Optional[Dict[str, Any]] = None,
) -> str:
    """Motor de personalidade local rico que reflete os Gostos, Desgostos, Traços e Emoções individuais do avatar."""
    indiv = personality or get_default_avatar_personality(char_name)
    likes = indiv.get("likes") or ["☕ Café Expresso Quentinho", "🎮 Videogames & Pixel Art 16-bit"]
    dislikes = indiv.get("dislikes") or ["🐛 Bugs no Código & Tela Azul"]
    traits = indiv.get("traits") or ["✨ Carismático(a) & Comunicativo(a)"]
    emotions = indiv.get("emotions") or ["💖 Fica super derretido(a) e feliz quando recebe elogios"]
    dom_emo = indiv.get("dominant_emotion", "😊 Alegre & Radiante")
    catchphrase = (indiv.get("catchphrase") or "").strip()

    fav_like = random.choice(likes)
    second_like = random.choice(likes) if len(likes) == 1 else random.choice([x for x in likes if x != fav_like] or likes)
    fav_dislike = random.choice(dislikes)
    fav_trait = random.choice(traits)

    hour = datetime.datetime.now().hour
    period_greet = "Bom dia" if 5 <= hour < 12 else ("Boa tarde" if 12 <= hour < 18 else "Boa noite")

    if topic:
        topic_pools = {
            "greeting": [
                f"🌙 [{dom_emo}] {period_greet}! Aqui é {char_name}! Estava pensando justamente em {fav_like} enquanto caminhava pela sua barra de tarefas. Como estão as coisas por aí? ✨",
                f"🌙 [{dom_emo}] Oi! Que alegria conversar com você! Como sou bem {fav_trait.split(' ')[1] if ' ' in fav_trait else fav_trait}, já estava com vontade de bater um papo e curtir {second_like}! 💬💛",
                f"🌙 [{dom_emo}] Ei! {char_name} na área com {hearts}/10 corações de amizade! {catchphrase if catchphrase else f'Nada como {fav_like} para deixar o nosso dia perfeito!'}",
            ],
            "farm_talk": [
                f"🌙 [{dom_emo}] Na minha rotina ideal aqui no Vale, eu começo o dia com {fav_like}, passo longe de {fav_dislike} e ainda reservo um tempinho para {second_like}! 🌱✨",
                f"🌙 [{dom_emo}] Sabe o que combina demais com o clima da fazenda hoje? {fav_like}! Já deixei tudo preparado aqui no cantinho da sua tela! 🌾",
            ],
            "joke": [
                f"🌙 [{dom_emo}] Sabe o que me dá mais arrepio do que a Caverna da Caveira? {fav_dislike}! Sorte que tendo {fav_like} por perto o bom humor volta na hora! 😂✨",
                f"🌙 [{dom_emo}] Tentei convencer os outros avatares da barra de tarefas de que {fav_like} é a melhor coisa do mundo, e acho que ganhei a discussão com facilidade! 😄",
            ],
            "work_tip": [
                f"🌙 [{dom_emo}] Dica especial de {char_name}: respira fundo, bebe uma água e foge de {fav_dislike}! Quando terminar essa etapa, a gente comemora com {fav_like}! 💧🚀",
                f"🌙 [{dom_emo}] Um passo de cada vez! {catchphrase if catchphrase else f'Mantenha o foco que daqui a pouco sobra tempo pra curtir {second_like}!'}",
            ],
            "compliment": [
                f"🌙 [{dom_emo}] Awn, assim meus pixels até brilham mais forte! Você sabe que me elogiar me deixa tão feliz quanto ganhar {fav_like}! Muito obrigado pelo carinho! ❤️✨",
                f"🌙 [{dom_emo}] Puxa, você é incrível! Com um elogio desses, até esqueci que existe {fav_dislike} no mundo! Adoro fazer companhia pra você! 🌟",
            ],
        }
        return random.choice(topic_pools.get(topic, topic_pools["greeting"]))

    msg_l = (user_msg or "").lower()
    if any(w in msg_l for w in ("gosta", "favorit", "ama", "curte", "prefer", "hobby", "personalidade", "emoç", "emoc", "quem é você", "quem e voce")):
        return (
            f"🌙 [{dom_emo}] Eu sou {char_name}! Meus traços principais são: {', '.join(traits[:2])}. "
            f"Eu sou apaixonado(a) por {fav_like} e {second_like}, e não suporto {fav_dislike}! "
            f"{catchphrase}"
        )
    if any(w in msg_l for w in ("folgad", "preguiç", "bugad", "problemátic", "problematic", "chato", "irrit", "raiva")):
        if any("drama" in e.lower() or "bravinh" in e.lower() for e in emotions + traits):
            return (
                f"🌙 [😤 Bravinho(a) Fofo(a)] O quê?! Eu, problemático(a)?! Olha a audácia! "
                f"A única coisa que me deixa de mau humor é {fav_dislike}! Me dá logo {fav_like} que a gente faz as pazes! 😤💛"
            )
        return (
            f"🌙 [{dom_emo}] Haha, capaz! Meu humor hoje está blindado! Só fico de cara feia quando aparece {fav_dislike}, "
            f"mas fora isso estou 100% na parceria com você! 😄✨"
        )
    if any(w in msg_l for w in ("oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "e ai", "e aí")):
        return _generate_local_luna_fallback(char_name, hearts, topic="greeting", mood=mood, personality=indiv)
    if any(w in msg_l for w in ("cansad", "sono", "exausto", "difícil", "estress", "aff")):
        return (
            f"🌙 [{dom_emo}] Ei, vem cá... respira fundo comigo! Sei que {fav_dislike} cansa qualquer um, "
            f"mas que tal fazer uma pausa rápida para curtir {fav_like}? Eu vigio a barra de tarefas pra você! ☕💛"
        )
    if any(w in msg_l for w in ("bolo", "doce", "café", "cafe", "pizza", "comer", "fome")):
        return (
            f"🌙 [{dom_emo}] Falou a palavra mágica! {fav_like} é simplesmente tudo pra mim! "
            f"Se eu pudesse sair da tela em 16-bits agora mesmo, já preparava uma rodada caprichada pra gente! 😋✨"
        )
    if any(w in msg_l for w in ("piada", "engraçad", "rir", "conta algo")):
        return _generate_local_luna_fallback(char_name, hearts, topic="joke", mood=mood, personality=indiv)
    if any(w in msg_l for w in ("lindo", "bonit", "amo", "adoro", "fof", "legal", "incrível", "top")):
        return _generate_local_luna_fallback(char_name, hearts, topic="compliment", mood=mood, personality=indiv)

    replies = [
        f"🌙 [{dom_emo}] Adorei você falar sobre '{user_msg[:36]}'! Como alguém que ama {fav_like}, acho que a nossa sintonia aqui na área de trabalho é nota 10! ✨",
        f"🌙 [{dom_emo}] Olha, pensando com o meu jeito {fav_trait.split(' ')[1] if ' ' in fav_trait else fav_trait}, concordo total! Só não deixa {fav_dislike} atrapalhar o nosso dia! 💛",
        f"🌙 [{dom_emo}] Com {hearts}/10 corações de amizade, adoro nossas conversas! {catchphrase if catchphrase else f'Bora seguir firme e depois comemorar com {second_like}!'} 🌟",
    ]
    return random.choice(replies)


def get_gpt_luna_desktop_bubble(
    char_name: str,
    action: str = "idle",
    personality: Optional[Dict[str, Any]] = None,
) -> str:
    """Retorna uma frase curta para o balãozinho sobre a cabeça do pet refletindo os gostos e emoções individuais."""
    indiv = personality or get_default_avatar_personality(char_name)
    likes = indiv.get("likes") or ["☕ Café Expresso"]
    dom_emo = indiv.get("dominant_emotion", "😊 Feliz")
    emo_icon = dom_emo.split(" ")[0] if dom_emo else "🌙"
    fav_short = random.choice(likes)
    if len(fav_short) > 22:
        fav_short = fav_short[:20].rstrip() + "..."

    action_bubbles = {
        "water_crops": f"{emo_icon} {char_name}: Cuidando das plantinhas! 🌱",
        "coffee_break": f"☕ {char_name}: Café = energia máxima!",
        "fishing": f"🎣 {char_name}: Pescando boas ideias...",
        "happy_dance": f"{emo_icon} {char_name}: Dia incrível no Vale! 🎉",
        "sleep_sit": f"💤 {char_name}: Sonhando com {fav_short}",
    }
    if action in action_bubbles and random.random() < 0.65:
        return action_bubbles[action]

    custom_bubbles = [
        f"{emo_icon} Amo {fav_short}!",
        f"{emo_icon} {char_name}: {dom_emo}!",
        f"💬 Clica 2x pra conversar comigo!",
        f"💧 {char_name}: Já bebeu água hoje?",
    ] + LUNA_DESKTOP_BUBBLES
    return random.choice(custom_bubbles)


def generate_social_encounter_plan(
    name_left: str,
    p_left: Dict[str, Any],
    name_right: str,
    p_right: Dict[str, Any],
    forced_action: Optional[str] = None,
) -> Dict[str, str]:
    """
    Planeja uma interação social animada entre dois avatares que se encontraram
    na área de trabalho, escolhendo a animação e as falas com base nos gostos
    e emoções individuais de cada um!
    """
    likes_l = p_left.get("likes") or ["☕ Café Expresso Quentinho"]
    likes_r = p_right.get("likes") or ["🍰 Bolo, Doces & Confeitaria"]
    traits_l = " ".join(p_left.get("traits", []) + p_left.get("emotions", [])).lower()
    traits_r = " ".join(p_right.get("traits", []) + p_right.get("emotions", [])).lower()
    dom_l = p_left.get("dominant_emotion", "😊").split(" ")[0]
    dom_r = p_right.get("dominant_emotion", "😊").split(" ")[0]

    fav_l = random.choice(likes_l)
    fav_r = random.choice(likes_r)
    short_l = fav_l[:22]
    short_r = fav_r[:22]

    if forced_action:
        chosen_act = forced_action
    else:
        # Escolher animação ponderada pela personalidade dos dois avatares
        candidates = ["social_chat_laugh", "social_high_five"]
        if any("café" in x.lower() for x in likes_l + likes_r):
            candidates.extend(["social_coffee_toast", "social_coffee_toast"])
        if "bravinh" in traits_l or "bravinh" in traits_r or "irônic" in traits_l or "irônic" in traits_r:
            candidates.extend(["social_playful_tease", "social_playful_tease"])
        if any("música" in x.lower() or "jogos" in x.lower() for x in likes_l + likes_r):
            candidates.append("social_dance_party")
        if "carinhos" in traits_l or "carinhos" in traits_r or any("bolo" in x.lower() or "planta" in x.lower() for x in likes_l + likes_r):
            candidates.append("social_gift_exchange")
        chosen_act = random.choice(candidates)

    if chosen_act == "social_coffee_toast":
        line_left = f"☕ Ei {name_right}! Bora um brinde de Café Expresso?"
        react_right_1 = f"{dom_r} Opa, café?! Bora! ☕✨"
        line_right = f"☕ Saúde, {name_left}! Combina demais com {short_r}!"
        react_left_2 = f"{dom_l} Energia em 100%! 🚀☕"
    elif chosen_act == "social_high_five":
        line_left = f"🙌 Aê {name_right}! Toca aqui, dupla imbatível!"
        react_right_1 = f"🙌✨ Toma esse High-Five!"
        line_right = f"{dom_r} Boa, {name_left}! Hoje o dia tá rendendo!"
        react_left_2 = f"🤜🤛 Parceria nota 10!"
    elif chosen_act == "social_gift_exchange":
        line_left = f"🎁 {name_right}, trouxe uma lembrancinha do Vale pra você!"
        react_right_1 = f"😮❗ Pra mim?!"
        line_right = f"🥰 Awn, obrigado(a) {name_left}! Amo quase tanto quanto {short_r}!"
        react_left_2 = f"❤️✨ Você merece!"
    elif chosen_act == "social_dance_party":
        line_left = f"🎶 Ei {name_right}, solta o som na barra de tarefas!"
        react_right_1 = f"💃🎶 Opa, meu passo favorito!"
        line_right = f"🤩 Curtindo {short_r} nessa dancinha com você, {name_left}!"
        react_left_2 = f"🎉✨ Que sintonia!"
    elif chosen_act == "social_playful_tease":
        line_left = f"😤 Ei {name_right}, tá passeando ou trabalhando?!"
        react_right_1 = f"😂🎵 Olha quem fala!"
        line_right = f"😏 Relaxa, {name_left}! Trouxe {short_r} pra fazer as pazes!"
        react_left_2 = f"💛 Та bom, tá perdoado(a)!"
    else:  # social_chat_laugh
        line_left = f"💬 Oi {name_right}! Já curtiu {short_l} hoje?"
        react_right_1 = f"👀💬 Conta mais!"
        line_right = f"{dom_r} Com certeza, {name_left}! E depois tem {short_r}!"
        react_left_2 = f"😄✨ Papo bom demais!"

    return {
        "action": chosen_act,
        "line_left": line_left,
        "react_right_1": react_right_1,
        "line_right": line_right,
        "react_left_2": react_left_2,
    }


# ==============================================================================
# FORMULÁRIO MODAL DE MÚLTIPLA ESCOLHA DE PERSONALIDADE POR AVATAR
# ==============================================================================

def open_avatar_personality_modal(
    parent: tk.Misc,
    record: Any = None,
    all_records: Optional[List[Any]] = None,
    on_saved_callback: Optional[Callable[[Any, Dict[str, Any]], None]] = None,
):
    """
    Abre o Formulário de Múltipla Escolha para personalizar a personalidade individual
    de cada avatar com seus gostos, desgostos, traços e emoções característicos.
    Permite alternar entre qualquer avatar da biblioteca ou editar o avatar atual.
    """
    records_list = list(all_records) if all_records else ([record] if record else [])
    if not records_list and record is not None:
        records_list = [record]

    win = tk.Toplevel(parent)
    win.title("🎭 Formulário de Múltipla Escolha — Personalidade, Gostos & Emoções do Avatar")
    win.geometry("880x760")
    win.minsize(820, 680)
    win.configure(bg="#5A2E14")
    win.wm_attributes("-topmost", True)

    # Cabeçalho superior
    header = tk.Frame(win, bg="#8C4A20", bd=3, relief="ridge", padx=14, pady=10)
    header.pack(fill="x", padx=10, pady=(10, 6))

    tk.Label(
        header,
        text="🎭 Personalizar Personalidade Individual do Avatar (Múltipla Escolha)",
        font=("Segoe UI", 13, "bold"),
        bg="#8C4A20",
        fg="#FFF6E0",
    ).pack(anchor="w")

    tk.Label(
        header,
        text=(
            "Marque os traços de personalidade, gostos favoritos, desgostos e reações emocionais características "
            "deste avatar. Cada personagem guarda suas próprias escolhas individualmente!"
        ),
        font=("Segoe UI", 9),
        bg="#8C4A20",
        fg="#FCE8C5",
        justify="left",
    ).pack(anchor="w", pady=(2, 0))

    # Barra seletora de Avatar + Botões de Preset/Sorteio
    selector_bar = tk.Frame(win, bg="#EAD09E", bd=2, relief="groove", padx=12, pady=8)
    selector_bar.pack(fill="x", padx=10, pady=(0, 6))

    tk.Label(
        selector_bar,
        text="👤 Avatar Selecionado:",
        font=("Segoe UI", 10, "bold"),
        bg="#EAD09E",
        fg="#3A1E08",
    ).pack(side="left")

    avatar_names = [f"{r.config.name} ({r.avatar_id})" for r in records_list] if records_list else ["Avatar Atual"]
    current_idx = 0
    if record and records_list:
        for idx, r in enumerate(records_list):
            if r.avatar_id == record.avatar_id:
                current_idx = idx
                break

    selected_avatar_var = tk.StringVar(value=avatar_names[current_idx] if avatar_names else "")
    avatar_combo = ttk.Combobox(
        selector_bar,
        textvariable=selected_avatar_var,
        values=avatar_names,
        state="readonly" if len(records_list) > 1 else "disabled",
        width=30,
        font=("Segoe UI", 10, "bold"),
    )
    avatar_combo.pack(side="left", padx=8)

    # Variáveis do formulário
    archetype_var = tk.StringVar(value=PERSONALITY_ARCHETYPES[0])
    dom_emotion_var = tk.StringVar(value=DOMINANT_EMOTIONS[0])
    catchphrase_var = tk.StringVar(value="")

    traits_vars: Dict[str, tk.BooleanVar] = {opt: tk.BooleanVar(value=False) for opt in PERSONALITY_TRAITS_CHOICES}
    likes_vars: Dict[str, tk.BooleanVar] = {opt: tk.BooleanVar(value=False) for opt in PERSONALITY_LIKES_CHOICES}
    dislikes_vars: Dict[str, tk.BooleanVar] = {opt: tk.BooleanVar(value=False) for opt in PERSONALITY_DISLIKES_CHOICES}
    emotions_vars: Dict[str, tk.BooleanVar] = {opt: tk.BooleanVar(value=False) for opt in PERSONALITY_EMOTIONS_CHOICES}

    def _get_current_record():
        if not records_list:
            return record
        sel = selected_avatar_var.get()
        for r in records_list:
            if f"{r.config.name} ({r.avatar_id})" == sel:
                return r
        return records_list[0]

    def _populate_form_from_dict(p_data: Dict[str, Any]):
        archetype_var.set(p_data.get("archetype", PERSONALITY_ARCHETYPES[0]))
        dom_emotion_var.set(p_data.get("dominant_emotion", DOMINANT_EMOTIONS[0]))
        catchphrase_var.set(p_data.get("catchphrase", ""))

        sel_traits = set(p_data.get("traits", []))
        for k, v in traits_vars.items():
            v.set(k in sel_traits)

        sel_likes = set(p_data.get("likes", []))
        for k, v in likes_vars.items():
            v.set(k in sel_likes)

        sel_dislikes = set(p_data.get("dislikes", []))
        for k, v in dislikes_vars.items():
            v.set(k in sel_dislikes)

        sel_emotions = set(p_data.get("emotions", []))
        for k, v in emotions_vars.items():
            v.set(k in sel_emotions)

    def _collect_form_dict() -> Dict[str, Any]:
        sel_traits = [k for k, v in traits_vars.items() if v.get()]
        sel_likes = [k for k, v in likes_vars.items() if v.get()]
        sel_dislikes = [k for k, v in dislikes_vars.items() if v.get()]
        sel_emotions = [k for k, v in emotions_vars.items() if v.get()]

        # Garantir pelo menos 1 escolha em cada categoria caso o usuário desmarque tudo
        if not sel_traits:
            sel_traits = [PERSONALITY_TRAITS_CHOICES[0]]
        if not sel_likes:
            sel_likes = [PERSONALITY_LIKES_CHOICES[0]]
        if not sel_dislikes:
            sel_dislikes = [PERSONALITY_DISLIKES_CHOICES[0]]
        if not sel_emotions:
            sel_emotions = [PERSONALITY_EMOTIONS_CHOICES[0]]

        return {
            "archetype": archetype_var.get(),
            "dominant_emotion": dom_emotion_var.get(),
            "traits": sel_traits,
            "likes": sel_likes,
            "dislikes": sel_dislikes,
            "emotions": sel_emotions,
            "catchphrase": catchphrase_var.get().strip(),
        }

    def _load_selected_avatar_personality(*_):
        rec = _get_current_record()
        if rec:
            p = load_avatar_personality(rec.folder_path, rec.config.name, rec.avatar_id)
        else:
            p = get_default_avatar_personality("Avatar")
        _populate_form_from_dict(p)

    def _restore_avatar_characteristic_defaults():
        rec = _get_current_record()
        name = rec.config.name if rec else "Avatar"
        aid = rec.avatar_id if rec else ""
        p = get_default_avatar_personality(name, aid)
        _populate_form_from_dict(p)

    def _randomize_choices():
        rec = _get_current_record()
        name = rec.config.name if rec else "Avatar"
        p = {
            "archetype": random.choice(PERSONALITY_ARCHETYPES),
            "dominant_emotion": random.choice(DOMINANT_EMOTIONS),
            "traits": random.sample(PERSONALITY_TRAITS_CHOICES, k=random.randint(3, 5)),
            "likes": random.sample(PERSONALITY_LIKES_CHOICES, k=random.randint(4, 6)),
            "dislikes": random.sample(PERSONALITY_DISLIKES_CHOICES, k=random.randint(2, 3)),
            "emotions": random.sample(PERSONALITY_EMOTIONS_CHOICES, k=random.randint(3, 4)),
            "catchphrase": f"Aqui é {name} curtindo o Vale do meu jeitinho único!",
        }
        _populate_form_from_dict(p)

    avatar_combo.bind("<<ComboboxSelected>>", _load_selected_avatar_personality)

    tk.Button(
        selector_bar,
        text="🎲 Sortear Gostos & Emoções",
        command=_randomize_choices,
        bg="#D9822B",
        fg="white",
        font=("Segoe UI", 9, "bold"),
        padx=10,
        pady=3,
        cursor="hand2",
    ).pack(side="right", padx=(6, 0))

    tk.Button(
        selector_bar,
        text="🔄 Padrão Característico do Avatar",
        command=_restore_avatar_characteristic_defaults,
        bg="#3B659C",
        fg="white",
        font=("Segoe UI", 9, "bold"),
        padx=10,
        pady=3,
        cursor="hand2",
    ).pack(side="right")

    # Área rolável para as seções de múltipla escolha
    scroll_outer = tk.Frame(win, bg="#F7E2B8", bd=3, relief="sunken")
    scroll_outer.pack(fill="both", expand=True, padx=10, pady=(0, 6))

    canvas = tk.Canvas(scroll_outer, bg="#F7E2B8", highlightthickness=0)
    scrollbar = ttk.Scrollbar(scroll_outer, orient="vertical", command=canvas.yview)
    form_inner = tk.Frame(canvas, bg="#F7E2B8", padx=14, pady=10)

    form_inner.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
    )
    win_id = canvas.create_window((0, 0), window=form_inner, anchor="nw")
    canvas.bind(
        "<Configure>",
        lambda e: canvas.itemconfigure(win_id, width=e.width),
    )
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # SEÇÃO 1: Arquétipo & Emoção Dominante
    sec1 = tk.LabelFrame(
        form_inner,
        text=" 🌟 1. Estilo Principal (Arquétipo) & Emoção Característica Dominante ",
        font=("Segoe UI", 10, "bold"),
        bg="#FFF3D6",
        fg="#3A1E08",
        padx=10,
        pady=8,
    )
    sec1.pack(fill="x", pady=(0, 8))
    sec1.columnconfigure(1, weight=1)
    sec1.columnconfigure(3, weight=1)

    tk.Label(sec1, text="Temperamento Base:", font=("Segoe UI", 9, "bold"), bg="#FFF3D6", fg="#3A1E08").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=4)
    ttk.Combobox(sec1, textvariable=archetype_var, values=PERSONALITY_ARCHETYPES, state="readonly", font=("Segoe UI", 9)).grid(row=0, column=1, sticky="ew", padx=(0, 14), pady=4)

    tk.Label(sec1, text="Emoção Característica:", font=("Segoe UI", 9, "bold"), bg="#FFF3D6", fg="#3A1E08").grid(row=0, column=2, sticky="w", padx=(0, 6), pady=4)
    ttk.Combobox(sec1, textvariable=dom_emotion_var, values=DOMINANT_EMOTIONS, state="readonly", font=("Segoe UI", 9)).grid(row=0, column=3, sticky="ew", pady=4)

    # SEÇÃO 2: Traços de Personalidade (Múltipla Escolha)
    sec2 = tk.LabelFrame(
        form_inner,
        text=" 🎭 2. Traços de Personalidade (Múltipla Escolha — Marque quantos quiser) ",
        font=("Segoe UI", 10, "bold"),
        bg="#FFF3D6",
        fg="#3A1E08",
        padx=10,
        pady=8,
    )
    sec2.pack(fill="x", pady=(0, 8))
    for c in range(3):
        sec2.columnconfigure(c, weight=1)

    for idx, opt in enumerate(PERSONALITY_TRAITS_CHOICES):
        r, c = divmod(idx, 3)
        tk.Checkbutton(
            sec2,
            text=opt,
            variable=traits_vars[opt],
            bg="#FFF3D6",
            fg="#3A1E08",
            selectcolor="#FFFDF7",
            activebackground="#FFF3D6",
            font=("Segoe UI", 9),
            anchor="w",
        ).grid(row=r, column=c, sticky="w", padx=4, pady=2)

    # SEÇÃO 3: Gostos & Paixões Favoritas (Múltipla Escolha)
    sec3 = tk.LabelFrame(
        form_inner,
        text=" ❤️ 3. Gostos & Paixões Característicos (O que este avatar mais ama) ",
        font=("Segoe UI", 10, "bold"),
        bg="#FFF3D6",
        fg="#3A1E08",
        padx=10,
        pady=8,
    )
    sec3.pack(fill="x", pady=(0, 8))
    for c in range(2):
        sec3.columnconfigure(c, weight=1)

    for idx, opt in enumerate(PERSONALITY_LIKES_CHOICES):
        r, c = divmod(idx, 2)
        tk.Checkbutton(
            sec3,
            text=opt,
            variable=likes_vars[opt],
            bg="#FFF3D6",
            fg="#3A1E08",
            selectcolor="#FFFDF7",
            activebackground="#FFF3D6",
            font=("Segoe UI", 9),
            anchor="w",
        ).grid(row=r, column=c, sticky="w", padx=6, pady=2)

    # SEÇÃO 4: Emoções e Reações Características (Múltipla Escolha)
    sec4 = tk.LabelFrame(
        form_inner,
        text=" ⚡ 4. Emoções & Reações Características (Como o avatar reage com você) ",
        font=("Segoe UI", 10, "bold"),
        bg="#FFF3D6",
        fg="#3A1E08",
        padx=10,
        pady=8,
    )
    sec4.pack(fill="x", pady=(0, 8))
    for c in range(2):
        sec4.columnconfigure(c, weight=1)

    for idx, opt in enumerate(PERSONALITY_EMOTIONS_CHOICES):
        r, c = divmod(idx, 2)
        tk.Checkbutton(
            sec4,
            text=opt,
            variable=emotions_vars[opt],
            bg="#FFF3D6",
            fg="#3A1E08",
            selectcolor="#FFFDF7",
            activebackground="#FFF3D6",
            font=("Segoe UI", 9),
            anchor="w",
        ).grid(row=r, column=c, sticky="w", padx=6, pady=2)

    # SEÇÃO 5: Desgostos / O que irrita ou dá preguiça (Múltipla Escolha)
    sec5 = tk.LabelFrame(
        form_inner,
        text=" 😤 5. Desgostos & Irritações Características (O que dá preguiça ou irrita o avatar) ",
        font=("Segoe UI", 10, "bold"),
        bg="#FFF3D6",
        fg="#3A1E08",
        padx=10,
        pady=8,
    )
    sec5.pack(fill="x", pady=(0, 8))
    for c in range(2):
        sec5.columnconfigure(c, weight=1)

    for idx, opt in enumerate(PERSONALITY_DISLIKES_CHOICES):
        r, c = divmod(idx, 2)
        tk.Checkbutton(
            sec5,
            text=opt,
            variable=dislikes_vars[opt],
            bg="#FFF3D6",
            fg="#3A1E08",
            selectcolor="#FFFDF7",
            activebackground="#FFF3D6",
            font=("Segoe UI", 9),
            anchor="w",
        ).grid(row=r, column=c, sticky="w", padx=6, pady=2)

    # SEÇÃO 6: Bordão / Frase Característica e Prévia ao Vivo
    sec6 = tk.LabelFrame(
        form_inner,
        text=" 💬 6. Bordão / Frase Característica Individual & Teste de Fala ",
        font=("Segoe UI", 10, "bold"),
        bg="#FFF3D6",
        fg="#3A1E08",
        padx=10,
        pady=8,
    )
    sec6.pack(fill="x", pady=(0, 4))

    tk.Label(
        sec6,
        text="Bordão ou nota especial deste avatar (opcional):",
        font=("Segoe UI", 9, "bold"),
        bg="#FFF3D6",
        fg="#3A1E08",
    ).pack(anchor="w")

    tk.Entry(
        sec6,
        textvariable=catchphrase_var,
        font=("Segoe UI", 10),
        bg="#FFFDF8",
        fg="#3A1E08",
    ).pack(fill="x", pady=(2, 6))

    preview_lbl = tk.Label(
        sec6,
        text="Clique em '🧪 Testar Fala com essa Personalidade' abaixo para ver o avatar reagindo com suas escolhas!",
        font=("Georgia", 10, "italic"),
        bg="#FFF8E8",
        fg="#4A2566",
        wraplength=760,
        justify="left",
        anchor="w",
        padx=8,
        pady=6,
        bd=1,
        relief="solid",
    )
    preview_lbl.pack(fill="x")

    # Rodapé de botões
    footer = tk.Frame(win, bg="#5A2E14", padx=10, pady=8)
    footer.pack(fill="x")

    def _on_test_personality():
        rec = _get_current_record()
        c_name = rec.config.name if rec else "Avatar"
        p_dict = _collect_form_dict()
        sample_reply = _generate_local_luna_fallback(
            char_name=c_name,
            hearts=9,
            user_msg="Me conta sobre sua personalidade, seus gostos e emoções!",
            personality=p_dict,
        )
        preview_lbl.configure(text=sample_reply)

    def _on_save_personality():
        rec = _get_current_record()
        p_dict = _collect_form_dict()
        if rec:
            save_avatar_personality(rec.folder_path, rec.config.name, p_dict)
            if on_saved_callback:
                on_saved_callback(rec, p_dict)
            messagebox.showinfo(
                "Personalidade Individual Salva! 🎭✨",
                f"A personalidade de '{rec.config.name}' foi atualizada com sucesso!\n\n"
                f"• Arquétipo: {p_dict['archetype']}\n"
                f"• Emoção Dominante: {p_dict['dominant_emotion']}\n"
                f"• {len(p_dict['traits'])} traços, {len(p_dict['likes'])} gostos e {len(p_dict['emotions'])} emoções ativas!",
                parent=win,
            )
        else:
            if on_saved_callback:
                on_saved_callback(None, p_dict)
            messagebox.showinfo(
                "Personalidade Configurada! 🎭",
                "Escolhas aplicadas ao avatar atual no editor!",
                parent=win,
            )
        win.destroy()

    tk.Button(
        footer,
        text="🧪 Testar Fala com essa Personalidade",
        command=_on_test_personality,
        bg="#6C3B8C",
        fg="white",
        font=("Segoe UI", 9, "bold"),
        padx=12,
        pady=5,
        cursor="hand2",
    ).pack(side="left")

    tk.Button(
        footer,
        text="💾 Salvar Personalidade deste Avatar",
        command=_on_save_personality,
        bg="#3E8E4C",
        fg="white",
        font=("Segoe UI", 10, "bold"),
        padx=18,
        pady=5,
        cursor="hand2",
    ).pack(side="right")

    tk.Button(
        footer,
        text="Cancelar",
        command=win.destroy,
        bg="#8C4A20",
        fg="white",
        font=("Segoe UI", 9, "bold"),
        padx=12,
        pady=5,
        cursor="hand2",
    ).pack(side="right", padx=(0, 8))

    _load_selected_avatar_personality()


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
