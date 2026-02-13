"""AI Trader - redesigned high-contrast dark dashboard shell."""

from __future__ import annotations

import streamlit as st

from app_pages import home_ops, runtime_audit, performance, config_experiments, ai_models


st.set_page_config(
    page_title="AI Trader Ops",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
:root { color-scheme: dark; }
.stApp { background: #050607; color: #f5f7fa; }
[data-testid="stSidebar"] { background: #0b0f12; border-right: 1px solid #2a333d; }
.stMetric { background: #0f151b; border: 1px solid #2a333d; border-radius: 10px; padding: 10px; }
.stButton > button {
  background: #131b22;
  color: #f5f7fa;
  border: 1px solid #3a4654;
}
.stButton > button:hover { border-color: #7fb3ff; color: #ffffff; }
.stDataFrame, .stTable { border: 1px solid #2a333d; border-radius: 8px; }
h1,h2,h3 { color: #f4f8ff; }
</style>
    """,
    unsafe_allow_html=True,
)


def _page_wrapper(fn):
    def _wrapped():
        fn.render()
    return _wrapped


PAGES = {
    "Operations": [
        st.Page(_page_wrapper(home_ops), title="Home (Ops)", url_path="home-ops"),
        st.Page(_page_wrapper(runtime_audit), title="Runtime Audit", url_path="runtime-audit"),
        st.Page(_page_wrapper(performance), title="Performance", url_path="performance"),
    ],
    "Configuration": [
        st.Page(_page_wrapper(config_experiments), title="Config & Experiments", url_path="config-experiments"),
        st.Page(_page_wrapper(ai_models), title="AI Models", url_path="ai-models"),
    ],
}


def main() -> None:
    st.sidebar.title("AI Trader")
    st.sidebar.caption("Dark High-Contrast Ops Console")
    st.sidebar.divider()
    st.sidebar.caption("Legacy pages are hidden from primary navigation.")

    nav = st.navigation(PAGES, position="sidebar")
    nav.run()


if __name__ == "__main__":
    main()
