# Quota Panel para GNOME

![Ícone do Quota Panel](quota-panel-color.svg)

Criador: **[kassio8](https://github.com/kassio8)**. Projeto independente, sem vínculo, patrocínio ou aprovação da OpenAI ou do projeto GNOME. Codex é um produto da OpenAI; o nome identifica apenas o CLI com o qual esta extensão funciona.

Mostra a cota usada da assinatura Codex na barra superior. O indicador exibe somente a porcentagem da janela de 5 horas, como `4%`. Esse valor não representa um total diário de tokens. O menu mantém todas as janelas informadas pelo Codex, seus percentuais e horários de renovação. Quando a janela de 5 horas está indisponível, o indicador mostra `—`.

## Compatibilidade e estado da distribuição

O projeto gera dois **pacotes candidatos de teste**:

- `quota-panel-legacy.shell-extension.zip`: GNOME 42, 43 e 44, com módulos legados.
- `quota-panel-modern.shell-extension.zip`: GNOME 45 a 51, com módulos ESM.

A geração e os testes automatizados não equivalem à validação em cada desktop. A nova versão ainda precisa passar pelos testes de sessão descritos em [DISTRIBUTION.md](DISTRIBUTION.md). Não há promessa de suporte automático a futuras versões. Nenhum pacote foi publicado no GNOME Extensions nesta etapa.

## Requisitos

- GNOME Shell em uma das versões alvo, GJS, GTK4 e libadwaita.
- Codex CLI instalado e autenticado pelo próprio usuário.
- Para gerar pacotes ou usar o instalador do projeto: Python 3 e `glib-compile-schemas`.

O pacote da extensão não inclui Python, o executável Codex, credenciais ou instaladores de dependências. A consulta usa um processo GJS curto e o `codex app-server`; não envia prompts. O leitor limita a resposta a 1 MiB e a consulta a 15 segundos. O Shell mantém um watchdog de 20 segundos e impede consultas sobrepostas.

## Instalar um pacote para teste

Baixe o ZIP em [Releases](https://github.com/kassio8/quota-panel-gnome/releases), crie uma pasta `dist/` e coloque o arquivo nela. Os exemplos abaixo partem da pasta que contém `dist/`. Confira sua versão com `gnome-shell --version`. Use apenas o ZIP correspondente. Por exemplo, no GNOME 42–44:

```bash
gnome-extensions install --force dist/quota-panel-legacy.shell-extension.zip
```

No GNOME 45–51:

```bash
gnome-extensions install --force dist/quota-panel-modern.shell-extension.zip
```

Saia da sessão e entre novamente para carregar alterações de código. Depois, ative pelo aplicativo **Extensões** ou execute:

```bash
gnome-extensions enable codex-quota@kassio8
```

Não instale os dois pacotes juntos: eles compartilham o mesmo UUID.

O identificador interno `codex-quota@kassio8` foi mantido para atualizar instalações existentes sem criar outra extensão. Ele não aponta para um computador nem uma conta. Os ZIPs não levam caminhos pessoais, configurações ou dependências do autor. Cada pessoa precisa ter o Codex CLI instalado e autenticado na própria conta. A extensão procura o CLI no PATH e nas pastas `~/.local/bin` e `~/.npm-global/bin` do usuário atual, inclusive quando essas pastas não aparecem no PATH da sessão gráfica.

Se o Codex estiver em outro local, execute `command -v codex` no terminal desse computador e informe o resultado em **Configurações → Caminho do executável**. Isso também atende instalações via NVM; o processo recebe a pasta do executável no PATH para encontrar o Node instalado ao lado dele. Se uma configuração antiga apontar para outro computador, apague o campo para voltar à detecção automática.

## Migrar da identificação antiga

O UUID mudou de `codex-quota@kassio.local` para `codex-quota@kassio8`. O GNOME considera os dois identificadores extensões diferentes. Se você já usava a versão antiga, desative-a antes de instalar o novo ZIP ou executar o instalador do projeto:

```bash
gnome-extensions disable codex-quota@kassio.local
```

Instale o pacote correspondente à sua versão do GNOME seguindo os comandos acima, saia da sessão e entre novamente. Ative `codex-quota@kassio8`. Mantenha a extensão antiga desativada para evitar dois indicadores e consultas duplicadas.

As preferências GSettings são preservadas porque o esquema e seu caminho continuam iguais. O arquivo local `codex-path.txt` da pasta antiga não é migrado; se a detecção automática não encontrar o CLI, configure o caminho nas preferências da nova extensão.

## Instalar a partir do projeto

```bash
git clone https://github.com/kassio8/quota-panel-gnome.git
cd quota-panel-gnome
sh install.sh
```

O instalador detecta a versão do GNOME e gera os adaptadores adequados. Preserva as configurações, registra o caminho do Codex e cria o atalho **Atualizar Quota Panel**. Requer o Codex CLI já instalado. A interface gráfica usa Zenity e informa quando é necessário sair e entrar na sessão; ela nunca encerra a sessão automaticamente.

O instalador gera o atalho com o caminho desta cópia do projeto. Para gerar apenas o atalho, execute `python3 create-launcher.py ~/.local/share/applications/codex-quota-update.desktop`. Se mover o projeto, gere o atalho novamente. Atalhos locais não são distribuídos no repositório nem nos ZIPs.

## Configurações

Abra o menu do indicador e selecione **Configurações…**.

- **Tipo de logo:** Colorida, Monocromática ou Terminal. As três opções usam desenhos próprios do Quota Panel, sem logos da OpenAI.
- **Tamanho da logo:** 12 a 24 pixels; padrão de 16 pixels.
- **Intervalo entre consultas:** 30 a 900 segundos; padrão para instalações novas de 60 segundos. Valores já salvos, inclusive 30 segundos, são preservados. A alteração substitui o timer imediatamente.
- **Caminho do executável:** caminho absoluto do Codex CLI, sem argumentos. Deixe vazio para procurar `codex` no PATH da sessão gráfica, em `~/.local/bin` e em `~/.npm-global/bin`. O caminho gravado pelo instalador anterior é usado apenas como último recurso. Caminhos com espaços são aceitos.

As configurações usam GSettings e persistem entre sessões. O controle **Restaurar padrão** restaura apenas o tipo e o tamanho da logo. Alterar o caminho do Codex afeta a próxima consulta; o menu também oferece **Atualizar agora**. A interface permanece em português nesta versão.

## Gerar os pacotes

```bash
cd quota-panel-gnome
sh package.sh
```

Os dois ZIPs são gravados em `dist/`. `build.py` converte apenas as formas de importação conhecidas, rejeitando mudanças que exijam novos adaptadores. A lógica de apresentação, atualização e preferências vem da mesma base. `reader.js` roda como programa GJS independente nos dois pacotes.

O manifesto `extension-files.txt` limita os arquivos distribuídos. O arquivo antigo `reader.py` permanece como referência no projeto, mas não entra nos pacotes. Os ícones próprios `quota-panel-*.svg` acompanham a extensão. Consulte [NOTICE](NOTICE) e [LICENSE](LICENSE) para a licença do material distribuído.

Para gerar um candidato restrito ao GNOME 46, use uma pasta separada dos candidatos de outras versões:

```bash
python3 build.py --shell-version 46 --output dist/gnome-46
```

Isso gera somente o ZIP moderno, declarando apenas GNOME 46. A seleção da versão não comprova funcionamento nessa sessão.

## Verificar

O comando completo exige também Node.js (testes do controlador e sintaxe dos pacotes) e `desktop-file-validate` (testes do instalador). Execute fora do sandbox para permitir o teste gráfico GTK/Broadway:

```bash
cd quota-panel-gnome
python3 validate.py
```

Qualquer falha **ou teste ignorado** produz código de saída 1. O sucesso automatizado não substitui os testes de sessão de [DISTRIBUTION.md](DISTRIBUTION.md). Os testes do controlador usam processos, relógio e UI simulados; os testes do leitor usam subprocessos reais com servidores simulados.

Para executar as partes separadamente:

```bash
cd quota-panel-gnome
glib-compile-schemas --strict schemas
for test in test_presentation test_appearance test_refresh test_preferences test_quota; do
    GSETTINGS_BACKEND=memory gjs -m "tests/$test.js" || exit 1
done
python3 -m unittest discover -s tests -v
```

Os testes usam servidores Codex simulados e configurações isoladas; não consultam a assinatura pessoal. O teste de janela GTK usa Broadway e informa quando o ambiente não permite iniciá-lo. Testes do formato legado executados num GJS moderno não substituem um desktop GNOME 42 real.

Para consultar manualmente a conta local:

```bash
gjs -m reader.js
```

O resultado é JSON com `status` igual a `ok`, `unavailable` ou `error`. A extensão mostra percentuais de cota, não uma contagem exata de tokens. Em erros, não apresenta dados anteriores como atuais.

## Remover

```bash
gnome-extensions uninstall codex-quota@kassio8
```

## Privacidade e licença

A extensão consulta o processo local `codex app-server` e lê a resposta de cotas. Não lê diretamente arquivos de credenciais, não envia prompts e não inclui telemetria própria. O Codex CLI realiza a comunicação autenticada necessária com seu serviço. Não envie tokens, arquivos de autenticação ou respostas pessoais em issues.

Código e ícones próprios: **GPL-2.0-or-later**. Veja [LICENSE](LICENSE) e [NOTICE](NOTICE). A licença do projeto não concede direitos sobre marcas de terceiros. O nome público é Quota Panel para GNOME, por kassio8; nomes semelhantes em outros projetos não indicam vínculo.
