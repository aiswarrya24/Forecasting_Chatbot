import streamlit as st
import pandas as pd
import plotly.express as px
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta
import plotly.graph_objects as go

from chat_ui import show_farewell, show_greeting, show_chat_bubble, show_login_box 
from .db import get_sales_data, get_tenant_gname, get_all_tenants_sales
from .llm import ask_llama, extract_query_info_from_llm
from .utils import append_chat, display_chat_history, export_csv, parse_date_string, get_week_start_end, get_month_start_end, get_all_time_start_end, show_typing_indicator
from .config import (
    ERROR_NO_RECORDS, ERROR_LLM_API_FAILURE, ERROR_UNCLEAR_QUERY,
    NAV_BACK_MESSAGE, CHATBOT_CAPABILITIES, DATE_FORMAT_ISO, DATE_FORMAT_DMY,
    TYPING_INDICATOR_MESSAGE, QUICK_ACTIONS, DATA_FETCH_INDICATOR_MESSAGE,
    DATA_PROCESSING_INDICATOR_MESSAGE, ERROR_GENERAL
)
from .auth import authenticate_creator  # Import Creator auth here for use in handler

def _get_start_end_dates_from_llm_response(llm_response: dict) -> tuple[datetime | None, datetime | None]:
    """Parses start and end dates from LLM response strings into datetime objects."""
    start_date = parse_date_string(llm_response["start_date"]) if llm_response.get("start_date") else None
    end_date = parse_date_string(llm_response["end_date"]) if llm_response.get("end_date") else None
    return start_date, end_date

def _display_sales_chart(df: pd.DataFrame, title: str, x_axis_label: str = "Date", y_axis_label: str = "Sales"):
    """
    Displays a line chart for sales data.
    Args:
        df (pd.DataFrame): DataFrame with 'date' and 'sales' columns.
        title (str): Title of the chart.
        x_axis_label (str): Label for the x-axis.
        y_axis_label (str): Label for the y-axis.
    """
    if df.empty:
        st.warning("No data to display for the chart.")
        return

    # Ensure 'date' column is datetime type for proper plotting
    df['date'] = pd.to_datetime(df['date'])
    fig = px.line(df, x='date', y='sales', title=title,
                  labels={'date': x_axis_label, 'sales': y_axis_label},
                  markers=True)
    fig.update_layout(hovermode="x unified")  # Shows all y-values at a specific x-point
    st.plotly_chart(fig, use_container_width=True)

def _show_back_to_main_menu_option():
    """Displays the option to go back to the main menu."""
    st.markdown("---")
    if st.button(NAV_BACK_MESSAGE, key=f"back_to_main_menu_{st.session_state.current_menu}"):
        st.session_state.current_menu = "main"
        # Clear any specific sub-menu states that might cause issues on return
        st.session_state.pop("awaiting_report_confirmation", None)
        st.session_state.pop("report_data_for_prompt", None)
        st.session_state.pop("report_generated_params", None)
        # Clear query-specific flags
        st.session_state.pop("processing_chat_input", None)
        st.session_state.pop("chat_query_to_process", None)
        st.experimental_rerun()

def show_main_menu():
    """Main UI function to render menu."""
    # Check tenant_id initialized
    if "tenant_id" not in st.session_state or not st.session_state.tenant_id:
        st.error("User not logged in. Please login first.")
        return

    st.title(f"🏪 SalesBot - {st.session_state.tenant_id}")
    st.write(f"Welcome, {st.session_state.tenant_id}! Please choose an option or ask a question about your sales.")

    show_greeting()

    if st.button("Logout"):
        handle_logout()

    # Initialize gname if not already set (only once after tenant login)
    if "gname" not in st.session_state or st.session_state.gname is None:
        st.session_state.gname = get_tenant_gname(st.session_state.tenant_id)
        if not st.session_state.gname:
            st.session_state.gname = None
        st.experimental_rerun()

