# Question Bank Cleaner

*Leia isto em outros idiomas: [Português](README.md)*

---

Desktop utility application for **assisted analysis and deduplication of question banks** stored in JavaScript/JSON.

The project originated from a command-line script and was reorganized to provide a **graphical interface (GUI)** that can also be used by people who are not familiar with terminals. The original comparison engine was preserved, including automatic removal of high-confidence duplicates, identification of ambiguous cases, audit reports, and human review before decisions are applied.

The graphical version uses **Tkinter** and can be packaged as a portable Windows executable with **PyInstaller**.

## Relationship with the TEP Quiz project

**Question Bank Cleaner** was developed, among other goals, to help users and maintainers of the [TEP Quiz](https://github.com/pablopcsantos/tep-quiz) project organize the question banks they use or create. The tool helps identify repeated questions, review similar cases, and generate a cleaner bank before it is used in the Quiz. Despite this practical origin, the program does not depend on TEP Quiz and can be used with other question banks compatible with the expected JavaScript/JSON structure.

---

## Main features

- visual selection of the input file;
- choice of output folder;
- automatic removal of completely identical questions;
- detection of high-confidence duplicates;
- identification of strongly similar groups;
- identification of possible duplicates for review;
- graphical interface for comparing questions side by side;
- visual decisions between:
  - duplicate;
  - not duplicate;
  - review later, when applicable;
- choice of which occurrence should be preserved;
- generation of a cleaned JavaScript question bank;
- textual audit reports;
- export of applied human decisions;
- log and progress panel;
- opening the output folder directly from the GUI;
- compatibility with the original command-line mode;
- portable Windows build as a single `.exe`.

---

## Usage tutorial

This section presents the recommended workflow for users who want to use the program without working directly with terminal commands.

> **Before you begin:** always keep a backup copy of the original bank. Question Bank Cleaner generates a new output bank and was not designed to silently replace the only copy of the source file.

### 1. Open the program

If you are using the portable Windows version, open:

```text
QuestionBankCleaner.exe
```

Python does not need to be installed to use the portable executable.

If you are running the project from source code, use:

```bash
python app.py
```

The main window opens in **dark mode**, which is the program's default theme.

If you prefer light mode, open:

```text
Configurações → Aparência → Modo claro
```

The visual preference is saved and reapplied on subsequent runs.

### 2. Select the question bank

In the **1 · Banco de entrada** section:

1. click **Selecionar arquivo**;
2. locate the bank you want to analyze;
3. select the file;
4. confirm your choice.

The program accepts `.js` and `.json` files as long as they contain a list of questions in a compatible JSON format.

Example of an accepted structure:

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

The selected file **is not modified directly**.

### 3. Choose the output folder

In the **2 · Pasta de saída** section:

1. click **Selecionar pasta**;
2. choose where to store the cleaned bank and reports;
3. confirm.

If you select the input bank first, the program automatically suggests a folder named:

```text
saida_question_bank_cleaner
```

in the same folder as the original file.

You may keep this suggestion or choose another location.

### 4. Analyze the bank

Click:

```text
▶ Analisar banco
```

The program automatically runs the initial stages:

1. reading the bank;
2. removing completely identical duplicates;
3. searching for high-confidence duplicates;
4. searching for strongly similar groups;
5. searching for possible duplicates that deserve human review;
6. generating the initial reports.

During processing, follow the **Progresso e mensagens** section.

For larger banks, this step may take some time. **RapidFuzz** makes the analysis faster; when it is unavailable, the program has a slower fallback mode.

### 5. Check the analysis summary

When analysis finishes, the program displays a window with information such as:

- number of original questions;
- number automatically removed;
- number of strong groups found.

At this point, the automatically cleaned bank has already been generated, but reviewing ambiguous cases is still recommended before considering the process complete.

### 6. Review strongly similar groups

Click:

```text
Revisar grupos fortes
```

This window displays sets of highly similar questions.

For each group, you can choose between:

**Não são duplicadas**  
Use when the questions are similar but represent different items and should remain in the bank.

**São duplicadas**  
Use when the questions effectively represent a repetition.

When selecting **São duplicadas**, choose in the **Manter** field which occurrence should remain in the bank: A, B, C, and so on.

The program displays information such as:

- area;
- topics;
- type;
- prompt;
- alternatives;
- answer key;
- supplementary information.

Read the questions before recording a removal.

For safety, new strongly similar groups start as:

```text
Não são duplicadas
```

This prevents a human-triggered removal from occurring solely because an item was classified as similar.

### 7. Review possible duplicates

Click:

```text
Revisar possíveis duplicatas
```

This window displays pairs whose similarity justifies manual inspection but is not strong enough for automatic removal.

The options are:

**Revisar depois**  
Neither question is removed. This is the initial state.

**Não são duplicadas**  
Both questions are preserved.

**São duplicadas**  
Choose whether to keep question **A** or question **B**.

The window also displays similarity indicators, including:

- overall similarity;
- prompt;
- alternatives;
- answer key.

After choosing a decision, click:

```text
Salvar decisão
```

A small window confirms that the decision was saved.

If there is only one review in the list, clicking **Anterior** or **Próxima** displays a message informing you that only one review is available.

You can leave an item as **Revisar depois** and continue the process; in that case, it will not be removed.

### 8. Apply decisions

After reviewing the desired items, click:

```text
✓ Aplicar decisões e gerar banco final
```

The program asks for confirmation.

When you continue, the following are combined:

- automatic high-confidence removals;
- decisions recorded for strong groups;
- decisions recorded for possible duplicates.

Items still marked as **Revisar depois** remain in the bank.

### 9. Open the result

After completion, you can use:

```text
Abrir pasta de saída
```

to view all generated files, or:

```text
Abrir banco gerado
```

to open directly:

```text
banco_questoes_limpo.js
```

This file contains the resulting bank.

### 10. Understand the generated files

The output folder may contain:

```text
banco_questoes_limpo.js
questoes_removidas.txt
questoes_conflitantes.txt
questoes_conflitantes_resolvidas.txt
questoes_possiveis_duplicatas.txt
questoes_possiveis_duplicatas_resolvidas.txt
```

In practical terms:

- **`banco_questoes_limpo.js`**: final bank;
- **`questoes_removidas.txt`**: record of removed questions;
- **`questoes_conflitantes.txt`**: decisions about strongly similar groups;
- **`questoes_conflitantes_resolvidas.txt`**: audit of decisions effectively applied to those groups;
- **`questoes_possiveis_duplicatas.txt`**: pairs that deserve review;
- **`questoes_possiveis_duplicatas_resolvidas.txt`**: audit of decisions applied to the pairs.

### 11. Recommended workflow for use with TEP Quiz

For users organizing a bank intended for [TEP Quiz](https://github.com/pablopcsantos/tep-quiz), a safe workflow is:

1. make a copy of the question bank you are creating or using;
2. open the copy in Question Bank Cleaner;
3. run the automatic analysis;
4. review strong groups;
5. review possible duplicates;
6. apply the decisions;
7. inspect `banco_questoes_limpo.js`;
8. only after reviewing the result, use the cleaned bank in the Quiz project.

Question Bank Cleaner does not automatically send the bank to TEP Quiz and does not modify the Quiz repository. Integration is deliberately manual so the user can review the result before replacing any file.

### 12. If something goes wrong

**The program says the JSON is invalid**  
Check quotation marks, commas, brackets, and whether the content between `[` and `]` actually forms a valid JSON list.

**Processing seems slow**  
Confirm that the version you are using includes RapidFuzz. The portable version generated by the project's build process includes the required dependencies.

**A similar question was not detected**  
The thresholds are heuristic. Semantically equivalent questions with very different wording may not be identified.

**A question was classified as similar but is not a duplicate**  
Mark it as **Não são duplicadas**. The purpose of the review windows is precisely to allow human decisions in ambiguous cases.

**I am unsure about an automatic removal**  
Check `questoes_removidas.txt` and keep the original bank until you have reviewed the result.

---

## How processing works

The workflow is divided into three levels.

### 1. Completely identical duplicates

The program creates a complete JSON signature for each question.

When two occurrences are completely identical, the repeated one is removed automatically.

### 2. High-confidence duplicates

Questions that are not completely identical may still be removed automatically when their core elements are practically equivalent.

The current criteria simultaneously require:

- prompt similarity ≥ **98%**;
- alternatives similarity ≥ **98%**;
- answer-key similarity ≥ **98%**.

Differences in metadata, such as examining body, year, block, or broad area, do not by themselves prevent identification when the main content is essentially equivalent.

The automatic choice of which occurrence to preserve prioritizes the question containing more useful information in fields such as block, topics, type, broad area, and supplementary information.

### 3. Human review

Cases that do not reach the automatic-removal threshold may be sent for review.

Overall similarity considers:

| Component | Weight |
|---|---:|
| Prompt | 50% |
| Alternatives | 35% |
| Answer key | 10% |
| Topics | 3% |
| Broad area | 2% |

Classification uses, among others, the following thresholds:

- **≥ 93%:** strong duplicate candidate;
- **≥ 84%:** possible duplicate;
- below that: low similarity.

The graphical interface keeps human decisions separate from automatic removal.

---

## Expected bank format

The standard file is JavaScript containing a list of JSON objects, for example:

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

The program looks for the list delimited by the first `[` and the last `]` in the file and interprets its contents with `json.loads`.

Therefore, the internal content must follow **valid JSON**, including:

- keys and strings in double quotes;
- no comments inside the list;
- no invalid commas;
- each question represented by an object.

---

## Graphical interface

Run:

```bash
python app.py
```

The recommended workflow is:

1. click **Selecionar arquivo** and choose the bank;
2. choose an output folder;
3. click **Analisar banco**;
4. wait for automatic cleaning and candidate search;
5. use **Revisar grupos fortes**;
6. use **Revisar possíveis duplicatas**;
7. record the desired decisions;
8. click **Aplicar decisões e gerar banco final**;
9. open the output folder or the generated bank directly from the interface.

### Appearance

The interface uses a more modern design with panels, flat buttons, greater visual spacing, and a custom palette.

**Dark mode is the default**.

Theme switching is available at:

```text
Configurações → Aparência → Modo escuro / Modo claro
```

The preference is stored in the user's profile and reapplied on the next run.

The theme is also propagated to open review windows.

### Reviewing possible duplicates

In the **Revisar possíveis duplicatas** window:

- the **Salvar decisão** button confirms saving through a small informational window;
- when only one item exists for review, the **Anterior** and **Próxima** buttons report that only one review is available;
- items still marked as **Revisar depois** are not removed when decisions are applied.

### Conservative GUI behavior

In the graphical interface, new strongly similar groups begin as **“Não são duplicadas”**.

This is intentional: the graphical version favors a conservative approach to avoid accidental human-triggered removals before explicit review.

Possible duplicates begin as **“Revisar depois”**.

---

## Generated files

By default, the application generates:

```text
banco_questoes_limpo.js
questoes_removidas.txt
questoes_conflitantes.txt
questoes_conflitantes_resolvidas.txt
questoes_possiveis_duplicatas.txt
questoes_possiveis_duplicatas_resolvidas.txt
```

### `banco_questoes_limpo.js`

Resulting bank after:

- automatic removals;
- and, when requested, applied human decisions.

### `questoes_removidas.txt`

Consolidated report of questions effectively removed.

### `questoes_conflitantes.txt`

Decision file for strongly similar groups.

The GUI updates this file automatically as the user reviews the groups.

### `questoes_possiveis_duplicatas.txt`

Pairs of questions whose similarity warrants review but that should not be removed automatically.

### `*_resolvidas.txt` files

Record an audit trail of applied human decisions.

---

## RapidFuzz

The project uses `RapidFuzz` when available to speed up approximate text comparison.

Installation:

```bash
pip install -r requirements.txt
```

If `RapidFuzz` is not installed, the engine retains a fallback mode based on token indexing and `difflib.SequenceMatcher`.

The fallback is functional but may be slower.

---

## Portable Windows version

The repository includes two ways to generate the portable version.

### Local build

On Windows, run:

```text
build_windows.bat
```

The script:

1. creates a build virtual environment;
2. installs dependencies;
3. installs PyInstaller;
4. generates a single executable without a console window.

The expected result is:

```text
dist\QuestionBankCleaner.exe
```

The generated executable includes the Python interpreter and required dependencies, so the end user **does not need to install Python**.

### Build through GitHub Actions

The file:

```text
.github/workflows/build-windows.yml
```

automatically generates the executable on a Windows runner when:

- the workflow is started manually under **Actions**;
- or a tag beginning with `v` is pushed to the repository.

At the end of the workflow, the executable is available as an artifact:

```text
QuestionBankCleaner-Windows
```

### Program icon

The project already includes its own icon and corresponding files in the `assets/` directory.

The original design was preserved as a **square SVG (1:1)** and the program-use versions were also included:

```text
assets/
├── question_bank_cleaner.ico
├── question_bank_cleaner.svg
├── question_bank_cleaner.png
└── ICON_GUIDE.md
```

The supplied `.ico` file is multi-resolution and contains:

```text
16×16
24×24
32×32
48×48
64×64
128×128
256×256
```

Use 32-bit/RGBA with a transparent background.

The fallback PNG was generated at **256×256 px**.

Both `build_windows.bat` and the GitHub Actions workflow automatically embed `question_bank_cleaner.ico` in the executable.

Detailed instructions are available in:

```text
assets/ICON_GUIDE.md
```

---

## Project structure

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

Main entry point for the graphical version.

Contains:

- GUI;
- visual analysis flow;
- structured review;
- threaded execution to keep the window responsive;
- progress and message logging;
- integration with the cleaning engine.

### `cleaner_core.py`

Analysis engine derived from the original script.

Contains:

- normalization;
- similarity comparison;
- duplicate detection;
- report generation;
- reading and applying decisions;
- original command-line mode.

### `cli.py`

Shortcut for using the traditional terminal workflow.

---

## Command-line mode

The CLI version remains available:

```bash
python cli.py --entrada banco_questoes.js
```

Some inherited options:

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

Example:

```bash
python cli.py ^
  --entrada banco_questoes.js ^
  --aplicar-conflitos ^
  --aplicar-possiveis
```

---

## Development installation

Python 3.11 or later is recommended.

Create a virtual environment:

```bash
python -m venv .venv
```

On Windows:

```bash
.venv\Scripts\activate
```

Install the runtime dependency:

```bash
pip install -r requirements.txt
```

Run the GUI:

```bash
python app.py
```

To prepare builds:

```bash
pip install -r requirements-build.txt
```

---

## Operational safety

The program **can remove questions from the output bank**.

Some recommendations:

- always keep a copy of the original bank;
- do not overwrite the only copy of the source file;
- review reports before applying human decisions;
- inspect the final file before replacing a bank used in production;
- use version control when the bank is part of a Git project.

By default, the application writes a **new output file** and does not directly modify the selected original file.

---

## Limitations

- Text similarity does not replace specialized semantic evaluation.
- Different questions may have very similar wording.
- Equivalent questions may be written differently enough to avoid detection.
- Current thresholds were defined as project heuristics, not as scientific validation of a deduplication method.
- The program assumes the list contained in the JavaScript file is valid JSON.
- Performance depends on bank size and RapidFuzz availability.
- The quality of final review still depends on human analysis of ambiguous cases.

---

## Compatibility

The GUI was developed with **Tkinter**, a graphical library included in standard Python distributions for Windows.

The source version can be used on systems with a compatible Python installation.

The portable executable made available through the project's build process is specific to Windows.

---

## Technologies used

- **Python 3**
- **Tkinter**
- **RapidFuzz** — optional acceleration for text similarity
- **difflib** — similarity fallback
- **PyInstaller** — packaging of the portable version
- **GitHub Actions** — automation of the Windows executable build

---

## 👤 Authorship and development

Desktop utility application independently developed by **Pablo Phillipe Cândido dos Santos**, intended for assisted analysis and deduplication of question banks structured in JavaScript/JSON, combining automatic removal of high-confidence duplicates, identification of similar cases, and human review of ambiguous situations.

Generative artificial intelligence tools were used as auxiliary resources during development, while responsibility for the project's conception, implementation, integration, and verification remained with the author.

Lattes CV: [http://lattes.cnpq.br/9500873674712528](http://lattes.cnpq.br/9500873674712528)
