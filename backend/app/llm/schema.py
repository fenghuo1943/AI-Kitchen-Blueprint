"""Anthropic 结构化输出 JSON Schema 清洗。

Anthropic 的 output_config.format(json_schema) 不支持部分 JSON Schema 关键字
（minLength/maxLength/minimum/maximum/multipleOf/pattern 等），否则返回 400；
且要求 object 必须带 additionalProperties: false。这里递归删除不支持的约束，
并强制 object 的 additionalProperties=false。$ref/$defs 官方支持，予以保留。
"""
from typing import Any

_UNSUPPORTED_KEYS = {
    "minLength", "maxLength", "minimum", "maximum", "multipleOf",
    "pattern", "minItems", "maxItems", "uniqueItems",
}


def sanitize_schema_for_anthropic(schema: Any) -> Any:
    """递归清洗 JSON Schema，返回新对象（不修改入参）。"""
    if isinstance(schema, dict):
        cleaned: dict = {}
        for key, value in schema.items():
            if key in _UNSUPPORTED_KEYS:
                continue
            cleaned[key] = sanitize_schema_for_anthropic(value)
        if schema.get("type") == "object":
            cleaned["additionalProperties"] = False
        return cleaned
    if isinstance(schema, list):
        return [sanitize_schema_for_anthropic(item) for item in schema]
    return schema
