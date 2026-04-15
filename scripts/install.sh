#!/usr/bin/env bash

set -euo pipefail

REPO_URL="${LETSVIBEDESIGN_REPO_URL:-https://github.com/kmeanskaran/desysflow-oss.git}"
REPO_REF="${LETSVIBEDESIGN_REPO_REF:-main}"
INSTALL_HOME="${LETSVIBEDESIGN_HOME:-$HOME/.letsvibedesign}"
REPO_DIR="${LETSVIBEDESIGN_REPO_DIR:-$INSTALL_HOME/desysflow-oss}"
LOCAL_REPO="${LETSVIBEDESIGN_LOCAL_REPO:-}"
BIN_DIR="${LETSVIBEDESIGN_BIN_DIR:-$HOME/.local/bin}"
LAUNCHER_PATH="$BIN_DIR/letsvibedesign"
OFFLINE="${LETSVIBEDESIGN_OFFLINE:-0}"
README_URL="${LETSVIBEDESIGN_README_URL:-https://github.com/kmeanskaran/desysflow-oss#readme}"
DOCS_URL="${LETSVIBEDESIGN_DOCS_URL:-https://github.com/kmeanskaran/desysflow-oss/tree/main/docs}"
GETTING_STARTED_URL="${LETSVIBEDESIGN_GETTING_STARTED_URL:-https://github.com/kmeanskaran/desysflow-oss/blob/main/docs/getting-started.md}"
BRAND="desysflow🌀"
LOG_DIR="${TMPDIR:-/tmp}"
INSTALL_LOG=""

log() {
  printf '%s %s\n' "$BRAND" "$1"
}

warn() {
  printf '%s %s\n' "$BRAND warning:" "$1" >&2
}

die() {
  printf '%s %s\n' "$BRAND error:" "$1" >&2
  if [ -n "${INSTALL_LOG:-}" ] && [ -f "$INSTALL_LOG" ]; then
    printf '\nLog: %s\n' "$INSTALL_LOG" >&2
  fi
  exit 1
}

step() {
  printf '\n%s %s\n' "$BRAND" "$1"
}

success() {
  printf '%s %s\n' "$BRAND done:" "$1"
}

run_logged() {
  local label="$1"
  shift
  printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$label" >> "$INSTALL_LOG"
  if ! "$@" >> "$INSTALL_LOG" 2>&1; then
    warn "$label failed. Recent log output:"
    tail -n 40 "$INSTALL_LOG" >&2 || true
    return 1
  fi
}

prepare_log_file() {
  mkdir -p "$LOG_DIR"
  INSTALL_LOG="$(mktemp "$LOG_DIR/desysflow-install.XXXXXX.log")"
}

has_cmd() {
  command -v "$1" >/dev/null 2>&1
}

is_true() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

detect_platform() {
  local kernel
  kernel="$(uname -s)"
  case "$kernel" in
    Darwin) PLATFORM="macos" ;;
    Linux) PLATFORM="linux" ;;
    *)
      die "unsupported platform: $kernel"
      ;;
  esac

  if [ "$PLATFORM" = "linux" ] && grep -qiE '(microsoft|wsl)' /proc/version 2>/dev/null; then
    PLATFORM="wsl2"
  fi
}

ensure_system_deps() {
  local missing=0

  for cmd in curl git; do
    if ! has_cmd "$cmd"; then
      warn "missing required command: $cmd"
      missing=1
    fi
  done

  if ! has_cmd node; then
    warn "missing required command: node"
    missing=1
  fi

  if ! has_cmd npm; then
    warn "missing required command: npm"
    missing=1
  fi

  if [ "$missing" -eq 0 ]; then
    return
  fi

  if [ "$PLATFORM" = "macos" ]; then
    if ! has_cmd brew; then
      die "Homebrew is required to auto-install dependencies on macOS. Install brew, then rerun this script."
    fi
    step "Installing missing system packages with Homebrew"
    run_logged "brew install git node" brew install git node
    success "System packages installed"
    return
  fi

  if has_cmd apt-get; then
    step "Installing missing system packages with apt"
    run_logged "sudo apt-get update" sudo apt-get update
    run_logged "sudo apt-get install -y curl git nodejs npm" sudo apt-get install -y curl git nodejs npm
    success "System packages installed"
    return
  fi

  if has_cmd dnf; then
    step "Installing missing system packages with dnf"
    run_logged "sudo dnf install -y curl git nodejs npm" sudo dnf install -y curl git nodejs npm
    success "System packages installed"
    return
  fi

  if has_cmd pacman; then
    step "Installing missing system packages with pacman"
    run_logged "sudo pacman -Sy --noconfirm curl git nodejs npm" sudo pacman -Sy --noconfirm curl git nodejs npm
    success "System packages installed"
    return
  fi

  die "could not install system dependencies automatically. Install curl, git, node, and npm, then rerun."
}

ensure_uv() {
  if has_cmd uv; then
    return
  fi

  if is_true "$OFFLINE"; then
    die "uv is required in offline mode. Install uv first, then rerun."
  fi

  step "Installing uv"
  run_logged "Installing uv via Astral installer" sh -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'

  if [ -x "$HOME/.local/bin/uv" ]; then
    PATH="$HOME/.local/bin:$PATH"
    export PATH
  fi

  has_cmd uv || die "uv installation completed but uv is still not on PATH"
  success "uv is ready"
}

