set -e
cd /d/GenerativeCreation/models
DL=https://modelscope.cn/models
get() {
  url="$1"; out="$2"
  echo "[dl] $out"
  curl -L --retry 3 --retry-delay 5 -C - --progress-bar "$url" -o "$out"
  ls -lh "$out"
}
get "$DL/AI-ModelScope/FLUX.1-Fill-dev-gguf/resolve/master/flux1-fill-dev-fp16-Q5_0-GGUF.gguf" diffusion_models/flux1-fill-dev-Q5_0.gguf
get "$DL/AI-ModelScope/flux_text_encoders/resolve/master/t5xxl_fp8_e4m3fn.safetensors" text_encoders/t5xxl_fp8_e4m3fn.safetensors
get "$DL/AI-ModelScope/flux_text_encoders/resolve/master/clip_l.safetensors" text_encoders/clip_l.safetensors
get "$DL/black-forest-labs/FLUX.1-Fill-dev/resolve/master/ae.safetensors" vae/ae.safetensors
echo ALL_DL_OK
