# Arquitetura do Quota Panel para GNOME

O Quota Panel é uma extensão de GNOME Shell que mostra **quanto da cota da assinatura Codex já foi usado**. No painel, `12%` significa 12% usados na janela de cinco horas. O menu detalha as janelas e os horários de renovação que o Codex CLI da pessoa informou. A autenticação e a comunicação com o serviço ficam a cargo do CLI.

## Caminho de uma consulta

1. O GNOME carrega [extension.js](extension.js). `CodexQuotaExtension.enable()` cria o indicador, inicia a primeira consulta e registra o temporizador. O temporizador e a ação **Atualizar agora** chamam o mesmo método, `_refresh()`.
2. O Shell inicia um processo separado com `gjs -m reader.js`, usando o caminho do script na extensão instalada. [reader.js](reader.js) localiza o executável e inicia `codex app-server` com argumentos separados. Os dois processos trocam mensagens JSON, uma por linha, via entrada e saída padrão.
3. O leitor envia `initialize`, aguarda a resposta, envia a notificação `initialized` e solicita `account/rateLimits/read`. Ele associa cada resposta ao ID da solicitação. Essa operação consulta cotas usando a sessão autenticada do CLI. A extensão não precisa abrir arquivos de credenciais nem enviar prompts.
4. [quota.js](quota.js) converte o resultado em grupos de limites (`buckets`) e janelas. O leitor imprime **um objeto JSON** em stdout e termina. O Shell interpreta esse objeto e usa [presentation.js](presentation.js) para formatar o painel e o menu. Mensagens de diagnóstico do leitor em stdout quebrariam esse contrato.

## Como interpretar os dados

`normalizeRateLimits()` prefere `rateLimitsByLimitId`, inclusive quando o mapa está vazio. Quando esse campo não é um objeto, tenta `rateLimits`. Em cada grupo, coleta as janelas `primary` e `secondary` e ordena por duração. Exemplo sintético da saída do leitor:

```json
{
  "status": "ok",
  "checkedAt": 1710000000,
  "ordinaryUsageAllowed": null,
  "buckets": [{
    "id": "codex",
    "name": "Codex",
    "windows": [{"durationMinutes": 300, "usedPercent": 12, "resetsAt": 1710018000}]
  }]
}
```

Os horários são segundos Unix. Um percentual desconhecido vira `null`; zero é uma medição válida. O estado `ok` exige algum percentual válido em alguma janela. Já `summaryLabel()` procura exatamente 300 minutos no grupo `codex`, ou no primeiro grupo se `codex` estiver ausente. Por isso uma resposta semanal válida pode aparecer no menu com `—` no painel.

`unavailable` indica uma consulta concluída sem percentuais utilizáveis. Em falha de execução, protocolo, autenticação ou timeout, o leitor retorna `error` com uma mensagem. O menu troca os dados anteriores pelo estado atual.

## Pontos de manutenção

| Mudança | Onde editar | Comportamento a preservar |
| --- | --- | --- |
| Consultas e ciclo de vida | [extension.js](extension.js), [refresh.js](refresh.js) | Uma consulta em andamento por vez. Ao desativar, cancelar timers, desconectar sinais e sinalizar o leitor. O contador de geração descarta respostas de uma ativação anterior. |
| Descoberta do CLI e protocolo | [reader.js](reader.js) | Um caminho explícito inválido gera erro. Com o campo vazio, a ordem é PATH, `~/.local/bin/codex`, `~/.npm-global/bin/codex` e o caminho salvo em `codex-path.txt` na instalação. O diretório do executável entra no PATH do filho. |
| Limites da consulta | [reader.js](reader.js), [extension.js](extension.js) | O leitor limita a leitura acumulada a 1 MiB e cancela a consulta após 15 s por padrão. O Shell envia SIGTERM ao leitor após 20 s. O leitor encerra o app-server e aguarda sua saída. |
| Preferências | [prefs.js](prefs.js), [preferences-ui.js](preferences-ui.js), [esquema GSettings](schemas/org.gnome.shell.extensions.codex-quota.gschema.xml) | A janela GTK4/libadwaita compartilha as chaves com o Shell. Aparência muda na hora. Alterar o intervalo substitui o timer; alterar o caminho afeta a próxima consulta. |
| Ícones | [appearance.js](appearance.js), [manifesto](extension-files.txt) | Os três SVGs pertencem ao projeto. Os índices salvos são 0 para colorido, 1 para monocromático e 2 para terminal. As barras representam uso de cota e distinguem a extensão da identidade visual da OpenAI. |

O nome público é **Quota Panel**. O GNOME identifica a instalação pelo UUID `codex-quota@kassio8`. As preferências ficam no esquema `org.gnome.shell.extensions.codex-quota`. Os identificadores estão em [metadata.json](metadata.json).

## Fonte, pacotes e verificação

Edite a fonte na raiz do repositório. [build.py](build.py) copia os arquivos declarados no manifesto, ajusta os metadados e compila o esquema. O pacote moderno usa módulos ES para GNOME 45–51. Para GNOME 42–44, o construtor adapta a entrada do Shell, a entrada de preferências e os módulos compartilhados usados por elas. O leitor continua sendo um processo GJS com módulos ES nos dois pacotes. Ao introduzir um novo import na extensão, confira também o adaptador legado. O leitor Python em [reader.py](reader.py) serve como referência histórica. O executável distribuído pelo projeto para ler cotas é o script GJS.

Na raiz do repositório, execute `python3 validate.py` para validar o código e `sh package.sh` para gerar ambos os ZIPs em `dist/`. Para alterações no protocolo, consulte [test_gjs_reader.py](tests/test_gjs_reader.py), que roda o leitor real com servidores simulados. Para concorrência e desativação, consulte [test_lifecycle.js](tests/test_lifecycle.js). Para conferir o que chega ao usuário, [test_packages.py](tests/test_packages.py) extrai os ZIPs e exercita o leitor em um ambiente isolado. A validação em sessões reais de GNOME está descrita em [DISTRIBUTION.md](DISTRIBUTION.md).
