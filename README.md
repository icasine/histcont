# histcont

Dados do site de história de Contagem (MG).

| Planilha | Script | Arquivo gerado | Link para o site |
|---|---|---|---|
| Calendário de Contagem | `scripts/gerar_eventos.py` | `eventos.json` | https://raw.githubusercontent.com/icasine/histcont/main/eventos.json |

## Como funciona

- O workflow `.github/workflows/atualizar-eventos.yml` roda todo dia às 16h (Brasília), lê a planilha publicada em CSV (link no bloco `env`) e grava `eventos.json`.
- Cada coluna de ano (2024, 2025...) vira uma ocorrência. Formatos aceitos: `dd/mm/aaaa`, `dd/mm/aaaa a dd/mm/aaaa`, `mm/aaaa` (mês sem dia) e `aaaa` (ano sem data). Célula vazia: não acontece ou ainda não foi definido.
- Para acrescentar um ano, basta criar a coluna (ex.: `2036`) na planilha; o script reconhece sozinho.
- Linhas com `publicar` diferente de "sim" ficam fora. A coluna `obs_internas` nunca vai para o JSON.
- Avisos (id repetido, data não reconhecida) aparecem no resumo da execução, em Actions.

Para rodar na hora: Actions > Atualizar eventos.json (Calendário de Contagem) > Run workflow.
