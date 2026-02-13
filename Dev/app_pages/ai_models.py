"""AI Models page - provider/model/key management and connectivity check."""

from __future__ import annotations

import os
from contextlib import contextmanager

import streamlit as st

from app_pages.shared import load_main_config, save_main_config, upsert_env_var, snapshot_configs


ANTHROPIC_MODELS = [
    "claude-opus-4-6",
    "claude-opus-4-1",
    "claude-sonnet-4-0",
    "claude-3-7-sonnet-latest",
]

OPENAI_MODELS = [
    "gpt-4.1",
    "gpt-4o",
    "gpt-4o-mini",
]


@contextmanager
def _proxy_context(use_system_proxy: bool):
    if use_system_proxy:
        yield
        return
    keys = ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "all_proxy", "no_proxy"]
    backup = {k: os.environ.get(k) for k in keys}
    try:
        for k in keys:
            os.environ.pop(k, None)
        yield
    finally:
        for k, v in backup.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _test_connection(provider: str, model: str, use_system_proxy: bool) -> tuple[bool, str, float]:
    import time
    t0 = time.time()
    try:
        if provider == "openai":
            from openai import OpenAI
            key = os.getenv("OPENAI_API_KEY", "")
            if not key:
                return False, "OPENAI_API_KEY missing", 0.0
            with _proxy_context(use_system_proxy):
                client = OpenAI(api_key=key)
                resp = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "Reply only: OK"}],
                    max_tokens=8,
                    temperature=0,
                )
            txt = (resp.choices[0].message.content or "").strip() if resp and resp.choices else ""
            return True, txt or "OK", time.time() - t0
        from anthropic import Anthropic
        key = os.getenv("ANTHROPIC_API_KEY", "")
        if not key:
            return False, "ANTHROPIC_API_KEY missing", 0.0
        with _proxy_context(use_system_proxy):
            client = Anthropic(api_key=key)
            resp = client.messages.create(
                model=model,
                max_tokens=8,
                messages=[{"role": "user", "content": "Reply only: OK"}],
            )
        txt = resp.content[0].text.strip() if resp and resp.content else ""
        return True, txt or "OK", time.time() - t0
    except Exception as e:
        return False, f"{type(e).__name__}: {e}", time.time() - t0


def render() -> None:
    st.title("AI Models")
    cfg = load_main_config()
    ai_cfg = cfg.setdefault("ai", {})

    provider = ai_cfg.get("provider", "anthropic")
    use_system_proxy = bool(ai_cfg.get("use_system_proxy", False))

    col1, col2 = st.columns(2)
    with col1:
        provider = st.selectbox(
            "Provider",
            options=["anthropic", "openai"],
            index=0 if provider == "anthropic" else 1,
            format_func=lambda x: "Anthropic" if x == "anthropic" else "OpenAI",
        )
        use_system_proxy = st.checkbox("Use system proxy", value=use_system_proxy)

    options = OPENAI_MODELS if provider == "openai" else ANTHROPIC_MODELS
    model = ai_cfg.get("model", options[0])
    fallback = ai_cfg.get("fallback_model", options[1] if len(options) > 1 else options[0])

    with col2:
        model = st.selectbox("Primary model", options=options, index=options.index(model) if model in options else 0)
        fallback = st.selectbox("Fallback model", options=options, index=options.index(fallback) if fallback in options else 0)

    env_name = "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
    current_key = os.getenv(env_name, "")
    masked = f"{current_key[:6]}...{current_key[-4:]}" if len(current_key) > 10 else ("Configured" if current_key else "Not configured")
    st.caption(f"{env_name}: {masked}")
    new_key = st.text_input("API Key (optional update)", value="", type="password")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Save AI Model Settings", type="primary"):
            snapshot_configs("before_ai_model_change")
            ai_cfg["provider"] = provider
            ai_cfg["model"] = model
            ai_cfg["fallback_model"] = fallback
            ai_cfg["use_system_proxy"] = use_system_proxy
            save_main_config(cfg)
            if new_key.strip():
                upsert_env_var(env_name, new_key.strip())
            st.success("AI model settings saved.")

    with c2:
        if st.button("Test Connection"):
            ok, message, latency = _test_connection(provider, model, use_system_proxy)
            if ok:
                st.success(f"OK ({latency*1000:.0f} ms): {message}")
            else:
                st.error(f"FAILED ({latency*1000:.0f} ms): {message}")

    st.divider()
    st.subheader("Current Runtime Selection")
    st.write(
        {
            "provider": provider,
            "primary_model": model,
            "fallback_model": fallback,
            "proxy_enabled": use_system_proxy,
        }
    )
