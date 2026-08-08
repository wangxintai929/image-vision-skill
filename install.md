# image-vision 安装说明

一个跨平台（opencode / Claude Code / Codex / Z.ai zcode）的图片识别 skill：当主模型不是多模态模型、无法直接查看图片时，自动调用视觉代理脚本，把图片交给任意 **OpenAI 兼容**视觉模型识别。

- GitHub 仓库：`https://github.com/wangxintai929/image-vision-skill`
- 依赖：Python 3.7+（脚本零第三方依赖）

## 一、目录结构

```
image-vision/
├── SKILL.md               # 技能指令（各平台共用）
├── vision.py              # 视觉代理脚本（Python 3.7+，零第三方依赖）
├── config.example.json    # 配置模板（首次安装时复制为 config.json 并填写）
├── index.json             # opencode 远程加载索引
├── plugin/               # opencode 兜底插件（自动拦截 read 图片失败并识别）
├── install.ps1            # Windows 一键安装脚本
├── install.sh             # macOS/Linux 一键安装脚本
└── install.md             # 本文件
```

## 二、安装方式（三选一）

### 方式一：opencode 远程加载（一行配置，推荐 opencode 用户）

在 `opencode.json`（全局 `~/.config/opencode/opencode.json` 或项目 `./opencode.json`）中加入：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "skills": {
    "urls": [
      "https://cdn.jsdelivr.net/gh/wangxintai929/image-vision-skill@main/"
    ]
  }
}
```

重启 opencode 后自动从 GitHub 拉取 skill（含 vision.py 脚本），无需手动复制文件。

> 技能内容更新后，需同步修改 `index.json` 中的 `version` 字段，opencode 才会重新拉取。

### 方式二：git clone + 一键脚本（所有平台通用）

```bash
git clone https://github.com/wangxintai929/image-vision-skill.git
cd image-vision
./install.sh          # macOS/Linux；Windows 用: powershell -ExecutionPolicy Bypass -File install.ps1
```

脚本自动完成：复制脚本到 `~/.config/image-vision/`、生成 `config.json`、把 `SKILL.md` 装到 opencode 与 Claude Code 的 skills 目录、执行配置检查。

### 方式三：手动安装

1. 下载仓库（`Code` → `Download ZIP`）并解压，或 `git clone`
2. 按下方"四、首次配置"和"五、按平台安装 skill 指令"手动操作

## 三、统一安装目录（方式二/三）

脚本和配置固定放在统一目录，各平台共用同一份：

- Windows: `%USERPROFILE%\.config\image-vision\`
- macOS/Linux: `~/.config/image-vision/`

## 四、首次配置（三项均为空，由你填写）

> **推荐：通过对话配置。** 装好 skill 后直接在对话中告诉模型 `base_url` / `api_key` / `model`（如"视觉模型用 OpenAI 的 gpt-4o，key 是 sk-xxx"），模型会自动写入配置文件并运行 `--check` 验证，无需手动编辑。

也可以手动编辑（脚本位置 `~/.config/image-vision/config.json`）：

```bash
cd ~/.config/image-vision
cp config.example.json config.json
```

编辑 `config.json`，填入你的视觉模型参数（任意 OpenAI 兼容服务均可）：

| 字段 | 说明 | 示例 |
|---|---|---|
| `base_url` | API 基础地址（不含 /chat/completions） | `https://api.openai.com/v1`、`https://api.deepseek.com/v1`、`https://api.siliconflow.cn/v1`、本地 vLLM `http://127.0.0.1:8000/v1` |
| `api_key` | 你的 API 密钥 | `sk-...` |
| `model` | 视觉模型名称 | `gpt-4o`、`qwen2.5-vl-72b-instruct`、`glm-4v` 等 |
| `timeout` | 请求超时（秒，默认 120） | `120` |
| `user_agent` | 自定义 User-Agent（可选，个别服务需要） | 留空即可 |

> 配置只读 `config.json` 一个文件（`VISION_CONFIG` 环境变量仅用于指定该文件位置，可选），不读取其他环境变量。

### 开箱即用示例：opencode-go（无需额外注册）

若你已登录 opencode 的 opencode-go 提供商（`opencode-go` 的 key 位于 `~/.local/share/opencode/auth.json`），可直接填入：

```json
{
  "base_url": "https://opencode.ai/zen/go/v1",
  "api_key": "（你的 opencode-go key）",
  "model": "qwen3.7-plus"
}
```

其他可选视觉模型：`mimo-v2.5`（最便宜）、`gpt-5.6-luna`（支持 PDF）、`kimi-k2.6`、`qwen3.8-max` 等。注意 opencode-go 按量计费。

## 五、按平台安装 skill 指令（方式二/三）

### opencode
```bash
mkdir -p ~/.config/opencode/skills
cp -r image-vision ~/.config/opencode/skills/image-vision   # 或仅复制 SKILL.md
# 重启 opencode 生效
```

### Claude Code
```bash
mkdir -p ~/.claude/skills
cp image-vision/SKILL.md ~/.claude/skills/image-vision/SKILL.md
```

支持完整功能：`AskUserQuestion` 填空配置、Bash 执行脚本、CLAUDE.md 全局指令。

### Codex（OpenAI Codex CLI）
Codex 无 SKILL.md 机制，使用全局指令文件兜底。在 `~/.codex/AGENTS.md` 中追加：

```markdown
当用户上传/引用图片且你无法直接查看图片时，运行：
python ~/.config/image-vision/vision.py "<图片路径>" -q "<用户问题>"
并以脚本输出回答用户。
```

注意：Codex 无结构化填空工具，配置参数时直接在回复中列出 `base_url` / `api_key` / `model` 请用户回复。

### Z.ai zcode CLI
```bash
mkdir -p ~/.zcode/skills
cp image-vision/SKILL.md ~/.zcode/skills/image-vision/SKILL.md   # 或放入 ~/.agents/skills/（跨工具兼容目录）
```

注意：zcode **不扫描** `~/.claude/skills/`，必须放入上述目录。支持完整功能：`AskUserQuestion` 填空配置（上限 4 题）、Bash 执行脚本、全局指令文件为 `~/.zcode/AGENTS.md`（兜底指引追加到此处）。

## 六、验证

```bash
# 1. 配置检查
python ~/.config/image-vision/vision.py --check

# 2. 真实识别测试（用一张含文字的图片）
python ~/.config/image-vision/vision.py "C:\path\to\test.png" -q "图片里有什么？"
```

预期：`--check` 提示配置通过；识别测试在 stdout 输出图片内容的文字描述。

## 七、常见问题

- **缺少配置项**：通过对话提供 `base_url` / `api_key` / `model`，或手动编辑 `config.json`。
- **无法连接**：检查网络与 `base_url` 是否正确（本地服务需先启动）。
- **HTTP 4xx**：多为密钥无效或模型名错误，按 API 返回的错误信息排查。
- **换模型/换厂商**：改 `config.json` 三项即可，无需改任何代码。
- **更新技能**：重新 clone/下载后运行安装脚本即可；改 `index.json` 版本号后 opencode 远程加载会自动更新。
