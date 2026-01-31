"""
AI Trader - Database Browser

GUI for viewing and managing the SQLite database.
"""

import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime
import sys

DEV_DIR = Path(__file__).parent.parent
if str(DEV_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_DIR))

from components.tooltips import ICONS
from components.status_bar import render_status_bar, get_status_bar_data
from src.utils.config import config

st.set_page_config(page_title="Database - AI Trader", page_icon="", layout="wide")

# Database path
DB_PATH = DEV_DIR / "data" / "trades.db"


def get_connection():
    """Get database connection."""
    return sqlite3.connect(DB_PATH)


def get_tables():
    """Get list of all tables in database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables


def get_table_info(table_name: str):
    """Get column info for a table."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    conn.close()
    return columns


def get_table_count(table_name: str) -> int:
    """Get row count for a table."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_table_data(table_name: str, limit: int = 100, offset: int = 0, order_by: str = None, order_desc: bool = True):
    """Get data from a table."""
    conn = get_connection()

    query = f"SELECT * FROM {table_name}"
    if order_by:
        direction = "DESC" if order_desc else "ASC"
        query += f" ORDER BY {order_by} {direction}"
    query += f" LIMIT {limit} OFFSET {offset}"

    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def execute_query(query: str):
    """Execute a custom SQL query."""
    conn = get_connection()
    try:
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df, None
    except Exception as e:
        conn.close()
        return None, str(e)


def get_database_stats():
    """Get overall database statistics."""
    conn = get_connection()
    cursor = conn.cursor()

    stats = {
        "file_size": 0,
        "tables": [],
        "total_records": 0
    }

    # File size
    if DB_PATH.exists():
        stats["file_size"] = DB_PATH.stat().st_size / 1024  # KB

    # Table stats
    tables = get_tables()
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        stats["tables"].append({"name": table, "count": count})
        stats["total_records"] += count

    conn.close()
    return stats


def render_table_browser():
    """Render table browser section."""
    st.subheader(f"{ICONS['list']} Table Browser")

    tables = get_tables()

    if not tables:
        st.warning("No tables found in database")
        return

    # Table selector
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        selected_table = st.selectbox("Select Table", tables)

    with col2:
        limit = st.number_input("Rows per page", min_value=10, max_value=500, value=50)

    with col3:
        # Get columns for ordering
        columns_info = get_table_info(selected_table)
        column_names = [col[1] for col in columns_info]
        order_by = st.selectbox("Order by", ["(default)"] + column_names)

    # Pagination
    total_rows = get_table_count(selected_table)
    total_pages = max(1, (total_rows + limit - 1) // limit)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        page = st.number_input("Page", min_value=1, max_value=total_pages, value=1)

    offset = (page - 1) * limit

    st.caption(f"Showing rows {offset + 1} - {min(offset + limit, total_rows)} of {total_rows}")

    # Get and display data
    order_col = None if order_by == "(default)" else order_by
    df = get_table_data(selected_table, limit=limit, offset=offset, order_by=order_col)

    if df.empty:
        st.info("No data in this table")
    else:
        # Display table schema
        with st.expander(f"{ICONS['info']} Table Schema"):
            schema_data = []
            for col in columns_info:
                schema_data.append({
                    "Column": col[1],
                    "Type": col[2],
                    "Not Null": "Yes" if col[3] else "No",
                    "Default": col[4] if col[4] else "-",
                    "Primary Key": "Yes" if col[5] else "No"
                })
            st.dataframe(pd.DataFrame(schema_data), use_container_width=True, hide_index=True)

        # Display data
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Export button
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            csv = df.to_csv(index=False)
            st.download_button(
                label=f"{ICONS['arrow_down']} Download CSV",
                data=csv,
                file_name=f"{selected_table}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )


def render_query_editor():
    """Render SQL query editor."""
    st.subheader(f"{ICONS['chart']} SQL Query Editor")

    st.caption("Execute custom SQL queries (SELECT only for safety)")

    # Query input
    default_query = "SELECT * FROM trades ORDER BY timestamp DESC LIMIT 10"
    query = st.text_area("SQL Query", value=default_query, height=100)

    col1, col2 = st.columns([1, 5])
    with col1:
        run_query = st.button("Run Query", type="primary")

    if run_query:
        # Safety check - only allow SELECT
        if not query.strip().upper().startswith("SELECT"):
            st.error("Only SELECT queries are allowed for safety")
            return

        with st.spinner("Executing query..."):
            df, error = execute_query(query)

            if error:
                st.error(f"Query error: {error}")
            elif df is not None:
                st.success(f"Query returned {len(df)} rows")
                st.dataframe(df, use_container_width=True, hide_index=True)

                # Export
                csv = df.to_csv(index=False)
                st.download_button(
                    label=f"{ICONS['arrow_down']} Download Results",
                    data=csv,
                    file_name=f"query_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )


def render_quick_queries():
    """Render quick query buttons."""
    st.subheader(f"{ICONS['alert']} Quick Queries")

    queries = {
        "Recent Trades": "SELECT * FROM trades ORDER BY timestamp DESC LIMIT 20",
        "Open Positions": "SELECT * FROM trades WHERE status = 'OPEN'",
        "Profitable Trades": "SELECT * FROM trades WHERE pnl > 0 AND status = 'CLOSED' ORDER BY pnl DESC LIMIT 20",
        "Losing Trades": "SELECT * FROM trades WHERE pnl < 0 AND status = 'CLOSED' ORDER BY pnl ASC LIMIT 20",
        "Recent Errors": "SELECT * FROM errors ORDER BY timestamp DESC LIMIT 20",
        "High Confidence Decisions": "SELECT * FROM decisions WHERE confidence_score >= 70 ORDER BY timestamp DESC LIMIT 20",
        "Trade Summary by Pair": """
            SELECT instrument,
                   COUNT(*) as total_trades,
                   SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
                   ROUND(SUM(pnl), 2) as total_pnl
            FROM trades
            WHERE status = 'CLOSED'
            GROUP BY instrument
        """,
        "Error Categories": """
            SELECT error_category, COUNT(*) as count
            FROM errors
            GROUP BY error_category
            ORDER BY count DESC
        """
    }

    cols = st.columns(4)
    for i, (name, query) in enumerate(queries.items()):
        with cols[i % 4]:
            if st.button(name, use_container_width=True):
                st.session_state.quick_query = query
                st.session_state.run_quick_query = True

    # Execute quick query if selected
    if st.session_state.get("run_quick_query"):
        query = st.session_state.get("quick_query", "")
        st.session_state.run_quick_query = False

        st.markdown("---")
        st.code(query, language="sql")

        df, error = execute_query(query)
        if error:
            st.error(f"Error: {error}")
        elif df is not None:
            st.dataframe(df, use_container_width=True, hide_index=True)


def render_database_stats():
    """Render database statistics."""
    st.subheader(f"{ICONS['info']} Database Statistics")

    stats = get_database_stats()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Database Size", f"{stats['file_size']:.1f} KB")

    with col2:
        st.metric("Total Records", f"{stats['total_records']:,}")

    with col3:
        st.metric("Tables", len(stats['tables']))

    # Table breakdown
    st.markdown("**Records per Table:**")

    cols = st.columns(len(stats['tables']))
    for i, table in enumerate(stats['tables']):
        with cols[i]:
            st.metric(table['name'].capitalize(), f"{table['count']:,}")


def render_maintenance():
    """Render database maintenance section."""
    st.subheader(f"{ICONS['settings']} Maintenance")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Vacuum Database", help="Reclaim unused space"):
            try:
                conn = get_connection()
                conn.execute("VACUUM")
                conn.close()
                st.success("Database vacuumed successfully")
            except Exception as e:
                st.error(f"Error: {e}")

    with col2:
        if st.button("Analyze Tables", help="Update query statistics"):
            try:
                conn = get_connection()
                conn.execute("ANALYZE")
                conn.close()
                st.success("Tables analyzed successfully")
            except Exception as e:
                st.error(f"Error: {e}")

    with col3:
        st.caption(f"DB Path: `{DB_PATH}`")

    # Danger zone
    with st.expander(f"{ICONS['warning']} Danger Zone"):
        st.warning("These actions cannot be undone!")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Clear All Errors", type="secondary"):
                if st.session_state.get("confirm_clear_errors"):
                    try:
                        conn = get_connection()
                        conn.execute("DELETE FROM errors")
                        conn.commit()
                        conn.close()
                        st.success("Errors cleared")
                        st.session_state.confirm_clear_errors = False
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.session_state.confirm_clear_errors = True
                    st.warning("Click again to confirm")

        with col2:
            if st.button("Clear Closed Trades", type="secondary"):
                if st.session_state.get("confirm_clear_trades"):
                    try:
                        conn = get_connection()
                        conn.execute("DELETE FROM trades WHERE status = 'CLOSED'")
                        conn.commit()
                        conn.close()
                        st.success("Closed trades cleared")
                        st.session_state.confirm_clear_trades = False
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.session_state.confirm_clear_trades = True
                    st.warning("Click again to confirm")


def main():
    st.title(f"{ICONS['list']} Database Browser")

    # Check if database exists
    if not DB_PATH.exists():
        st.error(f"Database not found at: {DB_PATH}")
        st.info("The database will be created when you run the first trade or analysis.")
        return

    # Tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs([
        f"{ICONS['list']} Browse Tables",
        f"{ICONS['chart']} Query Editor",
        f"{ICONS['alert']} Quick Queries",
        f"{ICONS['settings']} Maintenance"
    ])

    with tab1:
        render_database_stats()
        st.divider()
        render_table_browser()

    with tab2:
        render_query_editor()

    with tab3:
        render_quick_queries()

    with tab4:
        render_maintenance()

    # Status bar
    st.divider()
    try:
        from src.trading.mt5_client import MT5Client, MT5Error
        client = MT5Client()
        status_data = get_status_bar_data(client, config)
        render_status_bar(**status_data)
    except (ImportError, MT5Error, ConnectionError) as e:
        render_status_bar(connected=False)
    except Exception:
        render_status_bar(connected=False)


if __name__ == "__main__":
    main()
