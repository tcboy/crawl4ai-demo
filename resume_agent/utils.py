from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ValidationError


def load_env() -> None:
    # 支持 .env（本地开发）
    load_dotenv(override=False)


class OpenAIJsonError(RuntimeError):
    pass


def openai_structured_parse(
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    json_schema_hint: str,
    temperature: float = 0.0,
    api_key_env: str = "OPENAI_API_KEY",
) -> Dict[str, Any]:
    """
    仅用于 JD 结构化：要求返回 JSON object。
    失败时抛异常，调用方可降级到确定性规则解析。
    """
    load_env()
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise OpenAIJsonError(f"缺少环境变量 {api_key_env}，无法调用 OpenAI 结构化 JD")

    client = OpenAI(api_key=api_key)
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": user_prompt
            + "\n\n你必须只输出一个 JSON 对象（不要 markdown）。\n"
            + "JSON Schema 参考（非严格校验，仅提示字段）：\n"
            + json_schema_hint,
        },
    ]
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or ""
        data = json.loads(content)
        if not isinstance(data, dict):
            raise OpenAIJsonError("OpenAI 返回非 JSON object")
        return data
    except Exception as e:  # noqa: BLE001 - 需要包装所有异常
        raise OpenAIJsonError(f"OpenAI 结构化失败：{e}") from e


def parse_with_pydantic(model_cls: type[BaseModel], data: Dict[str, Any]) -> BaseModel:
    try:
        return model_cls.model_validate(data)
    except ValidationError as e:
        raise OpenAIJsonError(f"Pydantic 校验失败：{e}") from e

