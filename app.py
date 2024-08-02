import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import os
from fpdf import FPDF
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


# Prompt for the summarization model
prompt = """You are a YouTube video summarizer. You will be taking the transcript text and summarizing the entire video and providing the important summary in points within 2000 words."""

# Prompt for the question answering model
question_prompt = """You are a helpful assistant that answers questions based on the given context. Here is the context: {}. Answer the following question: {}"""

# Function to extract transcript details from a YouTube video
def extract_transcript_details(youtube_video_url):
    try:
        video_id = youtube_video_url.split("=")[1]
        transcript_text = YouTubeTranscriptApi.get_transcript(video_id)

        transcript = ""
        for i in transcript_text:
            transcript += " " + i["text"]

        return transcript.strip()

    except Exception as e:
        if "Could not retrieve a transcript for the video" in str(e):
            st.error("This video does not have subtitles enabled, so a transcript cannot be retrieved.")
        else:
            st.error(f"Error fetching transcript: {e}")
        return None

# Function to generate content using Gemini model
def generate_gimini_content(transcript_text, prompt):
    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(prompt + transcript_text)
        return response.text if response else "No response received."
    
    except Exception as e:
        st.error(f"Error fetching summary: {e}")
        return None

# Function to answer questions based on the transcript
def answer_question(transcript_text, question):
    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(question_prompt.format(transcript_text, question))
        return response.text if response else "No response received."
    
    except Exception as e:
        st.error(f"Error fetching answer: {e}")
        return None

# Function to extract the video ID from a YouTube link
def get_video_id(youtube_link):
    video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", youtube_link)
    return video_id_match.group(1) if video_id_match else None

# Function to create a PDF with the transcript and summary
def create_pdf(transcript_text, summary_text, filename):
    pdf = FPDF()
    pdf.add_page()
    
    # Title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, 'Detailed Notes', ln=True, align='C')
    pdf.ln(10)

    # Add the summary
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, summary_text)
    pdf.ln(10)

    # Add transcript text with proper formatting
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, 'Transcript:', ln=True)
    pdf.set_font("Arial", size=12)

    # Split by lines for proper formatting
    for line in transcript_text.splitlines():
        pdf.multi_cell(0, 10, line)

    pdf.output(filename)

# Initialize session state for conversation and question
if 'conversation' not in st.session_state:
    st.session_state.conversation = []

if 'question' not in st.session_state:
    st.session_state.question = ""

# Streamlit app layout
st.sidebar.title("YouTube Video To Text Converter")

# Sidebar for YouTube link input and video display
youtube_link = st.sidebar.text_input("Enter video link")

if youtube_link:
    video_id = get_video_id(youtube_link)
    if video_id:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        st.sidebar.video(video_url)  # Embed the video
    else:
        st.sidebar.error("Invalid YouTube link. Please enter a valid video URL.")

# Main section for detailed notes and conversation
st.title("Detailed Notes and Conversation")

# Section for getting detailed notes
if st.sidebar.button("Get Detailed Notes"):
    transcript_text = extract_transcript_details(youtube_link)

    if transcript_text:
        # Store the transcript_text in session state
        st.session_state.transcript_text = transcript_text

        summary = generate_gimini_content(transcript_text, prompt)
        if summary:
            st.markdown("## Detailed Notes")
            st.write(summary)

            # Create and provide download link for the transcript
            create_pdf(transcript_text, summary, "transcript.pdf")
            with open("transcript.pdf", "rb") as pdf_file:
                st.sidebar.download_button("Download Transcript as PDF", pdf_file, file_name="transcript.pdf")

# Custom CSS to fix the position of the input box at the bottom
st.markdown(
    """
    <style>
    .fixed-bottom-input {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background-color: #f3f3f3;
        padding: 10px;
        border-top: 1px solid #ccc;
    }
    .fixed-bottom-input input {
        width: calc(100% - 30px);
        padding: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Placeholder for question and answer section at the bottom
placeholder = st.empty()

# Section for asking questions about the video content
with placeholder.container():
    st.markdown("## Ask a Question About the Video Content")

    # Create a fixed position input box at the bottom
    user_question = st.text_input("Your Question:", st.session_state.question, key='fixed_question', placeholder="Type your question here...", label_visibility="hidden")

    # Process user question if available
    if user_question and 'transcript_text' in st.session_state:
        answer = answer_question(st.session_state.transcript_text, user_question)
        st.session_state.conversation.append({"question": user_question, "answer": answer})

    # Store the question in session state
    st.session_state.question = user_question

    # Display conversation history in reverse order
    st.write("### Conversation History")
    for item in reversed(st.session_state.conversation):
        st.markdown(f"""
            <div style="padding: 10px; background-color: gray; border-radius: 5px;">
                <strong>Question:</strong> {item['question']}
            </div>
            <div style="padding: 10px; border-radius: 5px;">
                <strong>Answer:</strong> {item['answer']}
            </div>
            <br>
        """, unsafe_allow_html=True)
