import type { Plugin } from "@opencode-ai/plugin"
import fs from "node:fs"
import os from "node:os"
import path from "node:path"

const DEBUG_LOG = path.join(os.homedir(), ".config", "image-vision", "plugin-debug.log")

function log(message: string): void {
  try {
    fs.appendFileSync(DEBUG_LOG, `[${new Date().toISOString()}] ${message}\n`)
  } catch {
    // 忽略日志写入失败
  }
}

/**
 * image-vision 兜底插件（opencode）
 *
 * 机制：在每次请求发给模型前，检查用户消息中的图片附件（type=file, mime=image/*），
 * 把图片的本地路径和处置规则以文本形式注入用户消息——模型必然看到真实路径，
 * 不会再自行搜索其他图片代替；路径不存在时则明确提醒用户先保存到本地。
 * 该方案与模型是否遵守 SKILL.md 无关（指令注入在机制层完成）。
 */
export default (async () => {
  log("插件已加载")
  return {
    "experimental.chat.messages.transform": async (
      _input: {},
      output: {
        messages: {
          info: { role?: string }
          parts: any[]
        }[]
      },
    ) => {
      // 从后向前找最新一条用户消息
      for (let i = output.messages.length - 1; i >= 0; i--) {
        const message = output.messages[i]
        if (message.info.role !== "user") continue

        const imageParts = message.parts.filter(
          (part) =>
            part.type === "file" &&
            typeof part.mime === "string" &&
            part.mime.startsWith("image/"),
        )
        if (imageParts.length === 0) continue

        const paths = imageParts
          .map((part) => (typeof part.filename === "string" ? part.filename : ""))
          .filter((value) => value.length > 0)
        if (paths.length === 0) continue

        const pathList = paths.join("、")
        const injection =
          `【系统注入·image-vision】检测到用户上传了 ${paths.length} 张图片，路径：${pathList}。` +
          "当前模型不支持图片输入，必须遵守：1) 禁止用 read/编辑工具直接读取这些图片文件（会报错）；" +
          `2) 若路径在本地存在，先定位视觉代理脚本 vision.py：优先使用当前 skill 自带的脚本（即 SKILL.md 同目录的 vision.py，按 skill 文件列表路径确认）；若无法确认 skill 自带脚本位置，再检查 ~/.config/image-vision/vision.py 是否存在，存在则用之；都找不到才用搜索工具（glob）定位。然后执行 python "<vision.py 绝对路径>" ${paths.map((p) => `"${p}"`).join(" ")} -q "<用户问题原文>"（图片路径务必加双引号，Windows 下 python 不可用时尝试 py），并以脚本输出作为图片内容回答用户，不做解释；` +
          "3) 若某个路径在本地不存在（图片未保存到磁盘），明确提醒用户“请先将图片保存到本地（如桌面），保存后把路径发我”，禁止搜索或用其他图片代替。"

        // 优先追加到用户消息的文本部分；无文本部分则新增一条
        const textPart = message.parts.find(
          (part) => part.type === "text" && typeof part.text === "string",
        )
        if (textPart) {
          textPart.text += "\n\n" + injection
        } else {
          message.parts.push({ type: "text", text: injection, id: "image-vision-injection" })
        }
        log(`已注入图片路径: ${pathList}`)
        break
      }
    },
  }
}) satisfies Plugin
