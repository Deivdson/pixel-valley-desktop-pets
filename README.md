# 🌾 Pixel Valley Desktop Pets

Aplicativo de **Desktop Pets interativos em Pixel Art 16-bit** para Windows, com suporte a importação e animação automática de folhas de sprites `4x6` geradas por IA (ex: Gemini), customizador procedural em camadas e **Caixas de Diálogo Interativas** com sistema de amizade, presentes e chat.

---

## ✨ Funcionalidades

- **Importador Automático de Folhas 4x6**: Recorta, remove o fundo de cada célula e monta automaticamente 8 animações completas (`idle`, `walk_right`, `walk_left`, `water_crops`, `coffee_break`, `fishing`, `happy_dance`, `sleep_sit`).
- **Gerador Procedural 100% Autoral**: Desenha personagens Chibi `16x32` diretamente via código Python/Pillow sem depender de arquivos proprietários externos.
- **Caixas de Diálogo Interativas**:
  - Dê **duplo clique** em qualquer personagem na área de trabalho (ou clique em `💬 Interagir / Diálogo`) para abrir a caixa de conversa;
  - Retrato em Pixel Art em alta definição (`184x184`), contador de **Corações de Amizade (❤️ 0–10)**, entrega de presentes e chat livre (local ou integrado com Gemini/Ollama).
- **Física na Área de Trabalho**: Os personagens caminham sobre a Barra de Tarefas do Windows, executam ações autônomas, podem ser arrastados com o mouse e respondem a cliques.
- **Atualização Automática (`🔄 Atualizar Programa`)**: Sincroniza com o Git, reprocessa folhas de sprites e recarrega os pets em tempo real.

---

## 🚀 Como Executar

No Windows, dê duplo clique em **`Executar_Stardew_Pets.bat`** ou execute no terminal:

```bash
python app.py
```

---

## ⚖️ Aviso Legal / Direitos Autorais (Fan Project Disclaimer)

Este é um **projeto de código aberto e independente feito por fã**, apenas para fins educacionais e de entretenimento pessoal.
- **Não oficial**: Este software **não é afiliado, endossado, patrocinado nem associado** à *ConcernedApe LLC* ou ao jogo *Stardew Valley*.
- **Zero Assets Proprietários**: Todo o código-fonte, interface gráfica, ícones, ferramentas e o gerador procedural de sprites incluídos neste repositório são 100% originais/autorais e não redistribuem nenhum arquivo gráfico extraído do jogo original.
