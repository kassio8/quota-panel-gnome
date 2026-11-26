# Quota Panel no macOS

Requer macOS e Python 3.9+.

Instalar ou atualizar:

```sh
./macos/install.sh
```

O instalador cria o ambiente em `~/Library/Application Support/QuotaPanel`, inicia no login e instala `rumps==0.4.0`. Edite `config.json` pelo menu **Configurações…**; `intervalSeconds` aceita 30–900 e `codexPath` aceita caminho absoluto.

Desinstalar:

```sh
./macos/uninstall.sh
```

O arquivo `config.json` fica preservado. Se o Codex estiver fora do PATH, configure `codexPath` ou instale novamente com o Codex disponível no terminal. Se o ícone ficar escondido pelo notch, procure os itens extras da barra ou reduza os ícones da barra. Faça login pelo Codex CLI antes de consultar a cota.
