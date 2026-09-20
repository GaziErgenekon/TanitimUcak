#!/usr/bin/env bash
# GAZİ Kampüs Uçuş Simülatörü — Linux/macOS başlatıcı.
#   ./baslat.sh              → menü
#   ./baslat.sh sunucu       → yalnız sunucu + tarayıcı
#   ./baslat.sh seri [PORT]  /  ./baslat.sh bt [AD]
#   ./baslat.sh kopru-seri [PORT]  /  ./baslat.sh kopru-bt [AD]
#       (hosted sayfa campus.gazisiber.org için yalnız köprü; sunucu açılmaz)
set -e
cd "$(dirname "$0")"

PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then
  echo "HATA: Python 3 bulunamadı. Kurun: sudo apt install python3 python3-venv"
  exit 1
fi

exec "$PY" baslat.py "$@"
