# streamlit_app.py

import streamlit as st
st.set_page_config(page_title="Fortune Teller", page_icon="🔮")  # Must come before any other st.* calls

from main import ChatBot

@st.cache_resource
def load_bot():
    return ChatBot()

bot = load_bot()

st.title("🔮 Fortune Teller ChatBot")
st.write("Ask a question about your life, and the fortune teller will respond in two concise sentences.")

question = st.text_input("Your question:", "")

if st.button("Ask"):
    if not question.strip():
        st.warning("Please enter a question before submitting.")
    else:
        with st.spinner("Gazing into the crystal ball..."):
            answer = bot.ask(question)
        st.markdown(f"**Answer:** {answer}")
