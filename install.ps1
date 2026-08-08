# image-vision 一键安装脚本（Windows / PowerShell 5.1+）
# 用法: powershell -ExecutionPolicy Bypass -File install.ps1
# 安装位置: %USERPROFILE%\.config\image-vision\（脚本与配置）
#          %USERPROFILE%\.config\opencode\skills\image-vision\SKILL.md（opencode）

$ErrorActionPreference = "Stop"

$Home = $env:USERPROFILE
$SrcDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DestDir = Join-Path $Home ".config\image-vision"
$OpencodeSkillDir = Join-Path $Home ".config\opencode\skills\image-vision"
$ClaudeSkillDir = Join-Path $Home ".claude\skills\image-vision"

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
    Write-Host "[配置] 已生成 $ConfigPath ，请编辑并填写 base_url / api_key / model"
} else {
    Write-Host "[配置] $ConfigPath 已存在，保留不动"
}

# 3. 安装 SKILL.md 到 opencode
New-Item -ItemType Directory -Path $OpencodeSkillDir -Force | Out-Null
Copy-Item (Join-Path $SrcDir "SKILL.md") $OpencodeSkillDir -Force
Write-Host "[opencode] SKILL.md 已安装到 $OpencodeSkillDir （重启 opencode 生效）"

# 4. 安装 SKILL.md 到 Claude Code（如已安装）
if (Test-Path (Join-Path $Home ".claude")) {
    New-Item -ItemType Directory -Path $ClaudeSkillDir -Force | Out-Null
    Copy-Item (Join-Path $SrcDir "SKILL.md") $ClaudeSkillDir -Force
    Write-Host "[claude code] SKILL.md 已安装到 $ClaudeSkillDir"
}

# 5. 验证
Write-Host ""
Write-Host "== 验证 =="
python (Join-Path $DestDir "vision.py") --check

Write-Host ""
Write-Host "安装完成。下一步：编辑 $ConfigPath 填入 API 参数，然后重启 opencode。"
