#!/bin/sh
set -eu

source_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
data_home=${XDG_DATA_HOME:-"$HOME/.local/share"}
target="$data_home/gnome-shell/extensions/codex-quota@kassio8"
command -v zenity >/dev/null

restart_needed=true
if sh "$source_dir/install.sh" --check >/dev/null 2>&1; then
    restart_needed=false
fi

if output=$(sh "$source_dir/install.sh" 2>&1); then
    if [ "$restart_needed" = true ]; then
        message='Atualização instalada. Para carregar o código novo, saia da sessão Ubuntu e entre novamente.

Logo, tamanho e intervalo são salvos automaticamente nas configurações.

O atalho Atualizar Quota Panel está disponível no menu de aplicativos. Se o indicador não aparecer, abra Extensões e ative Quota Panel.'
    else
        message='A extensão já está com os mesmos arquivos. O atalho Atualizar Quota Panel foi registrado no menu de aplicativos.

Logo, tamanho e intervalo são salvos automaticamente nas configurações.'
    fi
    zenity --info --no-markup --title='Quota Panel' --width=460 --text="$message" || true
else
    zenity --error --no-markup --title='Quota Panel' --width=460 \
        --text="Não foi possível concluir a instalação.

$output" || true
    exit 1
fi
