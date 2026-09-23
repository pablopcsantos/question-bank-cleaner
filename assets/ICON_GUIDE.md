# Ícone do Question Bank Cleaner

Os recursos definitivos do ícone já estão incluídos no projeto.

## Arquivos

```text
assets/
├── question_bank_cleaner.ico
├── question_bank_cleaner.svg
├── question_bank_cleaner.png
└── ICON_GUIDE.md
```

### `question_bank_cleaner.svg`

Arquivo-fonte vetorial do ícone, preservado no repositório para organização documental e futuras edições.

Características do arquivo fornecido:

- proporção 1:1;
- `viewBox`: `0 0 280 280`;
- dimensões declaradas: `280 mm × 280 mm`.

### `question_bank_cleaner.ico`

Arquivo utilizado pelo executável Windows e pela janela principal.

O arquivo fornecido já contém as seguintes resoluções:

```text
16×16
24×24
32×32
48×48
64×64
128×128
256×256
```

Portanto, ele está adequado para uso como ícone multirresolução no Windows.

### `question_bank_cleaner.png`

Fallback gráfico em **256×256 px**, gerado a partir do `.ico`.

Ele é usado pelo código quando a plataforma não aceita diretamente o `.ico`.

## Build

O `build_windows.bat` e o workflow do GitHub Actions detectam automaticamente:

```text
assets/question_bank_cleaner.ico
assets/question_bank_cleaner.png
```

O `.ico` é incorporado ao `QuestionBankCleaner.exe` durante o build com PyInstaller.