def show_main_ui():
    """Main UI function that includes chat input, menu, chat history, and main content."""

    # Show title and welcome message
    if "tenant_id" in st.session_state and st.session_state.tenant_id:
        st.title(f"🏪 SalesBot - {st.session_state.tenant_id}")
        st.write(f"Welcome, {st.session_state.tenant_id}! Please choose an option or ask a question about your sales.")
    else:
        st.error("User not logged in. Please login first.")
        return

    # Chat input box
    user_input_global = st.chat_input("Ask about your sales here:")

    if user_input_global:
        append_chat("user", user_input_global)
        st.session_state.processing_chat_input = True
        st.session_state.chat_query_to_process = user_input_global
        st.session_state.current_menu = "ask_question_menu"
        st.experimental_rerun()

    # Show chat history
    if "chat_history" in st.session_state:
        for role, message in st.session_state.chat_history:
            show_chat_bubble(role, message)

    # Quick action buttons
    cols = st.columns(len(QUICK_ACTIONS))
    for i, action in enumerate(QUICK_ACTIONS):
        with cols[i]:
            if st.button(action, key=f"quick_action_{action.replace(' ', '_').lower()}"):
                append_chat("user", action)
                st.session_state.processing_chat_input = True
                st.session_state.chat_query_to_process = action
                st.session_state.current_menu = "ask_question_menu"
                st.experimental_rerun()

    # Left menu panel and main content panel
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Menu")
        current_option = st.session_state.get("selected_main_menu_option", "Ask a Question")
        option = st.radio(
            "Choose:",
            [
                "Ask a Question",
                "Reports",
                "Forecasting",
                "Sales Summary",
                "Leaderboard",
                "Help",
                "Creator Access",
            ],
            index=[
                "Ask a Question",
                "Reports",
                "Forecasting",
                "Sales Summary",
                "Leaderboard",
                "Help",
                "Creator Access",
            ].index(current_option),
            key="main_menu_options",
        )
        if option != current_option:
            st.session_state.selected_main_menu_option = option
            st.session_state.current_menu = option.lower().replace(" ", "_")
            st.experimental_rerun()

    with col2:
        # Handle Creator Access menus
        if st.session_state.current_menu == "creator_access":
            show_creator_menu()
        elif st.session_state.current_menu == "creator_access_login":
            handle_creator_access_login()
        else:
            # If processing chat input flag is set, process it now
            if st.session_state.get("processing_chat_input"):
                query = st.session_state.pop("chat_query_to_process")
                st.session_state.processing_chat_input = False
                handle_chat_query_logic(query)
                st.experimental_rerun()

            # Show chat UI if in ask question menu
            if st.session_state.current_menu == "ask_question_menu":
                st.subheader("Your Chat")
                display_chat_history()

            # Handle report confirmation follow-up
            if st.session_state.get("awaiting_report_confirmation"):
                confirm_input = st.chat_input("Type 'Yes' or 'No'")
                if confirm_input:
                    append_chat("user", confirm_input)
                    if confirm_input.lower().strip() == "yes":
                        append_chat("bot", "Generating report...")
                        report_params = st.session_state.pop("report_data_for_prompt", None)
                        st.session_state.report_generated_params = report_params
                        st.session_state.current_menu = "reports"
                        st.session_state.awaiting_report_confirmation = False
                        st.experimental_rerun()
                    elif confirm_input.lower().strip() == "no":
                        append_chat("bot", "Okay!")
                        st.session_state.awaiting_report_confirmation = False
                        st.experimental_rerun()
                    else:
                        append_chat("bot", "Please type 'Yes' or 'No'.")
                        st.experimental_rerun()
            elif st.session_state.current_menu == "reports":
                show_reports()
            elif st.session_state.current_menu == "forecasting":
                show_forecasting()
            elif st.session_state.current_menu == "sales_summary":
                show_sales_summary_wrapper()
            elif st.session_state.current_menu == "leaderboard":
                show_leaderboard()
            elif st.session_state.current_menu == "help":
                show_help()
            else:
                st.info("Select an option from the menu to proceed or use the chat input.")

