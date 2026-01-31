"""
Shared MT5 session management for AI Trader dashboard.

Provides centralized MT5 client initialization and connection handling.
"""

import streamlit as st
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def get_client():
    """
    Get or create MT5 client from session state.

    Returns:
        MT5Client instance if connected, None otherwise.
    """
    # Initialize session state
    if "mt5_client" not in st.session_state:
        st.session_state.mt5_client = None
    if "connected" not in st.session_state:
        st.session_state.connected = False

    # Try to connect if not already connected
    if st.session_state.mt5_client is None:
        try:
            from src.trading.mt5_client import MT5Client, MT5Error
            client = MT5Client()
            if client.is_connected():
                st.session_state.mt5_client = client
                st.session_state.connected = True
        except ImportError as e:
            logger.error(f"Failed to import MT5Client: {e}")
        except Exception as e:
            logger.warning(f"Failed to connect to MT5: {e}")

    return st.session_state.mt5_client


def is_connected() -> bool:
    """
    Check if MT5 is connected.

    Returns:
        True if connected, False otherwise.
    """
    return st.session_state.get("connected", False)


def reset_connection():
    """Reset MT5 connection state, forcing a reconnection on next get_client() call."""
    st.session_state.mt5_client = None
    st.session_state.connected = False


def get_client_with_retry(max_attempts: int = 1):
    """
    Get MT5 client with optional retry logic.

    Args:
        max_attempts: Maximum connection attempts (default 1)

    Returns:
        MT5Client instance if connected, None otherwise.
    """
    for attempt in range(max_attempts):
        client = get_client()
        if client is not None:
            return client
        if attempt < max_attempts - 1:
            reset_connection()

    return None
