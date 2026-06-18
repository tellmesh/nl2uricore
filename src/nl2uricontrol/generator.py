from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


class MarkpactGenerationError(ValueError):
    """Raised when a Markpact cannot be generated from the request."""


@dataclass(frozen=True)
class GenerationRequest:
    prompt: str
    prefix: str
    pack_id: str | None = None
    version: str = "0.1.0"


def _slug(value: str) -> str:
    value = re.sub(r"[^0-9A-Za-z]+", "-", value.strip().lower()).strip("-")
    return value or "pack"


def _match_prefix_keywords(prefix: str, text: str, prefix_set: set[str], *text_kw: str) -> bool:
    return prefix in prefix_set or any(kw in text for kw in text_kw)


def _cap(
    prefix: str, cap_id: str, uri_tpl: str, kind: str, operation: str, *,
    side_effects: bool, approval: str,
) -> dict[str, Any]:
    return {
        "id": f"{prefix}.{cap_id}" if "." not in cap_id else cap_id,
        "uri": uri_tpl,
        "kind": kind,
        "operation": operation,
        "handler": f"markpact://self/python/{operation}",
        "side_effects": side_effects,
        "approval": approval,
    }


def _printer_caps(prefix: str, text: str) -> list[dict[str, Any]]:
    caps = [
        _cap(prefix, "status", f"{prefix}://{{device}}/query/status", "query", "status", side_effects=False, approval="not_required"),
        _cap(prefix, "nozzle_check", f"{prefix}://{{device}}/command/nozzle-check", "command", "nozzle_check", side_effects=True, approval="required"),
        _cap(prefix, "clean_head", f"{prefix}://{{device}}/command/clean-head", "command", "clean_head", side_effects=True, approval="required"),
    ]
    if "test" in text or "stron" in text:
        caps.append(
            _cap(prefix, "print_test_page", f"{prefix}://{{device}}/command/print-test-page", "command", "print_test_page", side_effects=True, approval="required")
        )
    return caps


def _usb_caps(prefix: str) -> list[dict[str, Any]]:
    return [
        _cap(prefix, "list_ports", f"{prefix}://host/{{host}}/query/ports", "query", "list_ports", side_effects=False, approval="not_required"),
        _cap(prefix, "port_status", f"{prefix}://port/{{port_id}}/query/status", "query", "port_status", side_effects=False, approval="not_required"),
        _cap(prefix, "enable_port", f"{prefix}://port/{{port_id}}/command/enable", "command", "enable_port", side_effects=True, approval="required"),
        _cap(prefix, "disable_port", f"{prefix}://port/{{port_id}}/command/disable", "command", "disable_port", side_effects=True, approval="required"),
    ]


def _browser_caps(prefix: str) -> list[dict[str, Any]]:
    return [
        _cap(prefix, "open_page", f"{prefix}://{{session}}/page/open", "command", "open_page", side_effects=True, approval="required"),
        _cap(prefix, "get_dom", f"{prefix}://{{session}}/page/dom", "query", "get_dom", side_effects=False, approval="not_required"),
    ]


def _cache_caps(prefix: str) -> list[dict[str, Any]]:
    return [
        _cap(prefix, "status", f"{prefix}://{{name}}/query/status", "query", "status", side_effects=False, approval="not_required"),
        _cap(prefix, "run", f"{prefix}://{{name}}/command/run", "command", "run", side_effects=True, approval="required"),
    ]


def _docker_caps(prefix: str) -> list[dict[str, Any]]:
    return [
        _cap(prefix, "status", f"{prefix}://container/{{name}}/query/status", "query", "status", side_effects=False, approval="not_required"),
        _cap(prefix, "restart", f"{prefix}://container/{{name}}/command/restart", "command", "restart", side_effects=True, approval="required"),
    ]


def _generic_caps(prefix: str) -> list[dict[str, Any]]:
    return [
        _cap(prefix, "status", f"{prefix}://{{resource}}/query/status", "query", "status", side_effects=False, approval="not_required"),
        _cap(prefix, "run", f"{prefix}://{{resource}}/command/run", "command", "run", side_effects=True, approval="required"),
    ]


_CAPABILITY_MATCHERS: list[tuple[tuple[str, ...], str | None]] = [
    (("printer", "print", "drukuj"), "printer"),
    (("usb", "usb"), None),
    (("browser", "web", "przegląd"), "browser"),
    (("cache", "cache"), "cache"),
    (("docker", "docker", "kontener"), "docker"),
]