# --- New function to encapsulate chat query processing logic ---
def handle_chat_query_logic(query: str):
    """
    Encapsulates the core logic for processing a natural language sales query.
    This is separated from `handle_chat` to manage reruns and state more clearly.
    """
    tenant_id = st.session_state.tenant_id
    gname = st.session_state.gname

    st.info(f"Processing query: '{query}' for tenant: {tenant_id}, group: {gname}")

    try:
        show_typing_indicator() # Show typing indicator before LLM call
        # Use LLM to extract intent and entities
        llm_info = extract_query_info_from_llm(query, tenant_id, gname)
        intent = llm_info.get("intent")
        scope = llm_info.get("scope", "tenant") # Default to tenant if not specified by LLM
        pname_filter = llm_info.get("pname")

        st.info(f"LLM extracted: Intent={intent}, Scope={scope}, Pname={pname_filter}")

        # Ensure scope aligns with logged-in tenant's gname for group queries
        if scope == "group" and not gname:
            bot_response = "I cannot process group-level queries as your tenant is not associated with a group."
            append_chat("bot", bot_response)
            return

        # Determine target for database query based on scope
        query_tname = tenant_id if scope == "tenant" else None
        query_gname = gname if scope == "group" else None

        # Determine dates based on intent, especially for monthly/weekly/all-time
        start_date, end_date = None, None
        is_all_time_query = False

        # --- Intent-based date and sales data handling ---
        if intent in ["single_day_sales", "date_range_sales", "highest_sales", "lowest_sales", "monthly_sales", "weekly_sales"]:
            # Logic for date inference
            if intent in ["highest_sales", "lowest_sales"]:
                start_date_str = llm_info.get("start_date")
                end_date_str = llm_info.get("end_date")
                if start_date_str is None and end_date_str is None:
                    is_all_time_query = True
                else:
                    start_date, end_date = _get_start_end_dates_from_llm_response(llm_info)
            elif intent == "monthly_sales":
                current_date = datetime.now()
                start_date, end_date = get_month_start_end(current_date)
            elif intent == "weekly_sales":
                current_date = datetime.now()
                start_date, end_date = get_week_start_end(current_date)
            elif intent in ["single_day_sales", "date_range_sales"]:
                start_date, end_date = _get_start_end_dates_from_llm_response(llm_info)
                if intent == "single_day_sales" and start_date and not end_date:
                    end_date = start_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                elif start_date and end_date:
                    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                elif not start_date and end_date:
                     start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)

            # Validate dates for non-all-time queries before fetching sales data
            if not start_date and not end_date and not is_all_time_query:
                bot_response = ERROR_UNCLEAR_QUERY
                append_chat("bot", bot_response)
                st.session_state.awaiting_report_confirmation = False
                return # Exit if dates are missing for non-all-time intents

            st.info(DATA_FETCH_INDICATOR_MESSAGE)
            sales_data = get_sales_data(
                tname=query_tname,
                gname=query_gname,
                start_date=start_date,
                end_date=end_date,
                pname=pname_filter,
                all_time=is_all_time_query,
                include_pname=True
            )

            # --- FIX: Ensure message is appended when no data is found ---
            if not sales_data:
                bot_response = ERROR_NO_RECORDS
                append_chat("bot", bot_response)
                st.session_state.awaiting_report_confirmation = False
                return # Exit early if no data is found
            # --- END FIX ---
            else:
                df = pd.DataFrame(sales_data)
                df['date'] = pd.to_datetime(df['date'])

                filtered_df_for_min_max = df.copy() # Default to full df
                if intent in ["highest_sales", "lowest_sales"]:
                    # Ensure we filter out actual zero sales for meaningful min/max
                    filtered_df_for_min_max = df[df['sales'] > 0.01].copy() # Filter sales > 0.01
                    if filtered_df_for_min_max.empty:
                        bot_response = "No sales greater than zero found for this period."
                        append_chat("bot", bot_response)
                        return # Exit here if no meaningful sales

                if intent == "single_day_sales" or (intent == "date_range_sales" and start_date == end_date and not is_all_time_query):
                    total_sales = df['sales'].sum()
                    bot_response = f"📅 Sales on {start_date.strftime(DATE_FORMAT_DMY)}: ₹{total_sales:,.2f}"
                elif intent == "date_range_sales":
                    total_sales = df['sales'].sum()
                    bot_response = f"📈 Total sales from {start_date.strftime(DATE_FORMAT_DMY)} to {end_date.strftime(DATE_FORMAT_DMY)}: ₹{total_sales:,.2f}"
                elif intent == "monthly_sales":
                    total_sales = df['sales'].sum()
                    bot_response = f"🗓️ Your monthly sales for {start_date.strftime('%B %Y')}: ₹{total_sales:,.2f}"
                elif intent == "weekly_sales":
                    total_sales = df['sales'].sum()
                    bot_response = f"🗓️ Your weekly sales for {start_date.strftime(DATE_FORMAT_DMY)} to {end_date.strftime(DATE_FORMAT_DMY)}: ₹{total_sales:,.2f}"
                elif intent == "highest_sales":
                    idx_max = filtered_df_for_min_max['sales'].idxmax()
                    highest_sale_date = filtered_df_for_min_max.loc[idx_max, 'date'].strftime(DATE_FORMAT_DMY)
                    highest_sale_amount = filtered_df_for_min_max.loc[idx_max, 'sales']
                    highest_sale_pname = filtered_df_for_min_max.loc[idx_max, 'pname'] if 'pname' in filtered_df_for_min_max.columns else "N/A"
                    bot_response = f"🏆 Highest sale of ₹{highest_sale_amount:,.2f} occurred on {highest_sale_date} (Property: {highest_sale_pname})."
                elif intent == "lowest_sales":
                    idx_min = filtered_df_for_min_max['sales'].idxmin()
                    lowest_sale_date = filtered_df_for_min_max.loc[idx_min, 'date'].strftime(DATE_FORMAT_DMY)
                    lowest_sale_amount = filtered_df_for_min_max.loc[idx_min, 'sales']
                    lowest_sale_pname = filtered_df_for_min_max.loc[idx_min, 'pname'] if 'pname' in filtered_df_for_min_max.columns else "N/A"
                    bot_response = f"📉 Lowest sale of ₹{lowest_sale_amount:,.2f} occurred on {lowest_sale_date} (Property: {lowest_sale_pname})."

                append_chat("bot", bot_response)

                st.info(DATA_PROCESSING_INDICATOR_MESSAGE)
                # LLM-powered insight generation for data summaries
                summary_prompt = f"""
                You have just retrieved sales data.
                Here is a summary of the data:
                Total sales: ₹{df['sales'].sum():,.2f}
                Number of records: {len(df)}
                Date range: {df['date'].min().strftime(DATE_FORMAT_DMY)} to {df['date'].max().strftime(DATE_FORMAT_DMY)}
                Average daily sales: ₹{df['sales'].sum() / df['date'].nunique():,.2f}

                Based on this data, provide a brief (1-2 sentences) natural language insight or observation.
                For example: "Overall sales for this period look strong, averaging ₹X per day."
                Avoid mentioning specific values again unless critical for insight.
                Just provide the insight, no salutation.
                """
                try:
                    llm_insight = ask_llama(summary_prompt)
                    append_chat("bot", f"💡 Here's an insight: {llm_insight}")
                except Exception as insight_e:
                    st.warning(f"Could not generate LLM insight: {insight_e}")
                    append_chat("bot", "I couldn't generate an additional insight at this moment.")

                # User feedback buttons
                st.markdown("---")
                feedback_cols = st.columns(2)
                with feedback_cols[0]:
                    if st.button("👍 This was helpful!", key="helpful_feedback"):
                        append_chat("bot", "Great! Glad I could help.")
                        st.session_state.current_menu = "main" # Go back to main menu
                        st.rerun()
                with feedback_cols[1]:
                    if st.button("👎 Needs improvement", key="unhelpful_feedback"):
                        append_chat("bot", "I apologize. Could you please clarify what I missed or got wrong?")
                        st.session_state.current_menu = "main" # Go back to main menu
                        st.rerun()
                st.session_state.awaiting_report_confirmation = True # Keep for report
                st.session_state.report_data_for_prompt = {
                    "tname": query_tname,
                    "gname": query_gname,
                    "start_date": start_date,
                    "end_date": end_date,
                    "scope": scope
                }
                append_chat("bot", "Would you like a detailed report for this period (Yes/No)?")

        elif intent == "summary":
            if scope == "tenant":
                show_sales_summary_logic(tenant_id=tenant_id, scope="tenant")
            elif scope == "group":
                show_sales_summary_logic(gname=gname, scope="group")
            st.session_state.awaiting_report_confirmation = False
        elif intent == "unknown":
            bot_response = ERROR_UNCLEAR_QUERY
            append_chat("bot", bot_response)
            st.session_state.awaiting_report_confirmation = False
        else: # Fallback for any unhandled intent
            bot_response = ERROR_UNCLEAR_QUERY
            append_chat("bot", bot_response)
            st.session_state.awaiting_report_confirmation = False

    except Exception as e:
        st.error(f"An error occurred during chat processing: {e}")
        import traceback
        st.error(traceback.format_exc())
        if "LLaMA API error" in str(e):
            bot_response = ERROR_LLM_API_FAILURE
        elif "JSONDecodeError" in str(e) or "Expecting value" in str(e):
            bot_response = "I received an unparseable response from the AI. Please try rephrasing your question or check the system prompt."
        else:
            bot_response = f"An unexpected error occurred: {e}\n\n{ERROR_UNCLEAR_QUERY}"
        append_chat("bot", bot_response)
        st.session_state.awaiting_report_confirmation = False