install_repo() {
  mkdir -p "$INSTALL_HOME"

  if [ -n "$LOCAL_REPO" ]; then
    LOCAL_REPO="$(cd "$LOCAL_REPO" && pwd)"
    [ -f "$LOCAL_REPO/letsvibedesign" ] || die "LETSVIBEDESIGN_LOCAL_REPO does not look like a desysflow checkout: $LOCAL_REPO"
    REPO_DIR="$LOCAL_REPO"
    success "Using local repository at $REPO_DIR"
    return
  fi

  if [ -d "$REPO_DIR/.git" ]; then
    if is_true "$OFFLINE"; then
      success "Using existing offline installation at $REPO_DIR"
      return
    fi
    step "Updating existing installation"
    run_logged "git fetch origin $REPO_REF --depth 1" git -C "$REPO_DIR" fetch origin "$REPO_REF" --depth 1
    run_logged "git checkout -B $REPO_REF origin/$REPO_REF" git -C "$REPO_DIR" checkout -B "$REPO_REF" "origin/$REPO_REF"
    success "Repository updated"
    return
  fi

  if [ -e "$REPO_DIR" ]; then
    die "install path exists and is not a git repository: $REPO_DIR"
  fi

  if is_true "$OFFLINE"; then
    die "offline mode requires an existing install at $REPO_DIR or LETSVIBEDESIGN_LOCAL_REPO to be set"
  fi

  step "Cloning repository"
  run_logged "git clone --depth 1 --branch $REPO_REF $REPO_URL $REPO_DIR" git clone --depth 1 --branch "$REPO_REF" "$REPO_URL" "$REPO_DIR"
  success "Repository cloned"
}

bootstrap_repo() {
  step "Bootstrapping runtime"
  run_logged "bootstrap.sh" env \
    REPO_DIR="$REPO_DIR" \
    DESYSFLOW_BOOTSTRAP_PYTHON="${DESYSFLOW_BOOTSTRAP_PYTHON:-3.11}" \
    bash -c '
    cd "$REPO_DIR"
    DESYSFLOW_BOOTSTRAP_NON_INTERACTIVE=1 \
    DESYSFLOW_SKIP_MODEL_CHECK=1 \
    DESYSFLOW_BOOTSTRAP_PYTHON="$DESYSFLOW_BOOTSTRAP_PYTHON" \
    ./scripts/bootstrap.sh
  '
  success "Python environment and UI dependencies are ready"
}

install_launcher() {
  step "Installing launcher"
  mkdir -p "$BIN_DIR"
  cat > "$LAUNCHER_PATH" <<EOF
#!/usr/bin/env bash
set -euo pipefail
exec "$REPO_DIR/letsvibedesign" "\$@"
EOF
  chmod +x "$LAUNCHER_PATH"
  success "Launcher installed at $LAUNCHER_PATH"
}

shell_rc_path() {
  case "${SHELL:-}" in
    */zsh)
      printf '%s\n' "$HOME/.zshrc"
      ;;
    */bash)
      if [ -f "$HOME/.bashrc" ]; then
        printf '%s\n' "$HOME/.bashrc"
      else
        printf '%s\n' "$HOME/.bash_profile"
      fi
      ;;
    *)
      if [ -f "$HOME/.zshrc" ]; then
        printf '%s\n' "$HOME/.zshrc"
      else
        printf '%s\n' "$HOME/.bashrc"
      fi
      ;;
  esac
}

ensure_path_export() {
  local path_dir path_line rc_file
  rc_file="$(shell_rc_path)"
  path_dir="$BIN_DIR"
  if [ "$path_dir" = "$HOME/.local/bin" ]; then
    path_line='export PATH="$HOME/.local/bin:$PATH"'
  else
    path_line="export PATH=\"$path_dir:\$PATH\""
  fi

  mkdir -p "$(dirname "$rc_file")"
  touch "$rc_file"

  if ! grep -Fqx "$path_line" "$rc_file"; then
    step "Updating shell PATH"
    {
      printf '\n# letsvibedesign\n'
      printf '%s\n' "$path_line"
    } >> "$rc_file"
    success "Added $BIN_DIR to PATH in $rc_file"
  else
    success "PATH already includes $BIN_DIR in $rc_file"
  fi
}

print_next_steps() {
  local rc_file
  rc_file="$(shell_rc_path)"

  cat <<EOF

$BRAND installed successfully.

Run:
  source "$rc_file" && letsvibedesign

Paths:
  Repo: $REPO_DIR
  Launcher: $LAUNCHER_PATH
  Shell rc: $rc_file

GitHub:
  README: $README_URL
  Docs: $DOCS_URL
  Getting started: $GETTING_STARTED_URL

Notes:
  - Platform: $PLATFORM
  - Offline mode: $OFFLINE
  - Default config: $REPO_DIR/.env.example
  - Install log: $INSTALL_LOG
EOF
}

main() {
  prepare_log_file
  detect_platform
  log "$BRAND installer"
  success "Detected platform: $PLATFORM"
  ensure_system_deps
  ensure_uv
  install_repo
  bootstrap_repo
  install_launcher
  ensure_path_export
  print_next_steps
}

main "$@"