def _infer_capabilities(prefix: str, prompt: str) -> list[dict[str, Any]]:
    text = prompt.lower()
    if _match_prefix_keywords(prefix, text, {"printer", "print"}, "druk", "printer"):
        return _printer_caps(prefix, text)
    if _match_prefix_keywords(prefix, text, {"usb"}, "usb", "port"):
        return _usb_caps(prefix)
    if _match_prefix_keywords(prefix, text, {"browser", "web"}, "browser", "przeglad"):
        return _browser_caps(prefix)
    if _match_prefix_keywords(prefix, text, {"cache"}, "cache"):
        return _cache_caps(prefix)
    if _match_prefix_keywords(prefix, text, {"docker"}, "docker", "kontener"):
        return _docker_caps(prefix)
    return _generic_caps(prefix)


def _handler_template(operation: str, prefix: str) -> str:
    if operation == "status":
        return f'''from __future__ import annotations


def handle(payload, context):
    variables = context.get("variables") or {{}}
    resource = variables.get("device") or variables.get("name") or variables.get("resource") or "default"
    return {{"ok": True, "resource": resource, "state": "ready", "scheme": "{prefix}", "mode": "mock" if context.get("environment") == "mock" else "real"}}
'''
    if operation in {"run", "restart", "enable_port", "disable_port", "nozzle_check", "clean_head", "print_test_page", "open_page"}:
        return f'''from __future__ import annotations


def handle(payload, context):
    variables = context.get("variables") or {{}}
    dry = bool(context.get("dry_run")) or context.get("environment") == "mock"
    return {{"ok": True, "operation": "{operation}", "variables": variables, "applied": not dry, "mode": "mock" if dry else "real"}}
'''
    if operation == "list_ports":
        return '''from __future__ import annotations


def handle(payload, context):
    host = (context.get("variables") or {}).get("host", "local")
    return {"ok": True, "host": host, "ports": [{"port_id": "1-1", "description": "Mock USB device"}], "count": 1, "mode": "mock"}
'''
    if operation == "port_status":
        return '''from __future__ import annotations


def handle(payload, context):
    port_id = (context.get("variables") or {}).get("port_id", "unknown")
    return {"ok": True, "port_id": port_id, "enabled": True, "mode": "mock"}
'''
    if operation == "get_dom":
        return '''from __future__ import annotations


def handle(payload, context):
    session = (context.get("variables") or {}).get("session", "default")
    return {"ok": True, "session": session, "html": "<html><body>Generated Markpact DOM</body></html>", "mode": "mock"}
'''
    return '''from __future__ import annotations


def handle(payload, context):
    return {"ok": True, "mode": "mock"}
'''


def _tests_block(prefix: str, capabilities: list[dict[str, Any]]) -> str:
    first_query = next((c for c in capabilities if c["kind"] == "query"), capabilities[0])
    uri = first_query["uri"].format(device="demo", host="local", port_id="1-1", session="default", name="demo", resource="demo")
    return f'''```yaml markpact:tests
tests:
  - id: generated_status
    uri: {uri}
    context:
      environment: real
    expect:
      ok: true
      operation: {first_query["operation"]}
```'''


def generate_markpact(request: GenerationRequest, *, use_llm: bool = False, model: str | None = None) -> str:
    if use_llm:
        raise MarkpactGenerationError(
            "LiteLLM generation is not configured in this environment. Use --no-llm for deterministic fallback."
        )

    prefix = _slug(request.prefix.replace("://", "").split("/")[0])
    if not prefix:
        raise MarkpactGenerationError("URI prefix is required.")

    pack_id = request.pack_id or f"uri{prefix}-markpact"
    capabilities = _infer_capabilities(prefix, request.prompt)
    operations = sorted({cap["operation"] for cap in capabilities})

    yaml_block = {
        "apiVersion": "urisys.io/v1",
        "kind": "UriPack",
        "metadata": {"id": pack_id, "version": request.version, "language": "python"},
        "description": f"Generated UriPack for {prefix}:// from NL prompt.",
        "schemes": [prefix],
        "capabilities": capabilities,
        "policy": {"default": "deny_mutations_without_approval"},
        "runtime": {"default_environment": "real", "supports": ["real", "local", "mock"]},
    }

    import yaml

    lines = [
        f"# UriPack Markpact: {pack_id}",
        "",
        f"Generated from prompt: {request.prompt.strip()}",
        "",
        "```yaml markpact:pack",
        yaml.safe_dump(yaml_block, sort_keys=False, allow_unicode=True).strip(),
        "```",
        "",
    ]

    for operation in operations:
        lines.extend(
            [
                f"```python markpact:handler id={operation}",
                _handler_template(operation, prefix).strip(),
                "```",
                "",
            ]
        )

    lines.append(_tests_block(prefix, capabilities))
    lines.append("")
    return "\n".join(lines)