if st.session_state.get("report_generated_params"):
    st.info("Generating report based on your chat query...")
    params = st.session_state.pop("report_generated_params")
    report_scope = "My Sales" if params["tname"] else "My Group's Sales"
    st.subheader(f"📊 Detailed Report for Chat Query ({report_scope})")

    start_date = params.get('start_date')
    end_date = params.get('end_date')

    df = pd.DataFrame(get_sales_data(
        tname=params["tname"],
        gname=params["gname"],
        start_date=start_date,
        end_date=end_date
    ))

    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df = df.groupby('date')['sales'].sum().reset_index()

        start_str = start_date.strftime(DATE_FORMAT_DMY) if start_date else "N/A"
        end_str = end_date.strftime(DATE_FORMAT_DMY) if end_date else "N/A"

        _display_sales_chart(df, f"{report_scope} - Sales from {start_str} to {end_str}")
        export_csv(df[['date', 'sales']], f"{report_scope.replace(' ', '_')}_Chat_Query_Sales.csv")
    else:
        st.warning(ERROR_NO_RECORDS)
        
    
def show_reports():
    """
    Displays the reports menu and generates sales reports based on user selection.
    Includes options for weekly, monthly, weekend vs. weekday, and custom date ranges.
    """
    st.subheader("📊 Sales Reports")
    _show_back_to_main_menu_option()

    # --- Chat-triggered Report ---
    if st.session_state.get("report_generated_params"):
        st.info("Generating report based on your chat query...")
        params = st.session_state.pop("report_generated_params")
        report_scope = "My Sales" if params["tname"] else "My Group's Sales"
        st.subheader(f"📊 Detailed Report for Chat Query ({report_scope})")

        start_date = params.get('start_date')
        end_date = params.get('end_date')

        df = pd.DataFrame(get_sales_data(
            tname=params["tname"],
            gname=params["gname"],
            start_date=start_date,
            end_date=end_date
        ))

        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df = df.groupby('date')['sales'].sum().reset_index()

            start_str = start_date.strftime(DATE_FORMAT_DMY) if start_date else "N/A"
            end_str = end_date.strftime(DATE_FORMAT_DMY) if end_date else "N/A"

            _display_sales_chart(df, f"{report_scope} - Sales from {start_str} to {end_str}")
            export_csv(df[['date', 'sales']], f"{report_scope.replace(' ', '_')}_Chat_Query_Sales.csv")
        else:
            st.warning(ERROR_NO_RECORDS)
        return

    # --- Scope Selector ---
    report_scope = st.radio("Select Report Scope:", ["My Sales", "My Group's Sales"], key="report_scope")
    tname = st.session_state.tenant_id
    gname = st.session_state.gname if report_scope == "My Group's Sales" else None

    if report_scope == "My Group's Sales" and not gname:
        st.warning("Your tenant is not associated with a group. Please select 'My Sales'.")
        return

    # --- Report Type Selector ---
    report_type = st.radio("Select Report Type:", [
        "Weekly Reports",
        "Monthly Reports",
        "Weekend vs. Weekday Reports",
        "Custom Date Range Reports"
    ], key="report_type_selector")

    # --- Weekly Reports ---
    if report_type == "Weekly Reports":
        selected_week = st.date_input("Select a date to get its week's report:", value=datetime.now(), key="weekly_date_input")
        if selected_week:
            start_date, end_date = get_week_start_end(datetime.combine(selected_week, datetime.min.time()))
            st.info(f"Generating weekly report for: {start_date.strftime(DATE_FORMAT_DMY)} to {end_date.strftime(DATE_FORMAT_DMY)}")

            df = pd.DataFrame(get_sales_data(tname=tname if gname is None else None, gname=gname, start_date=start_date, end_date=end_date))
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df = df.groupby('date')['sales'].sum().reset_index()
                _display_sales_chart(df, f"{report_scope} - Weekly Sales Report")
                export_csv(df[['date', 'sales']], f"{report_scope.replace(' ', '_')}_Weekly_Sales.csv")
            else:
                st.warning(ERROR_NO_RECORDS)

    # --- Monthly Reports ---
    elif report_type == "Monthly Reports":
        selected_month = st.date_input("Select a date to get its month's report:", value=datetime.now(), key="monthly_date_input")
        if selected_month:
            start_date, end_date = get_month_start_end(datetime.combine(selected_month, datetime.min.time()))
            st.info(f"Generating monthly report for: {start_date.strftime(DATE_FORMAT_DMY)} to {end_date.strftime(DATE_FORMAT_DMY)}")

            df = pd.DataFrame(get_sales_data(tname=tname if gname is None else None, gname=gname, start_date=start_date, end_date=end_date))
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df = df.groupby('date')['sales'].sum().reset_index()
                _display_sales_chart(df, f"{report_scope} - Monthly Sales Report")
                export_csv(df[['date', 'sales']], f"{report_scope.replace(' ', '_')}_Monthly_Sales.csv")
            else:
                st.warning(ERROR_NO_RECORDS)

    # --- Weekend vs. Weekday ---
    elif report_type == "Weekend vs. Weekday Reports":
        st.info("Analyzing sales for weekends vs. weekdays over the last 30 days.")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        df = pd.DataFrame(get_sales_data(tname=tname if gname is None else None, gname=gname, start_date=start_date, end_date=end_date))
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df['is_weekend'] = df['date'].dt.dayofweek.isin([5, 6])
            weekend_sales = df[df['is_weekend']]['sales'].sum()
            weekday_sales = df[~df['is_weekend']]['sales'].sum()

            st.write(f"**Weekend Sales:** ₹{weekend_sales:,.2f}")
            st.write(f"**Weekday Sales:** ₹{weekday_sales:,.2f}")

            bar_df = pd.DataFrame({
                'Category': ['Weekend', 'Weekday'],
                'Sales': [weekend_sales, weekday_sales]
            })
            fig = px.bar(bar_df, x='Category', y='Sales', title=f"{report_scope} - Weekend vs. Weekday Sales")
            st.plotly_chart(fig, use_container_width=True)
            export_csv(bar_df, f"{report_scope.replace(' ', '_')}_Weekend_Weekday_Sales.csv")
        else:
            st.warning(ERROR_NO_RECORDS)

    # --- Custom Date Range ---
    elif report_type == "Custom Date Range Reports":
        st.subheader("Select Custom Date Range")
        start_date_input = st.date_input("Start Date:", key="custom_start_date")
        end_date_input = st.date_input("End Date:", key="custom_end_date")

        if start_date_input and end_date_input:
            start_date = datetime.combine(start_date_input, datetime.min.time())
            end_date = datetime.combine(end_date_input, datetime.max.time())

            if start_date > end_date:
                st.error("Start date cannot be after end date.")
            else:
                st.info(f"Generating custom report for: {start_date.strftime(DATE_FORMAT_DMY)} to {end_date.strftime(DATE_FORMAT_DMY)}")
                df = pd.DataFrame(get_sales_data(tname=tname if gname is None else None, gname=gname, start_date=start_date, end_date=end_date))
                if not df.empty:
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.groupby('date')['sales'].sum().reset_index()
                    _display_sales_chart(df, f"{report_scope} - Custom Date Range Sales Report")
                    export_csv(df[['date', 'sales']], f"{report_scope.replace(' ', '_')}_Custom_Sales.csv")
                else:
                    st.warning(ERROR_NO_RECORDS)



