import type { Plugin } from "@opencode-ai/plugin"
import crypto from "node:crypto"
import fs from "node:fs"
import os from "node:os"
import path from "node:path"

const DEBUG_LOG = path.join(os.homedir(), ".config", "image-vision", "plugin-debug.log")
// 粘贴图片缓存目录：opencode 粘贴的图片只有 base64（url 字段），filename 常为无效路径，
// 插件将 base64 解码写入该目录，得到 vision.py 可读的本地文件
const CACHE_DIR = path.join(os.homedir(), ".config", "image-vision", "cache")

// 单张粘贴图片 base64 解码上限（约 50MB），防止超大附件耗尽内存/磁盘
const MAX_CACHE_BYTES = 50 * 1024 * 1024
// 缓存文件保留天数，超出后清理，防止无限积累占用磁盘
const CACHE_RETENTION_DAYS = 30

const MIME_EXT: Record<string, string> = {
  "image/png": ".png",
  "image/jpeg": ".jpg",
  "image/webp": ".webp",
  "image/gif": ".gif",
  "image/bmp": ".bmp",
  "image/avif": ".avif",
}

// 常见图片格式的魔数（文件头），用于校验解码结果确为图片
const MAGIC_BYTES: [number[], string][] = [
  [[0x89, 0x50, 0x4e, 0x47], "png"],
  [[0xff, 0xd8, 0xff], "jpg"],
  [[0x52, 0x49, 0x46, 0x46], "webp"],
  [[0x47, 0x49, 0x46, 0x38], "gif"],
  [[0x42, 0x4d], "bmp"],
]

function extFromMime(mime: string): string {
  return MIME_EXT[mime] || ".png"
}

/** 校验 buffer 是否以已知图片格式的魔数开头 */
function isImageBuffer(buffer: Buffer): boolean {
  return MAGIC_BYTES.some(([magic]) =>
    magic.every((byte, i) => buffer[i] === byte),
  )
}

/** 清理超过保留天数的缓存文件（每次注入前调用，保持目录有界） */
function cleanCache(): void {
  try {
    if (!fs.existsSync(CACHE_DIR)) return
    const deadline = Date.now() - CACHE_RETENTION_DAYS * 24 * 60 * 60 * 1000
    for (const name of fs.readdirSync(CACHE_DIR)) {
      if (!name.startsWith("paste-")) continue
      const filePath = path.join(CACHE_DIR, name)
      const stat = fs.statSync(filePath)
      if (stat.isFile() && stat.mtimeMs < deadline) fs.unlinkSync(filePath)
    }
  } catch {
    // 清理失败不影响主流程
  }
}

/** 将 data URI（data:image/png;base64,...）解码为本地缓存文件，返回文件路径；失败返回 null */
function cacheDataUri(url: string, mime: string): string | null {
  const match = /^data:image\/[a-zA-Z0-9.+-]+;base64,(.+)$/s.exec(url)
  if (!match) return null
  try {
    if (match[1].length > MAX_CACHE_BYTES * 1.5) return null // base64 长度上限，提前拒绝超大附件
    const buffer = Buffer.from(match[1], "base64")
    if (buffer.length === 0 || buffer.length > MAX_CACHE_BYTES) return null
    if (!isImageBuffer(buffer)) return null // 解码结果不是有效图片，丢弃
    fs.mkdirSync(CACHE_DIR, { recursive: true })
    cleanCache()
    const hash = crypto.createHash("md5").update(buffer).digest("hex").slice(0, 8)
    const filePath = path.join(CACHE_DIR, `paste-${Date.now()}-${hash}${extFromMime(mime)}`)
    fs.writeFileSync(filePath, buffer)
    return filePath
  } catch {
    return null
  }
}

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

        // 为每个图片 part 解析出可用的本地路径：
        // 1) filename 是绝对路径且文件真实存在 → 直接用
        // 2) 否则 url（data URI）解码写入缓存目录 → 用缓存路径
        // 3) 都没有 → 该图无法处理
        const paths = imageParts
          .map((part) => {
            const filename = typeof part.filename === "string" ? part.filename : ""
            if (filename && path.isAbsolute(filename) && fs.existsSync(filename)) {
              return filename
            }
            const url = typeof (part as { url?: unknown }).url === "string"
              ? (part as { url: string }).url
              : ""
            if (url) {
              const cached = cacheDataUri(url, part.mime)
              if (cached) {
                log(`已缓存粘贴图片: ${cached}`)
                return cached
              }
              log(`粘贴图片缓存失败（url=${url.slice(0, 60)}...）`)
            }
            return ""
          })
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
