import os
import tempfile

import streamlit as st
from main import ChatBot

st.set_page_config(page_title="Fortune Teller", page_icon="🔮")

st.title("🔮 Fortune Teller ChatBot")
st.write("Upload one or more documents (PDF, TXT, Word), then ask your question.")

uploaded = st.file_uploader(
    "Upload your documents",
    type=["pdf", "txt", "docx", "doc"],
    accept_multiple_files=True
)

file_paths: list[str] = []
if uploaded:
    tempdir = tempfile.mkdtemp()
    for file in uploaded:
        dest = os.path.join(tempdir, file.name)
        with open(dest, "wb") as f:
            f.write(file.getbuffer())
        file_paths.append(dest)
bot = ChatBot(file_paths=file_paths if file_paths else None)

st.write("---")
question = st.text_input("Your question:", "")

if st.button("Ask"):
    if not question.strip():
        st.warning("Please enter a question before submitting.")
    else:
        with st.spinner("Gazing into the crystal ball..."):
            answer = bot.ask(question)
        st.markdown(f"**Answer:** {answer}")
