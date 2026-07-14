
import streamlit as st

# --- Greeting Box ---
def show_greeting():
    st.markdown(
        """
        <div style='background: linear-gradient(135deg, #a0e9e0, #007c91); padding: 1.8rem; border-radius: 1rem; color: #002f3d; font-family: "Trebuchet MS", sans-serif; box-shadow: 0 6px 18px rgba(0, 0, 0, 0.25);'>
            <h2 style='margin-bottom: 0.5rem;'>🌊 Welcome aboard!</h2>
            <p style='font-size: 1.1rem; margin-bottom: 0.3rem;'>
                I'm <strong>Alexis</strong> – your personal sales co-pilot 🧭
            </p>
            <p style='font-size: 1rem;'>
                Need <strong>reports</strong> 📊, <strong>forecasts</strong> 📈, or a quick <strong>summary</strong> 🧾?
                Just ask away! 💬
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

# --- Farewell Box ---
def show_farewell():
    st.markdown(
        """
        <style>
        .farewell-box {
            background: linear-gradient(135deg, #4ca1af, #2c3e50);
            border-radius: 15px;
            padding: 30px;
            margin: 20px auto;
            max-width: 600px;
            color: #e0f7fa;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            text-align: center;
            box-shadow: 0 8px 16px rgba(0,0,0,0.3);
        }
        .farewell-emoji {
            font-size: 60px;
            margin-bottom: 15px;
            display: block;
        }
        .farewell-text {
            font-size: 22px;
            font-weight: 600;
            line-height: 1.4;
        }
        </style>
        <div class="farewell-box">
            <span class="farewell-emoji">🌟</span>
            <div class="farewell-text">
                Thanks for chatting with Alexis!<br>
                Have a fantastic day ahead! 😊
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# --- Chat Bubble UI ---
def show_chat_bubble(role, message):
    if not message:
        message = "⚠️ (Empty message)"
    bubble_color = "#d6f5f1" if role == "user" else "#b9e7e0"
    align = "flex-end" if role == "user" else "flex-start"
    border_radius = "20px 20px 0 20px" if role == "user" else "20px 20px 20px 0"

    st.markdown(f"""
        <div style="display: flex; justify-content: {align}; margin: 0.4rem 0;">
            <div style="background-color: {bubble_color}; color: #002f3d; padding: 0.9rem 1.2rem; border-radius: {border_radius}; max-width: 75%; font-family: 'Segoe UI', sans-serif; box-shadow: 2px 4px 12px rgba(0,0,0,0.1);">
                {message}
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- Login Box ---
def show_login_box():
    st.markdown(
        """
        <div style='background: linear-gradient(145deg, #a7ede7, #007c91); padding: 2rem; border-radius: 1rem; color: #002f3d; font-family: "Trebuchet MS", sans-serif; box-shadow: 0px 8px 20px rgba(0,0,0,0.3);'>
            <h3>🔐 Tenant Login</h3>
            <p style='font-size: 1rem;'>Please enter your <strong>Tenant ID</strong> below to access the SalesBot dashboard.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
