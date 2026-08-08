#!/usr/bin/env bash
# image-vision 一键安装脚本（macOS / Linux）
# 用法: bash install.sh
# 安装位置: ~/.config/image-vision/（脚本与配置）
#          ~/.config/opencode/skills/image-vision/SKILL.md（opencode）

set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST_DIR="$HOME/.config/image-vision"
OPENCODE_SKILL_DIR="$HOME/.config/opencode/skills/image-vision"
CLAUDE_SKILL_DIR="$HOME/.claude/skills/image-vision"

echo "== 安装 image-vision =="

# 1. 复制脚本与配置模板到统一安装目录
mkdir -p "$DEST_DIR"
cp "$SRC_DIR/vision.py" "$DEST_DIR/"
cp "$SRC_DIR/config.example.json" "$DEST_DIR/"
cp "$SRC_DIR/SKILL.md" "$DEST_DIR/"

# 2. 首次安装时生成 config.json（存在则保留，不覆盖用户配置）
CONFIG_PATH="$DEST_DIR/config.json"
if [ ! -f "$CONFIG_PATH" ]; then
    cp "$DEST_DIR/config.example.json" "$CONFIG_PATH"
    echo "[配置] 已生成 $CONFIG_PATH ，请编辑并填写 base_url / api_key / model"
else
    echo "[配置] $CONFIG_PATH 已存在，保留不动"
fi

# 3. 安装 SKILL.md 到 opencode
mkdir -p "$OPENCODE_SKILL_DIR"
cp "$SRC_DIR/SKILL.md" "$OPENCODE_SKILL_DIR/"
echo "[opencode] SKILL.md 已安装到 $OPENCODE_SKILL_DIR （重启 opencode 生效）"

# 4. 安装 image-vision-guard 插件到 opencode（工具层面兜底：拦截 read 图片失败并自动识别）
PLUGIN_DIR="$HOME/.config/opencode/plugin"
mkdir -p "$PLUGIN_DIR"
if [ -f "$SRC_DIR/plugin/image-vision-guard.ts" ]; then
    cp "$SRC_DIR/plugin/image-vision-guard.ts" "$PLUGIN_DIR/"
    echo "[opencode] 兜底插件已安装到 $PLUGIN_DIR"
fi

# 5. 安装 SKILL.md 到 Claude Code（如已安装）
if [ -d "$HOME/.claude" ]; then
    mkdir -p "$CLAUDE_SKILL_DIR"
    cp "$SRC_DIR/SKILL.md" "$CLAUDE_SKILL_DIR/"
    echo "[claude code] SKILL.md 已安装到 $CLAUDE_SKILL_DIR"
fi

# 6. 验证
echo ""
echo "== 验证 =="
python3 "$DEST_DIR/vision.py" --check

echo ""
echo "安装完成。下一步：编辑 $CONFIG_PATH 填入 API 参数，然后重启 opencode。"
