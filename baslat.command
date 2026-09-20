#!/usr/bin/env bash
# macOS: Finder'da çift tıklanabilir başlatıcı (Terminal açar).
#   baslat.command          → menü
#   baslat.command seri     → sunucu + seri köprü
#   baslat.command kopru-seri → yalnız seri köprü (campus.gazisiber.org için)
cd "$(dirname "$0")" || exit 1
exec ./baslat.sh "$@"
