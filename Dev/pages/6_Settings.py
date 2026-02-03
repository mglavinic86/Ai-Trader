"""
AI Trader - Settings Page

Configuration and settings management.
"""

import streamlit as st
import json
import sys
from pathlib import Path

DEV_DIR = Path(__file__).parent.parent
if str(DEV_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_DIR))

from src.utils.config import config
from src.core.settings_manager import settings_manager
from components.empty_states import render_minimal_status

st.set_page_config(page_title="Settings - AI Trader", page_icon="", layout="wide")


def main():
    st.title("Settings")

    # Tabs for different settings sections
    tab1, tab2, tab3, tab4 = st.tabs(["Configuration", "Risk Management", "News API", "System"])

    # === Configuration Tab ===
    with tab1:
        st.subheader("Application Settings")

        cfg = settings_manager.get_config()

        # Interface settings
        st.markdown("### Interface")

        col1, col2 = st.columns(2)
        with col1:
            interface_name = st.text_input(
                "Name",
                value=cfg.get("interface", {}).get("name", "AI Trader"),
                disabled=True
            )
        with col2:
            interface_version = st.text_input(
                "Version",
                value=cfg.get("interface", {}).get("version", "1.0"),
                disabled=True
            )

        # AI settings
        st.markdown("### AI Settings")

        col1, col2 = st.columns(2)

        with col1:
            ai_model = st.text_input(
                "Model",
                value=cfg.get("ai", {}).get("model", "claude"),
                disabled=True,
                help="AI model used for analysis"
            )

            use_adversarial = st.checkbox(
                "Use Adversarial Analysis",
                value=cfg.get("ai", {}).get("use_adversarial", True),
                help="Generate bull/bear cases before trading"
            )

        with col2:
            temperature = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=1.0,
                value=cfg.get("ai", {}).get("temperature", 0.3),
                step=0.1,
                help="Lower = more consistent, Higher = more creative"
            )

            use_rag = st.checkbox(
                "Use RAG Memory",
                value=cfg.get("ai", {}).get("use_rag", True),
                help="Learn from past trading errors"
            )

        use_sentiment = st.checkbox(
            "Use Sentiment Analysis",
            value=cfg.get("ai", {}).get("use_sentiment", True),
            help="Include price action sentiment in analysis"
        )

        # Analysis settings
        st.markdown("### Analysis Settings")

        col1, col2 = st.columns(2)

        with col1:
            timeframes = ["M15", "M30", "H1", "H4", "D1"]
            default_tf = cfg.get("analysis", {}).get("default_timeframe", "H4")
            default_timeframe = st.selectbox(
                "Default Timeframe",
                timeframes,
                index=timeframes.index(default_tf) if default_tf in timeframes else 2
            )

        with col2:
            min_rr = st.number_input(
                "Minimum R:R Ratio",
                min_value=1.0,
                max_value=5.0,
                value=float(cfg.get("analysis", {}).get("min_rr_ratio", 1.5)),
                step=0.1,
                help="Minimum risk/reward ratio for trades"
            )

        # Save button
        if st.button("Save Configuration", type="primary"):
            try:
                # Update config
                if "ai" not in cfg:
                    cfg["ai"] = {}
                if "analysis" not in cfg:
                    cfg["analysis"] = {}

                cfg["ai"]["use_adversarial"] = use_adversarial
                cfg["ai"]["use_rag"] = use_rag
                cfg["ai"]["use_sentiment"] = use_sentiment
                cfg["ai"]["temperature"] = temperature
                cfg["analysis"]["default_timeframe"] = default_timeframe
                cfg["analysis"]["min_rr_ratio"] = min_rr

                # Save to file
                settings_manager._config = cfg
                settings_manager.save_config()

                st.success("Configuration saved!")
            except Exception as e:
                st.error(f"Error saving: {e}")

    # === Risk Management Tab ===
    with tab2:
        st.subheader("Risk Management")

        st.warning("Risk management settings are hard-coded for safety and cannot be modified through the UI.")

        # Display current risk settings (read-only)
        st.markdown("### Current Risk Limits")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"""
            **Position Sizing by Confidence:**

            | Confidence | Max Risk |
            |------------|----------|
            | 90-100% | 3% |
            | 70-89% | 2% |
            | 50-69% | 1% |
            | <50% | No Trade |
            """)

        with col2:
            st.markdown(f"""
            **Drawdown Limits:**

            | Limit | Value |
            |-------|-------|
            | Max Daily Drawdown | {config.MAX_DAILY_DRAWDOWN * 100:.0f}% |
            | Max Weekly Drawdown | {config.MAX_WEEKLY_DRAWDOWN * 100:.0f}% |
            | Max Concurrent Positions | {config.MAX_CONCURRENT_POSITIONS} |
            | Min Confidence to Trade | {config.MIN_CONFIDENCE_TO_TRADE}% |
            """)

        st.info("These limits are defined in `src/utils/config.py` and should only be modified by developers.")

    # === News API Tab ===
    with tab3:
        st.subheader("News Calendar API")

        st.markdown("""
        Configure automatic economic calendar updates from news providers.
        The calendar is used to avoid trading during high-impact news events.
        """)

        # Load news provider config
        news_config_path = DEV_DIR / "settings" / "news_providers.json"
        try:
            with open(news_config_path, "r", encoding="utf-8") as f:
                news_config = json.load(f)
        except Exception:
            news_config = {"providers": {}}

        # Provider settings
        st.markdown("### Providers")

        providers = news_config.get("providers", {})

        # Finnhub
        st.markdown("#### Finnhub (Recommended)")
        col1, col2 = st.columns([3, 1])
        with col1:
            finnhub_key = st.text_input(
                "Finnhub API Key",
                value=providers.get("finnhub", {}).get("api_key", ""),
                type="password",
                help="Get free API key at https://finnhub.io (60 calls/min)"
            )
        with col2:
            finnhub_enabled = st.checkbox(
                "Enabled",
                value=providers.get("finnhub", {}).get("enabled", True),
                key="finnhub_enabled"
            )
        st.caption("[Get Finnhub API Key (Free)](https://finnhub.io/register)")

        # FMP
        st.markdown("#### Financial Modeling Prep")
        col1, col2 = st.columns([3, 1])
        with col1:
            fmp_key = st.text_input(
                "FMP API Key",
                value=providers.get("fmp", {}).get("api_key", ""),
                type="password",
                help="Get free API key at financialmodelingprep.com (250 calls/day)"
            )
        with col2:
            fmp_enabled = st.checkbox(
                "Enabled",
                value=providers.get("fmp", {}).get("enabled", True),
                key="fmp_enabled"
            )
        st.caption("[Get FMP API Key (Free)](https://site.financialmodelingprep.com/developer)")

        # Forex Factory
        st.markdown("#### Forex Factory")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.text("Uses JBlanked API (may require key)")
        with col2:
            ff_enabled = st.checkbox(
                "Enabled",
                value=providers.get("forexfactory", {}).get("enabled", True),
                key="ff_enabled"
            )

        # Recurring (fallback)
        st.markdown("#### Recurring Events (Fallback)")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.text("Auto-generates known high-impact events (NFP, FOMC, etc.)")
        with col2:
            recurring_enabled = st.checkbox(
                "Enabled",
                value=providers.get("recurring", {}).get("enabled", True),
                key="recurring_enabled"
            )
        st.caption("Works without API key - recommended as fallback")

        # Refresh settings
        st.markdown("### Refresh Settings")
        col1, col2 = st.columns(2)
        with col1:
            refresh_interval = st.number_input(
                "Refresh Interval (minutes)",
                min_value=15,
                max_value=240,
                value=news_config.get("refresh_interval_minutes", 60),
                step=15
            )
        with col2:
            days_ahead = st.number_input(
                "Days Ahead",
                min_value=1,
                max_value=14,
                value=news_config.get("days_ahead", 7),
                step=1
            )

        # Save button
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save News Config", type="primary"):
                try:
                    news_config["providers"]["finnhub"] = {
                        "enabled": finnhub_enabled,
                        "api_key": finnhub_key,
                        "priority": 1
                    }
                    news_config["providers"]["fmp"] = {
                        "enabled": fmp_enabled,
                        "api_key": fmp_key,
                        "priority": 2
                    }
                    news_config["providers"]["forexfactory"] = {
                        "enabled": ff_enabled,
                        "priority": 3
                    }
                    news_config["providers"]["recurring"] = {
                        "enabled": recurring_enabled,
                        "priority": 10
                    }
                    news_config["refresh_interval_minutes"] = refresh_interval
                    news_config["days_ahead"] = days_ahead

                    with open(news_config_path, "w", encoding="utf-8") as f:
                        json.dump(news_config, f, indent=2)

                    st.success("News config saved!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving: {e}")

        with col2:
            if st.button("Refresh Now"):
                try:
                    import asyncio
                    from src.analysis.news_filter import news_filter

                    async def do_refresh():
                        return await news_filter.refresh_from_api(force=True)

                    success = asyncio.run(do_refresh())
                    if success:
                        st.success("Calendar refreshed from API!")
                    else:
                        st.warning("Refresh failed - check API key or try backup provider")
                except Exception as e:
                    st.error(f"Refresh error: {e}")

        # Current calendar status
        st.markdown("### Current Calendar Status")
        try:
            from src.analysis.news_filter import news_filter
            status = news_filter.get_calendar_status()

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Events", status["total_events"])
            with col2:
                st.metric("HIGH Impact", status["high_impact"])
            with col3:
                st.metric("MEDIUM Impact", status["medium_impact"])

            st.text(f"Source: {status['source']}")
            st.text(f"Last Updated: {status['last_updated'] or 'Never'}")

        except Exception as e:
            st.error(f"Could not load calendar status: {e}")

        # View current events
        with st.expander("View Upcoming Events"):
            try:
                calendar_path = DEV_DIR / "settings" / "news_calendar.json"
                if calendar_path.exists():
                    with open(calendar_path, "r", encoding="utf-8") as f:
                        calendar_data = json.load(f)

                    events = calendar_data.get("events", [])
                    if events:
                        import pandas as pd
                        df = pd.DataFrame(events)
                        if "time" in df.columns:
                            df = df.sort_values("time")
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("No events in calendar")
                else:
                    st.info("Calendar file not found - click Refresh Now")
            except Exception as e:
                st.error(f"Error loading events: {e}")

    # === System Tab ===
    with tab4:
        st.subheader("System Information")

        # Connection status
        st.markdown("### MT5 Connection")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"""
            | Property | Value |
            |----------|-------|
            | Login | {config.MT5_LOGIN or 'Not configured'} |
            | Server | {config.MT5_SERVER or 'Not configured'} |
            | Mode | {'DEMO' if config.is_demo() else 'LIVE'} |
            """)

        with col2:
            connection_valid, error = config.validate_mt5()
            if connection_valid:
                st.success("MT5 credentials configured")
            else:
                st.error(f"MT5 not configured: {error}")

        # File paths
        st.markdown("### File Locations")

        paths = {
            "Settings Directory": str(settings_manager.settings_dir),
            "Skills Directory": str(settings_manager.skills_dir),
            "Knowledge Directory": str(settings_manager.knowledge_dir),
            "Config File": str(settings_manager.settings_dir / "config.json"),
            "System Prompt": str(settings_manager.settings_dir / "system_prompt.md"),
        }

        for name, path in paths.items():
            st.text(f"{name}: {path}")

        # Reload settings
        st.markdown("### Actions")

        if st.button("Reload All Settings"):
            settings_manager.reload()
            st.success("Settings reloaded from disk")
            st.rerun()

        # View raw config
        with st.expander("View Raw Config (JSON)"):
            st.json(settings_manager.get_config())

    # Minimal status bar
    render_minimal_status()


if __name__ == "__main__":
    main()
