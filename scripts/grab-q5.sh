#!/usr/bin/env bash
cd /d/GenerativeCreation/models/diffusion_models || exit 1
URL="https://www.modelscope.cn/models/unsloth/Qwen-Image-Edit-2511-GGUF/resolve/master/qwen-image-edit-2511-Q5_K_M.gguf"
F=qwen-image-edit-2511-Q5_K_M.gguf
TOTAL=15395662432
for i in $(seq 1 80); do
  SZ=$(stat -c %s "$F" 2>/dev/null || echo 0)
  if [ "$SZ" -ge "$TOTAL" ]; then echo "DONE $SZ/$TOTAL"; exit 0; fi
  echo "try $i size=$SZ/$TOTAL"
  curl -L -C - --retry 8 --retry-delay 3 --retry-all-errors --speed-time 45 --speed-limit 30000 -o "$F" "$URL" -s
  echo "curl exit $? size=$(stat -c %s "$F" 2>/dev/null)"
  sleep 3
done
echo "GAVEUP"
