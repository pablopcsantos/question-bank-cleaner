# Question Bank Cleaner

Aplicação desktop utilitária para **análise e deduplicação assistida de bancos de questões** armazenados em JavaScript/JSON.

O projeto nasceu a partir de um script de linha de comando e foi reorganizado para oferecer uma **interface gráfica (GUI)** voltada também a pessoas sem familiaridade com terminal. O motor original de comparação foi preservado, incluindo remoção automática de duplicatas de alta confiança, identificação de casos ambíguos, relatórios de auditoria e revisão humana antes da aplicação de decisões.

A versão gráfica utiliza **Tkinter** e pode ser empacotada como um executável portátil para Windows com **PyInstaller**.

## Relação com o projeto TEP Quiz

O **Question Bank Cleaner** foi desenvolvido, entre outros objetivos, para auxiliar os usuários e mantenedores do projeto [TEP Quiz](https://github.com/pablopcsantos/tep-quiz) na organização dos bancos de questões que estejam utilizando ou criando. A ferramenta facilita a identificação de questões repetidas, a revisão de casos semelhantes e a geração de um banco mais organizado antes de sua utilização no Quiz. Apesar dessa origem prática, o programa não depende do TEP Quiz e pode ser utilizado com outros bancos de questões compatíveis com a estrutura JavaScript/JSON esperada.

---

## Principais recursos

- seleção visual do arquivo de entrada;
- escolha da pasta de saída;
- remoção automática de questões integralmente idênticas;
- detecção de duplicatas de alta confiança;
- identificação de grupos com forte similaridade;
- identificação de possíveis duplicatas para revisão;
- interface gráfica para comparar questões lado a lado;
- decisão visual entre:
  - duplicada;
  - não duplicada;
  - revisar depois, quando aplicável;
- escolha da ocorrência que deve ser preservada;
- geração de banco limpo em JavaScript;
- relatórios textuais de auditoria;
- exportação das decisões humanas aplicadas;
- painel de log e progresso;
- abertura da pasta de saída diretamente pela GUI;
- compatibilidade com o modo de linha de comando original;
- build portátil para Windows em um único `.exe`.

---

## Tutorial de uso

Esta seção apresenta o fluxo recomendado para quem deseja usar o programa sem precisar trabalhar diretamente com comandos de terminal.

> **Antes de começar:** mantenha sempre uma cópia de segurança do banco original. O Question Bank Cleaner gera um novo banco de saída e não foi projetado para substituir silenciosamente o único exemplar do arquivo-fonte.

### 1. Abrir o programa

Se estiver usando a versão portátil para Windows, abra:

```text
QuestionBankCleaner.exe
```

Não é necessário instalar Python para utilizar o executável portátil.

Se estiver executando o projeto a partir do código-fonte, use:

```bash
python app.py
```

A tela principal será aberta em **modo escuro**, que é o tema padrão do programa.

Caso prefira o modo claro, abra:

```text
Configurações → Aparência → Modo claro
```

A preferência visual é salva e reaplicada nas próximas execuções.

### 2. Selecionar o banco de questões

Na seção **1 · Banco de entrada**:

1. clique em **Selecionar arquivo**;
2. localize o banco que deseja analisar;
3. selecione o arquivo;
4. confirme a escolha.

O programa aceita arquivos com extensão `.js` e `.json`, desde que contenham uma lista de questões em formato JSON compatível.

Exemplo de estrutura aceita:

```javascript
const bancoDeQuestoes = [
    {
        "bloco": "Bloco 1",
        "grandeArea": "Pediatria",
        "temas": ["Pneumologia"],
        "tipo": "objetiva",
        "pergunta": "Qual é a alternativa correta?",
        "opcoes": [
            "Alternativa A",
            "Alternativa B",
            "Alternativa C",
            "Alternativa D"
        ],
        "gabarito": "Opção A",
        "informacoesComplementares": "Comentário opcional."
    }
];
```

O arquivo selecionado **não é alterado diretamente**.

### 3. Escolher a pasta de saída

Na seção **2 · Pasta de saída**:

1. clique em **Selecionar pasta**;
2. escolha onde deseja armazenar o banco limpo e os relatórios;
3. confirme.

Se você selecionar primeiro o banco de entrada, o programa sugere automaticamente uma pasta chamada:

```text
saida_question_bank_cleaner
```

na mesma pasta do arquivo original.

Você pode manter essa sugestão ou escolher outro local.

### 4. Analisar o banco

Clique em:

```text
▶ Analisar banco
```

O programa executará automaticamente as etapas iniciais:

1. leitura do banco;
2. remoção de duplicatas integralmente idênticas;
3. procura de duplicatas de alta confiança;
4. busca de grupos de forte similaridade;
5. busca de possíveis duplicatas que merecem revisão humana;
6. geração inicial dos relatórios.

Durante o processamento, acompanhe a seção **Progresso e mensagens**.

Em bancos maiores, essa etapa pode levar algum tempo. O uso do **RapidFuzz** torna a análise mais rápida; quando ele não estiver disponível, o programa possui um modo alternativo mais lento.

### 5. Conferir o resumo da análise

Quando a análise terminar, o programa exibirá uma janela com informações como:

- número de questões originais;
- quantidade removida automaticamente;
- número de grupos fortes encontrados.

Nesse momento, o banco automático já terá sido gerado, mas ainda é recomendável revisar os casos ambíguos antes de considerar o processo concluído.

### 6. Revisar grupos de forte similaridade

Clique em:

```text
Revisar grupos fortes
```

Essa janela apresenta conjuntos de questões com semelhança elevada.

Para cada grupo, você poderá decidir entre:

**Não são duplicadas**  
Use quando as questões são parecidas, mas representam itens diferentes e devem permanecer no banco.

**São duplicadas**  
Use quando as questões representam efetivamente uma repetição.

Quando selecionar **São duplicadas**, escolha no campo **Manter** qual ocorrência deverá permanecer no banco: A, B, C etc.

O programa mostra informações como:

- área;
- temas;
- tipo;
- enunciado;
- alternativas;
- gabarito;
- informações complementares.

Leia as questões antes de registrar uma remoção.

Por segurança, novos grupos de forte similaridade começam como:

```text
Não são duplicadas
```

Assim, nenhuma remoção humana ocorre apenas porque um item foi classificado como semelhante.

### 7. Revisar possíveis duplicatas

Clique em:

```text
Revisar possíveis duplicatas
```

Essa janela apresenta pares cuja semelhança justifica uma inspeção manual, mas que não possuem segurança suficiente para remoção automática.

As opções são:

**Revisar depois**  
Nenhuma das questões é removida. É o estado inicial.

**Não são duplicadas**  
As duas questões são preservadas.

**São duplicadas**  
Escolha se deseja manter a questão **A** ou a questão **B**.

A janela também apresenta indicadores de similaridade, incluindo:

- similaridade geral;
- enunciado;
- alternativas;
- gabarito.

Depois de escolher a decisão, clique em:

```text
Salvar decisão
```

Uma pequena janela confirmará que a decisão foi salva.

Se existir apenas uma revisão nessa lista, clicar em **Anterior** ou **Próxima** exibirá uma mensagem informando que há somente uma revisão disponível.

Você pode deixar um item como **Revisar depois** e continuar o processo; nesse caso, ele não será removido.

### 8. Aplicar as decisões

Depois de revisar os itens desejados, clique em:

```text
✓ Aplicar decisões e gerar banco final
```

O programa solicitará uma confirmação.

Ao continuar, serão combinadas:

- as remoções automáticas de alta confiança;
- as decisões registradas nos grupos fortes;
- as decisões registradas nas possíveis duplicatas.

Itens ainda definidos como **Revisar depois** permanecem no banco.

### 9. Abrir o resultado

Após a conclusão, você pode usar:

```text
Abrir pasta de saída
```

para visualizar todos os arquivos produzidos, ou:

```text
Abrir banco gerado
```

para abrir diretamente:

```text
banco_questoes_limpo.js
```

Esse é o arquivo que contém o banco resultante.

### 10. Entender os arquivos gerados

A pasta de saída pode conter:

```text
banco_questoes_limpo.js
questoes_removidas.txt
questoes_conflitantes.txt
questoes_conflitantes_resolvidas.txt
questoes_possiveis_duplicatas.txt
questoes_possiveis_duplicatas_resolvidas.txt
```

Em termos práticos:

- **`banco_questoes_limpo.js`**: banco final;
- **`questoes_removidas.txt`**: registro das questões removidas;
- **`questoes_conflitantes.txt`**: decisões sobre grupos de forte similaridade;
- **`questoes_conflitantes_resolvidas.txt`**: auditoria das decisões efetivamente aplicadas nesses grupos;
- **`questoes_possiveis_duplicatas.txt`**: pares que merecem revisão;
- **`questoes_possiveis_duplicatas_resolvidas.txt`**: auditoria das decisões aplicadas aos pares.

### 11. Fluxo recomendado para uso com o TEP Quiz

Para quem estiver organizando um banco destinado ao [TEP Quiz](https://github.com/pablopcsantos/tep-quiz), um fluxo seguro é:

1. faça uma cópia do banco de questões que está criando ou utilizando;
2. abra a cópia no Question Bank Cleaner;
3. execute a análise automática;
4. revise os grupos fortes;
5. revise as possíveis duplicatas;
6. aplique as decisões;
7. examine `banco_questoes_limpo.js`;
8. somente depois de conferir o resultado, utilize o banco limpo no projeto de Quiz.

O Question Bank Cleaner não envia o banco automaticamente para o TEP Quiz e não modifica o repositório do Quiz. A integração é deliberadamente manual, permitindo que o usuário revise o resultado antes de substituir qualquer arquivo.

### 12. Se algo der errado

**O programa informa que o JSON é inválido**  
Verifique principalmente aspas, vírgulas, colchetes e se o conteúdo entre `[` e `]` realmente forma uma lista JSON válida.

**O processamento parece lento**  
Confirme se a versão utilizada possui RapidFuzz. A versão portátil gerada pelo processo de build do projeto inclui as dependências necessárias.

**Uma questão semelhante não foi detectada**  
Os limiares são heurísticos. Questões semanticamente equivalentes com redações muito diferentes podem não ser identificadas.

**Uma questão foi classificada como semelhante, mas não é duplicada**  
Marque-a como **Não são duplicadas**. O objetivo das janelas de revisão é justamente permitir a decisão humana nos casos ambíguos.

**Tenho dúvida sobre uma remoção automática**  
Consulte `questoes_removidas.txt` e preserve o banco original até conferir o resultado.

---

## Como o processamento funciona

O fluxo é dividido em três níveis.

### 1. Duplicatas integralmente idênticas

O programa cria uma assinatura JSON completa de cada questão.

Quando duas ocorrências são integralmente iguais, a repetida é removida automaticamente.

### 2. Duplicatas de alta confiança

Questões não integralmente idênticas podem ainda ser removidas automaticamente quando os elementos centrais são praticamente equivalentes.

Os critérios atuais exigem simultaneamente:

- similaridade do enunciado ≥ **98%**;
- similaridade das alternativas ≥ **98%**;
- similaridade do gabarito ≥ **98%**.

Diferenças de metadados, como banca, ano, bloco ou grande área, não impedem isoladamente a identificação quando o conteúdo principal é essencialmente equivalente.

A escolha automática da ocorrência preservada prioriza a questão com maior quantidade de informação útil em campos como bloco, temas, tipo, grande área e informações complementares.

### 3. Revisão humana

Casos que não atingem o nível de remoção automática podem ser encaminhados para revisão.

A similaridade geral considera:

| Componente | Peso |
|---|---:|
| Enunciado | 50% |
| Alternativas | 35% |
| Gabarito | 10% |
| Temas | 3% |
| Grande área | 2% |

A classificação utiliza, entre outros, os seguintes limiares:

- **≥ 93%:** forte candidata a duplicata;
- **≥ 84%:** possível duplicata;
- abaixo disso: baixa semelhança.

A interface gráfica mantém a decisão humana separada da remoção automática.

---

## Formato esperado do banco

O arquivo padrão é um JavaScript contendo uma lista de objetos JSON, por exemplo:

```javascript
const bancoDeQuestoes = [
    {
        "bloco": "Bloco 1",
        "grandeArea": "Pediatria",
        "temas": ["Pneumologia"],
        "tipo": "objetiva",
        "pergunta": "Qual é a alternativa correta?",
        "opcoes": [
            "Alternativa A",
            "Alternativa B",
            "Alternativa C",
            "Alternativa D"
        ],
        "gabarito": "Opção A",
        "informacoesComplementares": "Comentário opcional."
    }
];
```

O programa procura a lista delimitada pelo primeiro `[` e pelo último `]` do arquivo e interpreta seu conteúdo com `json.loads`.

Por isso, o conteúdo interno deve seguir **JSON válido**, incluindo:

- chaves e textos com aspas duplas;
- ausência de comentários dentro da lista;
- ausência de vírgulas inválidas;
- cada questão representada por um objeto.

---

## Interface gráfica

Execute:

```bash
python app.py
```

O fluxo recomendado é:

1. clique em **Selecionar arquivo** e escolha o banco;
2. escolha uma pasta de saída;
3. clique em **Analisar banco**;
4. aguarde a limpeza automática e a busca de candidatos;
5. use **Revisar grupos fortes**;
6. use **Revisar possíveis duplicatas**;
7. registre as decisões desejadas;
8. clique em **Aplicar decisões e gerar banco final**;
9. abra a pasta de saída ou o banco gerado diretamente pela interface.

### Aparência

A interface utiliza um desenho mais atual, com painéis, botões planos, maior espaçamento visual e uma paleta própria.

O **modo escuro é o padrão**.

A troca de tema está disponível em:

```text
Configurações → Aparência → Modo escuro / Modo claro
```

A preferência é armazenada no perfil do usuário e reaplicada na próxima execução.

O tema também é propagado para as janelas de revisão abertas.

### Revisão de possíveis duplicatas

Na janela **Revisar possíveis duplicatas**:

- o botão **Salvar decisão** confirma a gravação por meio de uma pequena janela informativa;
- quando existe somente um item para revisão, os botões **Anterior** e **Próxima** informam que há apenas uma revisão disponível;
- itens ainda marcados como **Revisar depois** não são removidos ao aplicar as decisões.

### Comportamento conservador da GUI

Na interface gráfica, novos grupos de forte similaridade começam como **“Não são duplicadas”**.

Isso é intencional: a versão gráfica privilegia uma postura conservadora para evitar remoções humanas acidentais antes de uma revisão explícita.

Possíveis duplicatas começam como **“Revisar depois”**.

---

## Arquivos gerados

Por padrão, a aplicação gera:

```text
banco_questoes_limpo.js
questoes_removidas.txt
questoes_conflitantes.txt
questoes_conflitantes_resolvidas.txt
questoes_possiveis_duplicatas.txt
questoes_possiveis_duplicatas_resolvidas.txt
```

### `banco_questoes_limpo.js`

Banco resultante após:

- remoções automáticas;
- e, quando solicitado, decisões humanas aplicadas.

### `questoes_removidas.txt`

Relatório consolidado das questões efetivamente removidas.

### `questoes_conflitantes.txt`

Arquivo de decisões para grupos de forte similaridade.

A GUI atualiza esse arquivo automaticamente conforme o usuário revisa os grupos.

### `questoes_possiveis_duplicatas.txt`

Pares de questões cuja semelhança justifica revisão, mas que não devem ser removidos automaticamente.

### Arquivos `*_resolvidas.txt`

Registram auditoria das decisões humanas aplicadas.

---

## RapidFuzz

O projeto utiliza `RapidFuzz` quando disponível para acelerar a comparação aproximada de textos.

Instalação:

```bash
pip install -r requirements.txt
```

Se `RapidFuzz` não estiver instalado, o motor mantém um modo de fallback baseado em indexação por tokens e `difflib.SequenceMatcher`.

O fallback é funcional, porém pode ser mais lento.

---

## Versão portátil para Windows

O repositório inclui duas formas de gerar a versão portátil.

### Build local

No Windows, execute:

```text
build_windows.bat
```

O script:

1. cria um ambiente virtual de build;
2. instala as dependências;
3. instala o PyInstaller;
4. gera um executável único e sem console.

O resultado esperado é:

```text
dist\QuestionBankCleaner.exe
```

O executável gerado inclui o interpretador Python e as dependências necessárias, portanto o usuário final **não precisa instalar Python**.

### Build pelo GitHub Actions

O arquivo:

```text
.github/workflows/build-windows.yml
```

gera automaticamente o executável em um runner Windows quando:

- o workflow é iniciado manualmente em **Actions**;
- ou uma tag começando por `v` é enviada ao repositório.

Ao final do workflow, o executável fica disponível como artefato:

```text
QuestionBankCleaner-Windows
```

### Ícone do programa

O projeto já inclui um ícone próprio e os arquivos correspondentes na pasta `assets/`.

O desenho original foi preservado em **SVG quadrado (1:1)** e as versões de uso do programa também foram incluídas:

```text
assets/
├── question_bank_cleaner.ico
├── question_bank_cleaner.svg
├── question_bank_cleaner.png
└── ICON_GUIDE.md
```

O arquivo `.ico` fornecido é multirresolução e contém:

```text
16×16
24×24
32×32
48×48
64×64
128×128
256×256
```

Use 32 bits/RGBA e fundo transparente.

O PNG de fallback foi gerado em **256×256 px**.

O `build_windows.bat` e o workflow do GitHub Actions incorporam automaticamente `question_bank_cleaner.ico` ao executável.

Instruções detalhadas estão em:

```text
assets/ICON_GUIDE.md
```

---

## Estrutura do projeto

```text
Question-Bank-Cleaner-GUI/
├── .github/
│   └── workflows/
│       └── build-windows.yml
├── assets/
│   └── ICON_GUIDE.md
├── exemplo/
│   └── banco_questoes_exemplo.js
├── app.py
├── cleaner_core.py
├── cli.py
├── build_windows.bat
├── requirements.txt
├── requirements-build.txt
├── README.md
└── .gitignore
```

### `app.py`

Ponto de entrada principal da versão gráfica.

Contém:

- GUI;
- fluxo visual de análise;
- revisão estruturada;
- execução em thread para manter a janela responsiva;
- registro de progresso e mensagens;
- integração com o motor de limpeza.

### `cleaner_core.py`

Motor de análise derivado do script original.

Contém:

- normalização;
- comparação de similaridade;
- detecção de duplicatas;
- geração de relatórios;
- leitura e aplicação de decisões;
- modo de linha de comando original.

### `cli.py`

Atalho para utilizar o fluxo tradicional por terminal.

---

## Modo de linha de comando

A versão CLI continua disponível:

```bash
python cli.py --entrada banco_questoes.js
```

Algumas opções herdadas:

```text
--entrada
--saida-js
--saida-txt
--saida-conflitos
--saida-conflitos-resolvidos
--saida-possiveis
--saida-possiveis-resolvidos
--aplicar-conflitos
--aplicar-possiveis
```

Exemplo:

```bash
python cli.py ^
  --entrada banco_questoes.js ^
  --aplicar-conflitos ^
  --aplicar-possiveis
```

---

## Instalação para desenvolvimento

Recomenda-se Python 3.11 ou superior.

Crie um ambiente virtual:

```bash
python -m venv .venv
```

No Windows:

```bash
.venv\Scripts\activate
```

Instale a dependência de execução:

```bash
pip install -r requirements.txt
```

Execute a GUI:

```bash
python app.py
```

Para preparar builds:

```bash
pip install -r requirements-build.txt
```

---

## Segurança operacional

O programa **pode remover questões do banco de saída**.

Algumas recomendações:

- mantenha sempre uma cópia do banco original;
- não sobrescreva o único exemplar do arquivo-fonte;
- revise os relatórios antes de aplicar decisões humanas;
- examine o arquivo final antes de substituir um banco utilizado em produção;
- use controle de versão quando o banco fizer parte de um projeto Git.

A aplicação grava um **novo arquivo de saída** por padrão e não modifica diretamente o arquivo original selecionado.

---

## Limitações

- Similaridade textual não substitui avaliação semântica especializada.
- Questões diferentes podem possuir redação muito parecida.
- Questões equivalentes podem ser redigidas de forma suficientemente diferente para não serem detectadas.
- Os limiares atuais foram definidos como heurísticas do projeto, não como validação científica de um método de deduplicação.
- O programa pressupõe que a lista contida no JavaScript seja JSON válido.
- O desempenho depende do tamanho do banco e da disponibilidade do RapidFuzz.
- A qualidade da revisão final continua dependendo da análise humana dos casos ambíguos.

---

## Compatibilidade

A GUI foi desenvolvida com **Tkinter**, biblioteca gráfica incluída nas distribuições padrão do Python para Windows.

A versão-fonte pode ser utilizada em sistemas com Python compatível.

O executável portátil disponibilizado pelo processo de build do projeto é específico para Windows.

---

## Tecnologias utilizadas

- **Python 3**
- **Tkinter**
- **RapidFuzz** — aceleração opcional de similaridade textual
- **difflib** — fallback de similaridade
- **PyInstaller** — empacotamento da versão portátil
- **GitHub Actions** — automação do build do executável Windows

---

## 👤 Autoria e desenvolvimento

Aplicação desktop utilitária desenvolvida de forma independente por **Pablo Phillipe Cândido dos Santos**, destinada à análise e deduplicação assistida de bancos de questões estruturados em JavaScript/JSON, combinando remoção automática de duplicatas de alta confiança, identificação de casos semelhantes e revisão humana das situações ambíguas.

O desenvolvimento contou com a utilização de ferramentas de inteligência artificial generativa como recurso auxiliar no processo de desenvolvimento, mantendo-se sob responsabilidade do autor a concepção, implementação, integração e verificação do projeto.

Currículo Lattes: [http://lattes.cnpq.br/9500873674712528](http://lattes.cnpq.br/9500873674712528)

---

## Licença

Nenhuma licença de software foi definida nesta versão do projeto.

Antes de publicar ou distribuir o código sob uma licença específica, escolha conscientemente os termos de uso, modificação e redistribuição que deseja conceder.
