#!/bin/sh
set -eu

uuid='codex-quota@kassio8'
source_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
data_home=${XDG_DATA_HOME:-"$HOME/.local/share"}
target="$data_home/gnome-shell/extensions/$uuid"
shell_version=$(gnome-shell --version | sed -n 's/.* \([0-9][0-9]*\)\..*/\1/p')
if [ -z "$shell_version" ]; then
    printf '%s\n' 'Não foi possível identificar a versão do GNOME Shell.' >&2
    exit 1
fi
stage_dir=$(mktemp -d)
trap 'rm -rf "$stage_dir"' EXIT HUP INT TERM
python3 "$source_dir/build.py" --stage "$stage_dir" --shell-version "$shell_version"
if [ "${1:-}" = '--check' ]; then
    while IFS= read -r relative || [ -n "$relative" ]; do
        [ -n "$relative" ] || continue
        cmp -s "$stage_dir/$relative" "$target/$relative" || exit 1
    done < "$source_dir/extension-files.txt"
    exit 0
fi
codex_bin=$(command -v codex || true)
if [ -z "$codex_bin" ] && [ -r "$target/codex-path.txt" ]; then
    IFS= read -r codex_bin < "$target/codex-path.txt" || true
fi
if [ ! -x "$codex_bin" ] && [ -x "$HOME/.local/bin/codex" ]; then
    codex_bin="$HOME/.local/bin/codex"
fi
if [ -z "$codex_bin" ] || [ ! -x "$codex_bin" ]; then
    printf '%s\n' 'Codex CLI não encontrado. Confira a instalação do Codex antes de atualizar.' >&2
    exit 1
fi
command -v glib-compile-schemas >/dev/null

mkdir -p "$target/schemas"
while IFS= read -r relative || [ -n "$relative" ]; do
    [ -n "$relative" ] || continue
    mkdir -p "$(dirname -- "$target/$relative")"
    cp "$stage_dir/$relative" "$target/$relative"
done < "$source_dir/extension-files.txt"
glib-compile-schemas --strict "$target/schemas"
printf '%s\n' "$codex_bin" > "$target/codex-path.txt"
python3 "$source_dir/create-launcher.py" "$data_home/applications/codex-quota-update.desktop"

if ! gnome-extensions enable "$uuid"; then
    printf '%s\n' 'A extensão foi copiada. Saia da sessão GNOME e entre novamente.'
    printf '%s\n' 'Depois, abra o aplicativo Extensões e ative Quota Panel.'
    exit 0
fi

printf '%s\n' 'Arquivos atualizados: consulta a cada 1 minuto e intervalo ajustável nas preferências.'
printf '%s\n' 'Saia da sessão GNOME e entre novamente para carregar esta versão.'
printf '%s\n' 'O GNOME mantém os módulos anteriores na memória até reiniciar a sessão.'
printf '%s\n' 'Depois, abra o indicador e escolha Configurações…; os ajustes serão aplicados na hora.'
