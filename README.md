# image-vision-skill

> 跨平台图片识别 Skill：当主模型不是多模态模型时，自动把图片交给任意 **OpenAI 兼容**视觉模型识别。

使用非多模态模型（如 DeepSeek、GLM、Kimi 等纯文本模型）时，遇到用户上传截图、报错图、设计稿，模型往往"看不到"图片。本项目提供一套跨平台方案：**Skill 指令 + 零依赖 Python 代理脚本**，主模型只需运行一条命令，即可把图片送入任意视觉大模型，获得识别结果并回答用户——使用者全程无感。

## 功能特性

- 🖼️ **任意 OpenAI 兼容视觉模型**：OpenAI、DeepSeek、通义千问 Qwen-VL、智谱 GLM-4V、SiliconFlow、本地 vLLM/Ollama 均可
- 🔄 **跨平台**：opencode / Claude Code / Codex / Z.ai zcode 通用（支持 skills 的平台直接加载，其余用指令文件兜底）
- ⚙️ **配置灵活**：`config.json` 或环境变量均可，换厂商/换模型只改配置不改代码
- 🐍 **零依赖**：纯 Python 标准库（urllib + base64），Python 3.7+ 即可运行
- 📦 **GitHub 远程加载**：opencode 用户一行配置自动安装，改版后自动更新

## 工作原理

```
用户上传图片
      ↓
主模型（非多模态，看不到图片）
      ↓ 自动加载 SKILL.md，运行:
python vision.py <图片路径> -q "<用户问题>"
      ↓
vision.py 读取配置 → base64 编码图片 → 请求 OpenAI 兼容 API
      ↓
视觉模型返回识别文本 → 主模型整合后回答用户
```

## 快速开始

### 方式一：opencode 远程加载（推荐）

在 `opencode.json`（全局 `~/.config/opencode/opencode.json` 或项目内）加入：

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

重启 opencode，自动拉取 skill 与脚本，无需手动复制文件。

### 方式二：git clone + 一键脚本（所有平台通用）

```bash
git clone https://github.com/wangxintai929/image-vision-skill.git
cd image-vision-skill
./install.sh          # macOS / Linux
# Windows: powershell -ExecutionPolicy Bypass -File install.ps1
```

脚本自动完成：复制脚本到 `~/.config/image-vision/`、生成配置模板、把 `SKILL.md` 安装到 opencode 与 Claude Code 的 skills 目录。

### 方式三：手动安装

下载 ZIP 解压，或 clone 后手动把 `SKILL.md` 复制到各平台 skills 目录（详见下文"平台支持"）。

## 配置

> **推荐：通过对话配置。** 装好 skill 后，直接在对话中告诉模型三项参数即可（如"视觉模型用 OpenAI 的 gpt-4o，key 是 sk-xxx，base_url 是 https://api.openai.com/v1"），模型会自动写入 `config.json` 并验证。

首次使用也可手动编辑配置，三项默认均为空，由你填写：

```bash
cd ~/.config/image-vision
cp config.example.json config.json
```

```json
{
  "base_url": "https://api.openai.com/v1",
  "api_key": "sk-...",
  "model": "gpt-4o",
  "timeout": 120,
  "user_agent": ""
}
```

| 字段 | 说明 | 示例 |
|---|---|---|
| `base_url` | API 基础地址（不含 /chat/completions） | `https://api.openai.com/v1`、`https://api.deepseek.com/v1`、`http://127.0.0.1:8000/v1`（本地 vLLM） |
| `api_key` | 你的 API 密钥 | `sk-...` |
| `model` | 视觉模型名称 | `gpt-4o`、`qwen2.5-vl-72b-instruct`、`glm-4v` |
| `timeout` | 请求超时秒数（默认 120） | `120` |
| `user_agent` | 自定义 User-Agent（可选，个别服务需要） | 留空 |

配置只读 `config.json` 一个文件，不读取环境变量；`VISION_CONFIG` 环境变量仅用于指定该文件的位置（可选）。

### 示例：opencode-go（无需额外注册）

若你已登录 opencode 的 opencode-go 提供商，key 位于 `~/.local/share/opencode/auth.json`：

```json
{
  "base_url": "https://opencode.ai/zen/go/v1",
  "api_key": "（你的 opencode-go key）",
  "model": "qwen3.7-plus"
}
```

可选视觉模型：`mimo-v2.5`（最便宜）、`gpt-5.6-luna`（支持 PDF）、`kimi-k2.6`、`qwen3.8-max` 等（opencode-go 按量计费）。

## 使用示例

在任意支持的工具中上传一张图片，提问：

```
用户：这张报错截图是什么意思？
```

主模型自动执行 `python vision.py <截图路径> -q "这张报错截图是什么意思？"`，视觉模型识别后，主模型结合结果给出解答。

命令行直接调用：

```bash
python ~/.config/image-vision/vision.py "design.png" -q "这个页面的配色方案是什么？"
# 支持多张图片
python ~/.config/image-vision/vision.py "a.png" "b.png" -q "两张图的区别是什么？"
```

## 平台支持

| 平台 | 安装方式 |
|---|---|
| opencode | `skills.urls` 远程加载，或复制到 `~/.config/opencode/skills/image-vision/`；另装兜底插件（`plugin/image-vision-guard.ts` → `~/.config/opencode/plugin/`），工具层面拦截 read 图片失败并自动识别，不依赖模型自觉 |
| Claude Code | 复制到 `~/.claude/skills/image-vision/SKILL.md`（支持 AskUserQuestion 填空配置） |
| Codex | 无 SKILL.md 机制：在全局 `~/.codex/AGENTS.md` 追加"遇到图片运行 vision.py"指引（无填空工具，对话式提问） |
| Z.ai zcode | 复制到 `~/.zcode/skills/image-vision/SKILL.md` 或 `~/.agents/skills/`（不扫 ~/.claude/skills/；支持 AskUserQuestion 填空配置） |

## 验证

```bash
# 配置检查
python ~/.config/image-vision/vision.py --check

# 真实识别测试
python ~/.config/image-vision/vision.py "test.png" -q "图片里有什么？"
```

预期：`--check` 提示配置通过；识别测试输出图片内容的文字描述。

## 更新

- **远程加载（方式一）**：仓库更新后，需将 `index.json` 中 `version` 递增，opencode 重启后自动拉取新版
- **脚本安装（方式二/三）**：重新 clone 后运行安装脚本即可（不覆盖已有 `config.json`）

## 常见问题

- **缺少配置项** → 补全 `config.json` 或设置环境变量
- **无法连接** → 检查网络与 `base_url`（本地服务需先启动）
- **HTTP 4xx** → 多为密钥无效或模型名错误，按 API 返回信息排查
- **换模型/换厂商** → 只改 `config.json`，无需改任何代码

## 仓库结构

```
image-vision-skill/
├── SKILL.md               # 技能指令（各平台共用）
├── vision.py              # 视觉代理脚本（Python 3.7+，零依赖）
├── config.example.json    # 配置模板
├── index.json             # opencode 远程加载索引
├── plugin/               # opencode 兜底插件（自动拦截 read 图片失败并识别）
├── install.ps1            # Windows 一键安装脚本
├── install.sh             # macOS/Linux 一键安装脚本
└── install.md             # 详细安装说明
```

## 许可证

MIT License
