<div align="center">

# 🎭 Narrative Flow Checker

### Validador de diálogos para jogos narrativos (RPGs de escolha / Visual Novels)

<img src="assets/banner-anime.gif" width="700" alt="Banner anime" />

<br>

![Python](https://img.shields.io/badge/Python-3.14-blue?style=for-the-badge&logo=python)
![PySide6](https://img.shields.io/badge/PySide6-GUI-00C853?style=for-the-badge)
![Status](https://img.shields.io/badge/status-V1%20funcional-success?style=for-the-badge)

</div>

---

## ✨ Sobre o projeto

Brincando com Python e tentando entender o que tô fazendo da vida, criei um programa que valida os diálogos de um jogo narrativo, focado para RPGs de múltipla escolha com muitos diálogos e também visual novels.

Ele funciona durante o desenvolvimento para ajudar a encontrar erros antes de virar bug no jogo.

Basicamente, ele lê um arquivo `.json` com a estrutura dos diálogos e confere se está tudo consistente.

---

## 🧠 O que ele verifica

- Se o ponto inicial do diálogo existe (`start`)
- Se uma escolha leva para um destino válido
- Se alguma parte do diálogo ficou inacessível
- Se uma condição foi exigida (`requires`) mas nunca ativada (`set_flags`)
- Se o fluxo geral está coerente

> Quando dá problema, ele mostra **o que deu erro**, **onde foi** (`Path`) e **em que linha** do JSON (quando possível).

---

## 📌 Explicando rapidinho: o que é “nó”?

Se você ver a palavra **nó** no projeto, pensa assim:

👉 **Nó = um bloco de diálogo / uma cena pequena**  
É tipo um “ponto” da conversa.

Exemplo:
- um personagem fala algo
- aparecem escolhas
- cada escolha leva pra outro trecho

Então a história vai “pulando” de nó em nó.

---

## 🖼️ Interface

### Tela principal
<img src="https://imgur.com/a/opQhNZp" width="800" alt="Interface do validador" />

### Exemplo de erro apontando Path + Linha
<img src="https://imgur.com/a/yAeOXVF" width="800" alt="Relatório com erro" />

---

## 🚀 Tecnologias

- **Python 3**
- **PySide6** (interface gráfica)
- **JSON** (estrutura dos diálogos)

---
