# Distribuição do Quota Panel para GNOME

Projeto independente de kassio8: https://github.com/kassio8/quota-panel-gnome.

## Pacotes candidatos

- `quota-panel-legacy.shell-extension.zip`: GNOME 42–44.
- `quota-panel-modern.shell-extension.zip`: GNOME 45–51.

Os metadados declaram versões alvo para testes. Isso não comprova funcionamento em todas essas sessões. Os pacotes são distribuídos como pré-lançamento no GitHub, sem publicação no GNOME Extensions.

A base anterior foi usada em GNOME 46. A identidade pública e os ícones atuais ainda precisam ser verificados em sessão real. Testes GJS, testes de preferências GTK/Broadway e servidores Codex simulados não substituem essa validação.

## Gerar e validar

Na raiz do repositório:

```bash
python3 validate.py
sh package.sh
```

Os ZIPs ficam em `dist/`. Para restringir os metadados a uma versão:

```bash
python3 build.py --shell-version 46 --output dist/gnome-46
```

`extension-files.txt` define o conteúdo dos ZIPs. O construtor usa uma pasta temporária limpa e compila os esquemas. Credenciais, caminhos pessoais, atalhos locais, caches e arquivos Python não entram nos pacotes. O código Python do repositório serve ao desenvolvimento e à referência histórica do leitor.

## Teste em sessão

Use a versão exata do GNOME e um Codex CLI instalado e autenticado pelo próprio usuário.

1. Instale o ZIP correspondente, inicie uma nova sessão e ative a extensão.
2. Confira ícone, percentual da janela de 5 horas, menu e horários de renovação.
3. Teste as três opções de ícone, tamanho e persistência das preferências.
4. Teste caminho automático e explícito do CLI, incluindo caminhos com espaços.
5. Altere o intervalo e confirme que não há consultas simultâneas ou timers duplicados.
6. Desative e reative durante uma consulta; confira o encerramento do processo.
7. Teste CLI ausente, autenticação ausente, resposta inválida e timeout.
8. Teste bloqueio/desbloqueio, reinstalação e uma instalação limpa em outro usuário.

Registre distribuição, versões do GNOME, GJS, libadwaita e Codex CLI. Não inclua credenciais ou respostas pessoais nos registros públicos.

## Identidade e atualização

O nome público é **Quota Panel**. O UUID `codex-quota@kassio8` e o esquema `org.gnome.shell.extensions.codex-quota` são identificadores internos mantidos por compatibilidade. A mudança visual não cria outra extensão nem redefine preferências.

Instalações antigas com `codex-quota@kassio.local` devem seguir a migração do [README](README.md#migrar-da-identificação-antiga). Não mantenha os dois UUIDs ativos.

## Publicação no GNOME Extensions

Antes de enviar à loja, valide cada sessão declarada, gere metadados restritos às versões aprovadas e confira as [regras de revisão atuais](https://gjs.guide/extensions/review-guidelines/review-guidelines.html). A publicação no GitHub não implica aprovação pela loja.
