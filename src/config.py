# src/config.py

# LLM Configuration
LLAMA_MODEL = "llama3-8b-8192" # Or "llama3-70b-8192" if you have access and prefer it.

# Database Configuration (Placeholder - replace with actual MongoDB connection string in .env)
MONGO_DB_CONNECTION_STRING = "mongodb://localhost:27017/" # Or your remote MongoDB connection string

# Database Names - CORRECTED!
DB_NAME = "predictive"
SALES_COLLECTION = "newDB"

# Error Messages
ERROR_NO_RECORDS = "🚫 No records found for the specified period."
ERROR_LLM_API_FAILURE = "An error occurred while connecting to the AI. Please check your API key and network connection."
ERROR_UNCLEAR_QUERY = "I'm sorry, I couldn't understand your request. Could you please rephrase it or be more specific?"
ERROR_CREATOR_AUTH_FAILED = "Creator authentication failed."
ERROR_GENERAL = "An unexpected error occurred. Please try again."

# Navigation and UI Messages
NAV_BACK_MESSAGE = "⬅️ Back to Main Menu"

# Chatbot Capabilities/Help Text
CHATBOT_CAPABILITIES = """
**I can help you with your sales data! Here are some things you can ask me:**

* **Daily Sales:** "What were my sales on [date]?" (e.g., "What were my sales on June 1st?")
* **Period Sales:** "Show sales from [start date] to [end date]?" (e.g., "Sales from May 1st to May 15th")
* **Monthly Sales:** "What was my monthly sale?" or "Show sales for August?"
* **Weekly Sales:** "What were my sales this week?" or "Show sales for the week of June 10th?"
* **Highest/Lowest Sales:** "When was my highest sale?" or "What was the lowest sale last year?"
* **Sales Summary:** "Tell me about my overall sales."
* **Group Performance:** You can ask about your group's performance by including "my group" or your group name (e.g., "How did my group perform this month?").
* **Properties:** "Show me sales for propertyX." (You can include specific property names in your queries).
* **Reports:** I can generate detailed reports for specific periods.
* **Forecasting:** I can provide simple sales forecasts.
* **Leaderboard:** See how tenants or groups rank by sales.

**Try asking me:**
* "What were my sales yesterday?"
* "Show me sales for property 'Alpha' last week."
* "How much did my group sell in April 2024?"
* "When was the highest sale for 'property2'?"
* "Give me a summary of my all-time sales."
"""

# Date Formats
DATE_FORMAT_ISO = "%Y-%m-%d"
DATE_FORMAT_DMY = "%d %B %Y"

# --- New UI/UX Constants ---
TYPING_INDICATOR_MESSAGE = "SalesBot is thinking..."
LLM_TYPING_INDICATOR_DURATION_SECONDS = 3 # Simulate thinking time for LLM responses
DATA_FETCH_INDICATOR_MESSAGE = "Fetching data..."
DATA_PROCESSING_INDICATOR_MESSAGE = "Analyzing data..."

# Quick Action Buttons (for main menu)
QUICK_ACTIONS = [
    "Overall Sales Summary",
    "This Month's Sales",
    "Highest Sale Ever",
    "Lowest Sale Ever",
    "Show help"
]
