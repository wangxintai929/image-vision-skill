import type { Plugin } from "@opencode-ai/plugin"
import fs from "node:fs"
import os from "node:os"
import path from "node:path"

const IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg", ".ico"]

const DEBUG_LOG = path.join(os.homedir(), ".config", "image-vision", "plugin-debug.log")

function log(message: string): void {
  try {
    fs.appendFileSync(DEBUG_LOG, `[${new Date().toISOString()}] ${message}\n`)
  } catch {
    // 忽略日志写入失败
  }
}

function isImagePath(filePath: string): boolean {
  return IMAGE_EXTENSIONS.includes(path.extname(filePath).toLowerCase())
}

/**
 * image-vision 兜底插件（opencode）
 *
 * 当主模型不支持图片输入时，read 图片会失败（报错 "does not support image input"）。
 * 本插件拦截该失败：自动执行 vision.py 调用外部视觉模型识别图片，
 * 并把识别文本改写成 read 工具的输出——模型视角下 read "成功"，
 * 直接基于内容回答，全程无感，且不依赖模型是否遵守技能指令。
 */
export default (async ({ $ }) => {
  log("插件已加载")
  return {
    "tool.execute.after": async (
      input: { tool: string; args: any },
      output: { title: string; output: string },
    ) => {
      log(`hook 触发: tool=${input.tool} args=${JSON.stringify(input.args ?? {})} output=${(output.output || output.title || "").slice(0, 120)}`)
      if (input.tool !== "read") return

      const text = output.output || output.title || ""
      if (!/does not support image input/i.test(text)) return

      const args = input.args ?? {}
      const filePath =
        typeof args.filePath === "string"
          ? args.filePath
          : typeof args.path === "string"
            ? args.path
            : undefined
      if (!filePath || !isImagePath(filePath)) return

      // 定位视觉代理脚本（统一安装目录 ~/.config/image-vision/vision.py）
      const visionScript = path.join(os.homedir(), ".config", "image-vision", "vision.py")

      // 执行视觉识别（Windows/Linux/macOS 通用，使用默认问题）
      const proc = await $`python ${visionScript} ${filePath}`.quiet().nothrow()
      const stdout = proc.stdout?.toString("utf8")?.trim() || ""
      const stderr = proc.stderr?.toString("utf8")?.trim() || ""
      log(`vision.py 退出码=${proc.exitCode} stdout=${stdout.slice(0, 120)} stderr=${stderr.slice(0, 120)}`)

      if (proc.exitCode === 0 && stdout) {
        output.title = "图片识别结果（image-vision）"
        output.output = stdout
      } else {
        output.output = `图片识别失败：${stderr || stdout || "vision.py 执行失败（请检查安装与配置）"}`
      }
    },
  }
}) satisfies Plugin
