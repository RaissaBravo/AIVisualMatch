#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
API_DIR="$ROOT_DIR/VisualMatch.API"
APP_DIR="$ROOT_DIR/VisualMatch.APP"
API_PORT="${VISUALMATCH_API_PORT:-8000}"
PROXY_PORT="${VISUALMATCH_PROXY_PORT:-8001}"
METRO_PORT="${VISUALMATCH_METRO_PORT:-8081}"
ENV_FILE="$APP_DIR/.env.local"
EXPORT_VENV="$API_DIR/.venv-export"
API_PID=""
SOCAT_PID=""

cleanup() {
  trap - INT TERM EXIT

  printf '\nEncerrando VisualMatch...\n'
  if [[ -n "$SOCAT_PID" ]] && kill -0 "$SOCAT_PID" 2>/dev/null; then
    kill "$SOCAT_PID" 2>/dev/null || true
  fi
  if [[ -n "$API_PID" ]] && kill -0 "$API_PID" 2>/dev/null; then
    kill "$API_PID" 2>/dev/null || true
    wait "$API_PID" 2>/dev/null || true
  fi
}

fail() {
  printf 'Erro: %s\n' "$1" >&2
  exit 1
}

command -v npm >/dev/null 2>&1 || fail "npm não encontrado. Instale o Node.js 20.19.4 ou superior."
command -v socat >/dev/null 2>&1 || fail "socat não encontrado. Instale com: brew install socat"
command -v ipconfig >/dev/null 2>&1 || fail "ipconfig não encontrado; este script deve ser executado no macOS."
NODE_VERSION="$(node -p 'process.versions.node')"
IFS=. read -r NODE_MAJOR NODE_MINOR NODE_PATCH <<< "$NODE_VERSION"
if (( NODE_MAJOR < 20 || (NODE_MAJOR == 20 && NODE_MINOR < 19) || (NODE_MAJOR == 20 && NODE_MINOR == 19 && NODE_PATCH < 4) )); then
  fail "Node.js $NODE_VERSION não é suportado. Ative a versão 20.19.4 ou superior (por exemplo: nvm use 20)."
fi
[[ -x "$API_DIR/.venv/bin/python" ]] || fail "Ambiente Python ausente. Crie-o em VisualMatch.API/.venv e instale requirements.txt."
[[ -d "$APP_DIR/node_modules" ]] || fail "Dependências do app ausentes. Execute npm install em VisualMatch.APP."

if lsof -nP -iTCP:"$API_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  fail "a porta $API_PORT já está em uso. Encerre o processo atual ou defina VISUALMATCH_API_PORT."
fi
if lsof -nP -iTCP:"$PROXY_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  fail "a porta $PROXY_PORT já está em uso. Encerre o processo atual ou defina VISUALMATCH_PROXY_PORT."
fi
if lsof -nP -iTCP:"$METRO_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  fail "a porta $METRO_PORT já está sendo usada, provavelmente por outro Metro. Encerre-o antes de continuar."
fi

# The ONNX files are not in git: export every registered model that is missing.
MISSING_MODELS="$(cd "$API_DIR" && .venv/bin/python -c 'from app import config; print(" ".join(spec.id for spec in config.MODELS.values() if not spec.path.exists()))')" \
  || fail "não foi possível ler o registro de modelos da API."
if [[ -n "$MISSING_MODELS" ]]; then
  printf 'Modelos ausentes em VisualMatch.API/models (%s); exportando a partir dos pesos oficiais.\n' "$MISSING_MODELS"
  if [[ ! -x "$EXPORT_VENV/bin/python" ]]; then
    printf 'Primeira exportação: instalando PyTorch em %s (alguns minutos).\n' "$EXPORT_VENV"
    "$API_DIR/.venv/bin/python" -m venv "$EXPORT_VENV"
    "$EXPORT_VENV/bin/pip" install -q -r "$API_DIR/requirements-export.txt" || { rm -rf "$EXPORT_VENV"; fail "não foi possível instalar requirements-export.txt."; }
  fi
  (cd "$API_DIR" && "$EXPORT_VENV/bin/python" scripts/export_models.py) || fail "não foi possível exportar os modelos: $MISSING_MODELS."
fi

NETWORK_INTERFACE="$(route -n get default 2>/dev/null | awk '/interface:/{print $2; exit}')"
MAC_IP=""
if [[ -n "$NETWORK_INTERFACE" ]]; then
  MAC_IP="$(ipconfig getifaddr "$NETWORK_INTERFACE" 2>/dev/null || true)"
fi
if [[ -z "$MAC_IP" ]]; then
  MAC_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)"
fi
[[ -n "$MAC_IP" ]] || fail "não foi possível descobrir o IP local do Mac. Verifique a conexão de rede."

export EXPO_PUBLIC_API_BASE_URL="http://$MAC_IP:$PROXY_PORT"

ENV_TEMP="$(mktemp "${TMPDIR:-/tmp}/visualmatch-env.XXXXXX")"
if [[ -f "$ENV_FILE" ]]; then
  awk -v api_url="$EXPO_PUBLIC_API_BASE_URL" '
    BEGIN { updated = 0 }
    /^EXPO_PUBLIC_API_BASE_URL=/ {
      if (!updated) print "EXPO_PUBLIC_API_BASE_URL=" api_url
      updated = 1
      next
    }
    { print }
    END {
      if (!updated) print "EXPO_PUBLIC_API_BASE_URL=" api_url
    }
  ' "$ENV_FILE" > "$ENV_TEMP"
else
  printf 'EXPO_PUBLIC_API_BASE_URL=%s\n' "$EXPO_PUBLIC_API_BASE_URL" > "$ENV_TEMP"
fi
mv "$ENV_TEMP" "$ENV_FILE"

trap cleanup INT TERM EXIT

printf 'VisualMatch\n'
printf '  API local:       http://127.0.0.1:%s\n' "$API_PORT"
printf '  API no celular:  %s\n' "$EXPO_PUBLIC_API_BASE_URL"
printf '  Model info:      %s/api/model-info\n' "$EXPO_PUBLIC_API_BASE_URL"
printf '  Modelos:         todos prontos na API; escolha qual usar no app\n'
printf '  .env.local:      atualizado\n'
printf '\nUse Ctrl+C para encerrar API, proxy e Metro.\n\n'

(
  cd "$API_DIR"
  exec .venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port "$API_PORT"
) &
API_PID=$!

socat "TCP-LISTEN:$PROXY_PORT,fork,reuseaddr,bind=0.0.0.0" "TCP:127.0.0.1:$API_PORT" &
SOCAT_PID=$!

sleep 1
kill -0 "$API_PID" 2>/dev/null || fail "a API encerrou durante a inicialização."
kill -0 "$SOCAT_PID" 2>/dev/null || fail "o socat encerrou durante a inicialização."

cd "$APP_DIR"
npm run dev -- --clear --port "$METRO_PORT"
