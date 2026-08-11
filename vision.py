#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""视觉代理脚本：调用任意 OpenAI 兼容视觉模型识别图片。

用法:
    python vision.py <图片路径> [<图片路径> ...] [-q "问题"]
    python vision.py --check    # 检查配置是否完整

配置来源:
    config.json（查找顺序：VISION_CONFIG 环境变量指定路径 → 脚本同目录 → ~/.config/image-vision/）
    不支持环境变量直接覆盖配置项，配置一律以 config.json 为准。

支持的提供商示例（任意 OpenAI 兼容服务均可）:
    OpenAI:            https://api.openai.com/v1
    DeepSeek:          https://api.deepseek.com/v1
    SiliconFlow:       https://api.siliconflow.cn/v1
    本地 vLLM/Ollama:  http://127.0.0.1:8000/v1 等
"""

import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_QUESTION = "请详细描述这些图片的内容，包括所有可见的文字信息。"

# 常见图片格式的 MIME 类型映射（Windows 上 mimetypes 对部分扩展名不可靠）
IMAGE_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".avif": "image/avif",
    ".svg": "image/svg+xml",
    ".tiff": "image/tiff",
    ".ico": "image/x-icon",
}

# 单张图片超过该大小（字节）时警告，部分 API 会拒绝过大的图片
MAX_IMAGE_BYTES = 20 * 1024 * 1024


def find_config_path() -> str:
    """确定配置路径：VISION_CONFIG 优先；其次按 脚本同目录 → ~/.config/image-vision/ 找第一个存在的；默认脚本同目录。"""
    env_path = os.environ.get("VISION_CONFIG")
    if env_path:
        return env_path
    candidates = [
        os.path.join(SCRIPT_DIR, "config.json"),
        os.path.join(os.path.expanduser("~"), ".config", "image-vision", "config.json"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return candidates[0]


CONFIG_PATH = find_config_path()


def load_config() -> dict:
    """加载配置：仅读取 config.json（或 VISION_CONFIG 指定的文件）。"""
    config = {}
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"错误：无法读取配置文件 {CONFIG_PATH}（{e}）", file=sys.stderr)
            sys.exit(1)

    config["base_url"] = str(config.get("base_url", "")).strip()
    config["api_key"] = str(config.get("api_key", "")).strip()
    config["model"] = str(config.get("model", "")).strip()
    try:
        config["timeout"] = int(config.get("timeout", 120))
    except (TypeError, ValueError):
        # 配置里 timeout 写成了非数字（如 "120s"）时回退默认值
        config["timeout"] = 120
    return config


def check_config(config: dict) -> None:
    """检查三项配置是否完整，缺失则给出中文提示。"""
    missing = [k for k in ("base_url", "api_key", "model") if not config.get(k)]
    if missing:
        names = {"base_url": "API Base URL", "api_key": "API Key", "model": "模型名称"}
        print(f"错误：缺少配置项：{', '.join(names[k] for k in missing)}")
        print(f"请在对话中提供这三项参数（模型会自动写入 {CONFIG_PATH}），"
              "或手动编辑该文件补全后重试")
        sys.exit(1)


def encode_image(path: str) -> str:
    """读取图片并转为 data URI（base64）。"""
    if not os.path.isfile(path):
        print(f"错误：图片文件不存在：{path}", file=sys.stderr)
        sys.exit(1)
    try:
        size = os.path.getsize(path)
    except OSError as e:
        print(f"错误：无法访问图片文件 {path}（{e}）", file=sys.stderr)
        sys.exit(1)
    if size > MAX_IMAGE_BYTES:
        print(f"警告：图片 {path} 约 {size // (1024 * 1024)}MB，超过 {MAX_IMAGE_BYTES // (1024 * 1024)}MB，"
              "部分 API 会拒绝，且读取会占用大量内存", file=sys.stderr)
    ext = os.path.splitext(path)[1].lower()
    mime = IMAGE_MIME.get(ext)
    if mime is None:
        mime, _ = mimetypes.guess_type(path)
    if mime is None or not mime.startswith("image/"):
        mime = "image/png"
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError as e:
        print(f"错误：无法读取图片文件 {path}（{e}）", file=sys.stderr)
        sys.exit(1)
    data = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{data}"


def call_vision(config: dict, image_paths: list, question: str) -> None:
    """向 OpenAI 兼容 API 发送图片识别请求，结果写入 stdout。"""
    check_config(config)

    base_url = config["base_url"].rstrip("/")
    url = f"{base_url}/chat/completions"
    content = [
        {"type": "text", "text": question},
        *[{"type": "image_url", "image_url": {"url": encode_image(p)}} for p in image_paths],
    ]
    payload = {
        "model": config["model"],
        "messages": [{"role": "user", "content": content}],
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['api_key']}",
        "User-Agent": config.get("user_agent") or "image-vision/1.0",
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=config["timeout"]) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"错误：API 返回 HTTP {e.code}：{body}", file=sys.stderr)
        sys.exit(1)
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"错误：无法连接 {url}（{e}）。请检查网络和 base_url 配置。", file=sys.stderr)
        sys.exit(1)

    try:
        text = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        print(f"错误：响应格式异常：{json.dumps(result, ensure_ascii=False)[:500]}", file=sys.stderr)
        sys.exit(1)

    if isinstance(text, list):
        text = "".join(part.get("text", "") for part in text if isinstance(part, dict))
    print(text)


def main() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(description="调用 OpenAI 兼容视觉模型识别图片")
    parser.add_argument("images", nargs="*", help="一个或多个图片文件路径")
    parser.add_argument("-q", "--question", default=DEFAULT_QUESTION, help="向模型提出的问题")
    parser.add_argument("--check", action="store_true", help="仅检查配置是否完整")
    parser.add_argument("--config-path", action="store_true", help="仅输出实际使用的配置文件路径")
    args = parser.parse_args()

    if args.config_path:
        print(CONFIG_PATH)
        return

    config = load_config()
    if args.check:
        check_config(config)
        print("配置检查通过。")
        return
    if not args.images:
        parser.error("请至少提供一个图片文件路径")

    call_vision(config, args.images, args.question)


if __name__ == "__main__":
    main()
