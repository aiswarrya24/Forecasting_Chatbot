
# src/utils.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import time # For simulating typing delay
from .config import DATE_FORMAT_ISO, DATE_FORMAT_DMY, TYPING_INDICATOR_MESSAGE, LLM_TYPING_INDICATOR_DURATION_SECONDS

def init_chat_history():
    """Initializes chat history in Streamlit's session state."""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

def append_chat(role: str, message: str):
    """Appends a message to the chat history."""
    st.session_state.chat_history.append({"role": role, "content": message})

def display_chat_history():
    """Displays all messages in the chat history."""
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

def export_csv(df: pd.DataFrame, filename: str):
    """Provides a download button for a DataFrame as a CSV."""
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label=f"Download {filename}",
        data=csv,
        file_name=filename,
        mime='text/csv',
        key=f"download_{filename.replace('.', '_')}" # Ensure unique key for button
    )

def parse_date_string(date_str: str) -> datetime | None:
    """
    Parses a date string into a datetime object. Handles multiple formats.
    Args:
        date_str (str): The date string from LLM (e.g., "YYYY-MM-DD").
    Returns:
        datetime | None: Parsed datetime object, or None if parsing fails.
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, DATE_FORMAT_ISO)
    except ValueError:
        try: # Try another common format if ISO fails
            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return None # Return None if parsing fails

def get_week_start_end(ref_date: datetime) -> tuple[datetime, datetime]:
    """Calculates the start and end dates of the week for a given reference date."""
    start_of_week = ref_date - timedelta(days=ref_date.weekday())
    end_of_week = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
    return start_of_week, end_of_week

def get_month_start_end(ref_date: datetime) -> tuple[datetime, datetime]:
    """Calculates the start and end dates of the month for a given reference date."""
    start_of_month = ref_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Calculate end of month: add one month, then subtract one day
    if start_of_month.month == 12:
        end_of_month = start_of_month.replace(year=start_of_month.year + 1, month=1) - timedelta(days=1)
    else:
        end_of_month = start_of_month.replace(month=start_of_month.month + 1) - timedelta(days=1)
    end_of_month = end_of_month.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start_of_month, end_of_month

def get_all_time_start_end() -> tuple[datetime, datetime]:
    """Returns a very early and very late date to represent 'all time'."""
    return datetime(1900, 1, 1), datetime(2100, 12, 31, 23, 59, 59, 999999)

def show_typing_indicator():
    """Displays a 'thinking' message in the chat history, simulating typing."""
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown(TYPING_INDICATOR_MESSAGE)
        time.sleep(LLM_TYPING_INDICATOR_DURATION_SECONDS) # Simulate thinking time
        message_placeholder.empty() # Clear indicator

