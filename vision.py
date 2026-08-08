#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""视觉代理脚本：调用任意 OpenAI 兼容视觉模型识别图片。

用法:
    python vision.py <图片路径> [<图片路径> ...] [-q "问题"]
    python vision.py --check    # 检查配置是否完整

配置来源（优先级从高到低）:
    1. 环境变量  VISION_BASE_URL / VISION_API_KEY / VISION_MODEL
    2. 环境变量  VISION_CONFIG 指定的配置文件
    3. 本目录下的 config.json（用户首次安装时填写，见 config.example.json）

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
CONFIG_PATH = os.environ.get("VISION_CONFIG") or os.path.join(SCRIPT_DIR, "config.json")
DEFAULT_QUESTION = "请详细描述这些图片的内容，包括所有可见的文字信息。"


def load_config() -> dict:
    """加载配置：config.json 为基础，环境变量优先覆盖。"""
    config = {}
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"错误：无法读取配置文件 {CONFIG_PATH}（{e}）", file=sys.stderr)
            sys.exit(1)

    config["base_url"] = os.environ.get("VISION_BASE_URL", config.get("base_url", "")).strip()
    config["api_key"] = os.environ.get("VISION_API_KEY", config.get("api_key", "")).strip()
    config["model"] = os.environ.get("VISION_MODEL", config.get("model", "")).strip()
    config["timeout"] = config.get("timeout", 120)
    return config


def check_config(config: dict) -> None:
    """检查三项配置是否完整，缺失则给出中文提示。"""
    missing = [k for k in ("base_url", "api_key", "model") if not config.get(k)]
    if missing:
        names = {"base_url": "API Base URL", "api_key": "API Key", "model": "模型名称"}
        print(f"错误：缺少配置项：{', '.join(names[k] for k in missing)}")
        print(f"请编辑 {CONFIG_PATH} 补全后重试，或设置环境变量 "
              "VISION_BASE_URL / VISION_API_KEY / VISION_MODEL")
        sys.exit(1)


def encode_image(path: str) -> str:
    """读取图片并转为 data URI（base64）。"""
    if not os.path.isfile(path):
        print(f"错误：图片文件不存在：{path}", file=sys.stderr)
        sys.exit(1)
    mime, _ = mimetypes.guess_type(path)
    if mime is None or not mime.startswith("image/"):
        mime = "image/png"
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
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
        "User-Agent": config.get("user_agent") or "opencode/1.18.15",
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
    args = parser.parse_args()

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