def show_forecasting():
    """
    Displays sales forecasting.
    """
    st.subheader("📈 Sales Forecasting")
    _show_back_to_main_menu_option()

    forecast_scope = st.radio("Select Forecast Scope:", ["My Sales", "My Group's Sales"], key="forecast_scope")

    current_tname = st.session_state.tenant_id
    current_gname = st.session_state.gname

    if forecast_scope == "My Group's Sales" and not current_gname:
        st.warning("Your tenant is not associated with a group. Please select 'My Sales'.")
        return

    query_tname = current_tname if forecast_scope == "My Sales" else None
    query_gname = current_gname if forecast_scope == "My Group's Sales" else None

    # Get historical data for forecasting
    # Fetch all time data for better model training
    sales_data = get_sales_data(tname=query_tname, gname=query_gname, all_time=True)

    if not sales_data:
        st.warning(ERROR_NO_RECORDS + " Cannot perform forecasting without historical data.")
        return

    df = pd.DataFrame(sales_data)
    df['date'] = pd.to_datetime(df['date'])
    df = df.groupby('date')['sales'].sum().reset_index() # Aggregate daily sales
    df = df.sort_values('date')

    if len(df) < 2:
        st.warning("Not enough historical data to perform forecasting (need at least 2 data points).")
        return

    st.write(f"Using {len(df)} historical data points from {df['date'].min().strftime(DATE_FORMAT_DMY)} to {df['date'].max().strftime(DATE_FORMAT_DMY)}.")

    forecast_period_days = st.slider("Forecast for next (days):", 7, 30, 7, key="forecast_period_slider")

    # Simple Linear Regression for forecasting
    # Convert dates to numerical values (e.g., days since first date)
    df['days_since_start'] = (df['date'] - df['date'].min()).dt.days

    X = df[['days_since_start']]
    y = df['sales']

    model = LinearRegression()
    model.fit(X, y)

    # Generate future dates for prediction
    last_date = df['date'].max()
    future_dates = [last_date + timedelta(days=i) for i in range(1, forecast_period_days + 1)]
    future_days_since_start = [(d - df['date'].min()).days for d in future_dates]

    # Predict sales for future dates
    future_X = pd.DataFrame({'days_since_start': future_days_since_start})
    predictions = model.predict(future_X)

    forecast_df = pd.DataFrame({
        'date': future_dates,
        'predicted_sales': predictions
    })

    st.subheader("Predicted Sales:")
    st.dataframe(forecast_df.style.format({"predicted_sales": "₹{:,.2f}"}))

    # Plot historical and predicted sales
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['date'], y=df['sales'], mode='lines+markers', name='Historical Sales'))
    fig.add_trace(go.Scatter(x=forecast_df['date'], y=forecast_df['predicted_sales'], mode='lines+markers', name='Predicted Sales', line=dict(dash='dot')))

    fig.update_layout(
        title=f"{forecast_scope} Sales Forecast for Next {forecast_period_days} Days",
        xaxis_title="Date",
        yaxis_title="Sales (₹)",
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.info("Note: This is a simple linear regression forecast. For more accurate predictions, consider advanced time series models (e.g., ARIMA).")

def show_sales_summary_wrapper():
    """
    Wrapper function for sales summary to manage scope selection in UI.
    """
    st.subheader("📋 Sales Summary (All Time)")
    _show_back_to_main_menu_option()

    summary_scope = st.radio("Select Summary Scope:", ["My Sales Summary", "My Group's Sales Summary"], key="summary_scope_radio")

    if summary_scope == "My Sales Summary":
        show_sales_summary_logic(tenant_id=st.session_state.tenant_id, scope="tenant")
    elif summary_scope == "My Group's Sales Summary":
        if not st.session_state.gname:
            st.warning("Your tenant is not associated with a group. Please select 'My Sales Summary'.")
            return
        show_sales_summary_logic(gname=st.session_state.gname, scope="group")

def show_sales_summary_logic(tenant_id: str | None = None, gname: str | None = None, scope: str = "tenant"):
    """
    Displays the all-time sales summary for a tenant or their associated group.
    This function contains the core logic for the summary.
    Args:
        tenant_id (str | None): The tenant ID (for tenant scope).
        gname (str | None): The group name (for group scope).
        scope (str): "tenant" or "group".
    """
    st.info(f"Generating sales summary for scope: {scope}")
    if scope == "tenant":
        current_tname = tenant_id if tenant_id else st.session_state.tenant_id
        sales_data = get_sales_data(tname=current_tname, all_time=True, include_pname=True)
        title_prefix = f"📌 Sales Summary for {current_tname}"
    elif scope == "group":
        current_gname = gname if gname else st.session_state.gname
        if not current_gname:
            st.warning("Your tenant is not associated with a group. Cannot generate group summary.")
            return
        sales_data = get_sales_data(gname=current_gname, all_time=True, include_pname=True)
        title_prefix = f"📌 Group Sales Summary (Group: {current_gname})"
    else:
        st.error("Invalid scope for sales summary.")
        return

    if not sales_data:
        st.warning(ERROR_NO_RECORDS)
        return

    df = pd.DataFrame(sales_data)
    df['date'] = pd.to_datetime(df['date'])

    total_sales = df['sales'].sum()
    num_active_days = df['date'].nunique()
    avg_daily_sale = total_sales / num_active_days if num_active_days > 0 else 0

    # Find highest/lowest sales days and associated properties/tenants
    highest_sale_info = {}
    lowest_sale_info = {}

    if not df.empty:
        # Filter out zero sales for summary's highest/lowest display
        filtered_df_for_min_max = df[df['sales'] > 0.01].copy() # Ensure positive sales

        if not filtered_df_for_min_max.empty:
            # Highest Sale
            highest_sale_row = filtered_df_for_min_max.loc[filtered_df_for_min_max['sales'].idxmax()]
            highest_sale_info = {
                "amount": highest_sale_row['sales'],
                "date": highest_sale_row['date'].strftime(DATE_FORMAT_DMY),
                "pname": highest_sale_row['pname'] if 'pname' in filtered_df_for_min_max.columns else "N/A",
                "tname": highest_sale_row['tname'] if 'tname' in filtered_df_for_min_max.columns else "N/A" # For group
            }

            # Lowest Sale
            lowest_sale_row = filtered_df_for_min_max.loc[filtered_df_for_min_max['sales'].idxmin()]
            lowest_sale_info = {
                "amount": lowest_sale_row['sales'],
                "date": lowest_sale_row['date'].strftime(DATE_FORMAT_DMY),
                "pname": lowest_sale_row['pname'] if 'pname' in filtered_df_for_min_max.columns else "N/A",
                "tname": lowest_sale_row['tname'] if 'tname' in filtered_df_for_min_max.columns else "N/A" # For group
            }
        else: # If all sales are zero or below threshold after filtering
            st.warning("No sales greater than zero found for summary period.")
            return # Exit if no meaningful data for min/max
    else:
        # Default empty values
        highest_sale_info = {"amount": 0, "date": "N/A", "pname": "N/A", "tname": "N/A"}
        lowest_sale_info = {"amount": 0, "date": "N/A", "pname": "N/A", "tname": "N/A"}

    st.markdown(f"**{title_prefix} (All Time)**")
    st.write(f"Total Sales: ₹{total_sales:,.2f}")
    st.write(f"Average Daily Sale: ₹{avg_daily_sale:,.2f}")
    st.write(f"Number of Active Days: {num_active_days}")

    if scope == "tenant":
        st.write(f"Highest Sale: ₹{highest_sale_info['amount']:,.2f} on {highest_sale_info['date']} (Property: {highest_sale_info['pname']})")
        st.write(f"Lowest Sale: ₹{lowest_sale_info['amount']:,.2f} on {lowest_sale_info['date']} (Property: {lowest_sale_info['pname']})")
    elif scope == "group":
        st.write(f"Highest Single-Day Sale in Group: ₹{highest_sale_info['amount']:,.2f} on {highest_sale_info['date']} by {highest_sale_info['tname']} (Property: {highest_sale_info['pname']})")
        st.write(f"Lowest Single-Day Sale in Group: ₹{lowest_sale_info['amount']:,.2f} on {lowest_sale_info['date']} by {lowest_sale_info['tname']} (Property: {lowest_sale_info['pname']})")

def show_leaderboard():
    """
    Displays the all-time sales leaderboard for tenants or groups, with pretty chatbot-style UI.
    """
    st.title("🏆 All-Time Sales Leaderboard")
    _show_back_to_main_menu_option()

    leaderboard_type = st.radio("📊 Show Leaderboard By:", ["Tenants", "Groups"], key="leaderboard_type")

    with st.spinner(f"{DATA_FETCH_INDICATOR_MESSAGE} leaderboard data..."):
        all_sales_data = get_all_tenants_sales()

    if not all_sales_data:
        st.warning(ERROR_NO_RECORDS + " Cannot generate leaderboard without data.")
        append_chat("bot", "Oops! No sales data found yet to build the leaderboard. Go make some sales first! 😅")
        return

    df_all_sales = pd.DataFrame(all_sales_data)

    if leaderboard_type == "Tenants":
        tenant_summary = df_all_sales.groupby('tname')['sales'].sum().reset_index()
        tenant_summary = tenant_summary.sort_values(by='sales', ascending=False).reset_index(drop=True)
        tenant_summary.index = tenant_summary.index + 1

        st.subheader("👤 Top Tenants by All-Time Sales")
        st.dataframe(tenant_summary.style.format({"sales": "₹{:,.2f}"}), use_container_width=True)
        export_csv(tenant_summary, "All_Time_Tenant_Leaderboard.csv")

        # Plotly Bar Chart
        fig = px.bar(tenant_summary,
                     x='tname', y='sales',
                     title="Tenant Sales Chart",
                     labels={'tname': 'Tenant', 'sales': 'Total Sales (₹)'},
                     color='tname',
                     color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_layout(xaxis_title="Tenant", yaxis_title="Total Sales (₹)")
        st.plotly_chart(fig, use_container_width=True)

        append_chat("bot", "Here’s the leaderboard for top-performing tenants! 📈")
        append_chat("bot", "Some serious sales power in here! 💪")

    elif leaderboard_type == "Groups":
        group_summary = df_all_sales.groupby('gname')['sales'].sum().reset_index()
        group_summary = group_summary.sort_values(by='sales', ascending=False).reset_index(drop=True)
        group_summary.index = group_summary.index + 1

        st.subheader("👥 Top Groups by All-Time Sales")
        st.dataframe(group_summary.style.format({"sales": "₹{:,.2f}"}), use_container_width=True)
        export_csv(group_summary, "All_Time_Group_Leaderboard.csv")

        # Plotly Bar Chart
        fig = px.bar(group_summary,
                     x='gname', y='sales',
                     title="Group Sales Chart",
                     labels={'gname': 'Group', 'sales': 'Total Sales (₹)'},
                     color='gname',
                     color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_layout(xaxis_title="Group", yaxis_title="Total Sales (₹)")
        st.plotly_chart(fig, use_container_width=True)

        append_chat("bot", "Here's the group leaderboard! 🏘️ Let’s see which group’s dominating!")
        append_chat("bot", "Teamwork really does make the dream work 💼💥")


def show_help():
    """
    Displays information about the chatbot's capabilities.
    """
    st.subheader("❓ Chatbot Help")
    _show_back_to_main_menu_option()
    st.markdown(CHATBOT_CAPABILITIES)

def handle_creator_access_login():
    """
    Handles the login process for creator access.
    """
    st.subheader("🔑 Creator Access Login")
    password = st.text_input("Enter Creator Password:", type="password", key="creator_password_input")
    login_button = st.button("Login as Creator", key="creator_login_button")

    if login_button:
        if authenticate_creator(password):
            st.session_state.is_creator = True
            st.session_state.current_menu = "creator_menu"
            st.success("Creator login successful!")
            st.rerun()
        else:
            st.error("Invalid Creator Password")

    _show_back_to_main_menu_option()

def show_creator_menu():
    """
    Displays the menu options available only to the creator.
    """
    st.subheader("🛠️ Creator Tools")
    # Button to go back to main menu and logout creator
    if st.button("Back to Main Menu (Logout Creator)", key="creator_logout_button"):
        st.session_state.pop("is_creator", None) # Logout creator
        st.session_state.current_menu = "main" # Go back to tenant main menu
        st.rerun()

    creator_option = st.radio("Choose Creator Option:",
                              ["Show Lowest 10% Tenants", "Admin Reports (Pooled Data)"],
                              key="creator_menu_options")

    if creator_option == "Show Lowest 10% Tenants":
        show_lowest_tenants()
    elif creator_option == "Admin Reports (Pooled Data)":
        show_admin_pooled_reports()

def show_lowest_tenants():
    """
    Identifies and displays the lowest 10% performing tenants by all-time sales.
    """
    st.subheader("📉 Lowest 10% Tenants (All Time Sales)")

    # FIX: Removed 'all_time=True'
    all_sales_data = get_all_tenants_sales()

    if not all_sales_data:
        st.warning(ERROR_NO_RECORDS + " Cannot analyze tenant performance without data.")
        return

    df_all_sales = pd.DataFrame(all_sales_data)

    # Group by tenant and sum sales for all time
    tenant_summary = df_all_sales.groupby('tname')['sales'].sum().reset_index()
    tenant_summary = tenant_summary.sort_values(by='sales', ascending=True).reset_index(drop=True)

    # Calculate 10% threshold
    num_tenants = len(tenant_summary)
    if num_tenants == 0:
        st.info("No tenants found to analyze.")
        return

    num_lowest = max(1, int(num_tenants * 0.10)) # Ensure at least 1 tenant if any exist
    lowest_tenants_df = tenant_summary.head(num_lowest)

    st.write(f"Showing the lowest {num_lowest} tenants based on all-time sales:")
    st.dataframe(lowest_tenants_df.style.format({"sales": "₹{:,.2f}"}))
    export_csv(lowest_tenants_df, "Lowest_10_Percent_Tenants.csv")

def show_admin_pooled_reports():
    """
    Generates reports using pooled data from all tenants (Admin view).
    Similar to show_reports but without tenant/group scope selection.
    """
    st.subheader("🌐 Admin Reports (Pooled Data)")

    report_type = st.radio("Select Report Type for All Tenants:",
                           ["Weekly Reports (Pooled)", "Monthly Reports (Pooled)", "Custom Date Range (Pooled)"],
                           key="admin_report_type_selector")

    start_date, end_date = None, None
    sales_df = pd.DataFrame()

    if report_type == "Weekly Reports (Pooled)":
        today = datetime.now()
        selected_week = st.date_input("Select a date to get its week's pooled report:", value=today, key="admin_weekly_date_input")
        if selected_week:
            start_date, end_date = get_week_start_end(datetime.combine(selected_week, datetime.min.time()))
            st.info(f"Generating pooled weekly report for: {start_date.strftime(DATE_FORMAT_DMY)} to {end_date.strftime(DATE_FORMAT_DMY)}")
            # FIX: Removed 'all_time=True' here as well, rely on start_date/end_date
            sales_data = get_all_tenants_sales(start_date=start_date, end_date=end_date)
            sales_df = pd.DataFrame(sales_data)
            if not sales_df.empty:
                sales_df['date'] = pd.to_datetime(sales_df['date'])
                sales_df = sales_df.groupby('date')['sales'].sum().reset_index()
                _display_sales_chart(sales_df, "All Tenants - Pooled Weekly Sales Report")
                export_csv(sales_df[['date', 'sales']], "All_Tenants_Weekly_Sales.csv")
            else:
                st.warning(ERROR_NO_RECORDS)

    elif report_type == "Monthly Reports (Pooled)":
        today = datetime.now()
        selected_month_date = st.date_input("Select a date to get its month's pooled report:", value=today, key="admin_monthly_date_input")
        if selected_month_date:
            start_date, end_date = get_month_start_end(datetime.combine(selected_month_date, datetime.min.time()))
            st.info(f"Generating pooled monthly report for: {start_date.strftime(DATE_FORMAT_DMY)} to {end_date.strftime(DATE_FORMAT_DMY)}")
            # FIX: Removed 'all_time=True' here as well
            sales_data = get_all_tenants_sales(start_date=start_date, end_date=end_date)
            sales_df = pd.DataFrame(sales_data)
            if not sales_df.empty:
                sales_df['date'] = pd.to_datetime(sales_df['date'])
                sales_df = sales_df.groupby('date')['sales'].sum().reset_index()
                _display_sales_chart(sales_df, "All Tenants - Pooled Monthly Sales Report")
                export_csv(sales_df[['date', 'sales']], "All_Tenants_Monthly_Sales.csv")
            else:
                st.warning(ERROR_NO_RECORDS)

    elif report_type == "Custom Date Range (Pooled)":
        st.subheader("Select Custom Date Range for Pooled Report")
        start_date_input = st.date_input("Start Date (Pooled):", key="admin_custom_start_date")
        end_date_input = st.date_input("End Date (Pooled):", key="admin_custom_end_date")

        if start_date_input and end_date_input:
            start_date_obj = datetime.combine(start_date_input, datetime.min.time())
            end_date_obj = datetime.combine(end_date_input, datetime.max.time()) # End of selected day

            if start_date_obj > end_date_obj:
                st.error("Start date cannot be after end date.")
            else:
                st.info(f"Generating pooled custom report for: {start_date_obj.strftime(DATE_FORMAT_DMY)} to {end_date_obj.strftime(DATE_FORMAT_DMY)}")
                # FIX: Removed 'all_time=True' here as well
                sales_data = get_all_tenants_sales(start_date=start_date_obj, end_date=end_date_obj)
                sales_df = pd.DataFrame(sales_data)
                if not sales_df.empty:
                    sales_df['date'] = pd.to_datetime(sales_df['date'])
                    sales_df = sales_df.groupby('date')['sales'].sum().reset_index()
                    _display_sales_chart(sales_df, "All Tenants - Pooled Custom Date Range Sales Report")
                    export_csv(sales_df[['date', 'sales']], "All_Tenants_Custom_Sales.csv")
                else:
                    st.warning(ERROR_NO_RECORDS)
def handle_logout():
    """
    Handles user logout: clears session and thanks the user.
    """
    st.subheader("🔒 Logout")
    if st.button("Logout"):
        # Clear all session state keys
        for key in list(st.session_state.keys()):
            st.session_state.pop(key)

        # Show the prettier farewell message
        show_farewell()

        st.stop()  # Stop execution so user sees this message and no further UI loads






