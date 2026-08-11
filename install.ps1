# image-vision 一键安装脚本（Windows / PowerShell 5.1+）
# 用法: powershell -ExecutionPolicy Bypass -File install.ps1
# 安装位置: %USERPROFILE%\.config\image-vision\（脚本与配置）
#          %USERPROFILE%\.config\opencode\skills\image-vision\SKILL.md（opencode）

$ErrorActionPreference = "Stop"

$UserHome = $HOME
$SrcDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DestDir = Join-Path $UserHome ".config\image-vision"
$OpencodeSkillDir = Join-Path $UserHome ".config\opencode\skills\image-vision"
$ClaudeSkillDir = Join-Path $UserHome ".claude\skills\image-vision"

Write-Host "== 安装 image-vision =="

# 1. 复制脚本与配置模板到统一安装目录
New-Item -ItemType Directory -Path $DestDir -Force | Out-Null
Copy-Item (Join-Path $SrcDir "vision.py") $DestDir -Force
Copy-Item (Join-Path $SrcDir "config.example.json") $DestDir -Force
Copy-Item (Join-Path $SrcDir "SKILL.md") $DestDir -Force

# 2. 首次安装时生成 config.json（存在则保留，不覆盖用户配置）
$ConfigPath = Join-Path $DestDir "config.json"
if (-not (Test-Path $ConfigPath)) {
    Copy-Item (Join-Path $DestDir "config.example.json") $ConfigPath
    Write-Host "[配置] 已生成 $ConfigPath ，可直接通过对话提供 base_url / api_key / model，由模型写入"
} else {
    Write-Host "[配置] $ConfigPath 已存在，保留不动"
}

# 3. 安装 SKILL.md 到 opencode
New-Item -ItemType Directory -Path $OpencodeSkillDir -Force | Out-Null
Copy-Item (Join-Path $SrcDir "SKILL.md") $OpencodeSkillDir -Force
Write-Host "[opencode] SKILL.md 已安装到 $OpencodeSkillDir （重启 opencode 生效）"

# 4. 安装 image-vision-guard 插件到 opencode（工具层面兜底：拦截 read 图片失败并自动识别）
$PluginDir = Join-Path $UserHome ".config\opencode\plugin"
New-Item -ItemType Directory -Path $PluginDir -Force | Out-Null
if (Test-Path (Join-Path $SrcDir "plugin\image-vision-guard.ts")) {
    Copy-Item (Join-Path $SrcDir "plugin\image-vision-guard.ts") $PluginDir -Force
    Write-Host "[opencode] 兜底插件已安装到 $PluginDir"
}

# 5. 安装 SKILL.md 到 Claude Code（如已安装）
if (Test-Path (Join-Path $UserHome ".claude")) {
    New-Item -ItemType Directory -Path $ClaudeSkillDir -Force | Out-Null
    Copy-Item (Join-Path $SrcDir "SKILL.md") $ClaudeSkillDir -Force
    Write-Host "[claude code] SKILL.md 已安装到 $ClaudeSkillDir"
}

# 5b. 安装 SKILL.md 到 Z.ai zcode
$ZcodeSkillDir = Join-Path $UserHome ".zcode\skills\image-vision"
New-Item -ItemType Directory -Path $ZcodeSkillDir -Force | Out-Null
Copy-Item (Join-Path $SrcDir "SKILL.md") $ZcodeSkillDir -Force
Write-Host "[zcode] SKILL.md 已安装到 $ZcodeSkillDir"

# 5c. Codex 无 SKILL.md 机制：向 ~/.codex/AGENTS.md 追加兜底指引（已存在则不重复）
$CodexDir = Join-Path $UserHome ".codex"
if (Test-Path $CodexDir) {
    $CodexAgents = Join-Path $CodexDir "AGENTS.md"
    if (-not (Test-Path $CodexAgents)) { New-Item -ItemType File -Path $CodexAgents -Force | Out-Null }
    $CodexContent = Get-Content $CodexAgents -Raw -ErrorAction SilentlyContinue
    if ($CodexContent -notmatch "(?m)^## image-vision") {
        $CodexText = @"

## image-vision（图片识别兜底）
当用户上传/引用图片且你无法直接查看图片时，运行：
python ~/.config/image-vision/vision.py "<图片路径>" -q "<用户问题>"
并以脚本输出回答用户。
"@
        Add-Content -Path $CodexAgents -Value $CodexText -Encoding UTF8
        Write-Host "[codex] 已追加 image-vision 指引到 $CodexAgents"
    } else {
        Write-Host "[codex] $CodexAgents 已包含 image-vision 指引，跳过"
    }
} else {
    Write-Host "[codex] 未检测到 .codex 目录，跳过（需要时按 install.md 手动追加指引）"
}

# 6. 验证
Write-Host ""
Write-Host "== 验证 =="
python (Join-Path $DestDir "vision.py") --check

Write-Host ""
Write-Host "安装完成。重启 opencode 后，直接在对话中提供视觉模型参数即可完成配置。"
