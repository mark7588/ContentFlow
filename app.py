import os
from flask import Flask, request, render_template, redirect, url_for
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound
import google.generativeai as genai
import re
from dotenv import load_dotenv

# Load environment variables from .env file (if it exists)
load_dotenv()

app = Flask(__name__)

# --- Configure Google Gemini API ---
# Get API key from environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables. Please set it.")

genai.configure(api_key=GEMINI_API_KEY)
# Use a supported Gemini model. If you get a 404 error, check the available models for your API key.
model = genai.GenerativeModel('gemini-1.5-flash-latest')  # Try this model, or use ListModels to find others

# --- Helper function to extract YouTube video ID ---
def get_video_id(url):
    # Regex to extract video ID from various YouTube URL formats
    pattern = r'(?:https?://)?(?:www\.)?(?:m\.)?(?:youtube\.com|youtu\.be)/(?:watch\?v=|embed/|v/|)([\w-]{11})(?:\S+)?'
    match = re.match(pattern, url)
    if match:
        return match.group(1)
    return None

# --- Function to get YouTube transcript ---
def get_youtube_transcript(video_id):
    try:
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        try:
            transcript_obj = transcripts.find_manually_created_transcript(['en'])
            return transcript_obj.fetch()
        except Exception:
            try:
                transcript_obj = transcripts.find_transcript(['en'])
                return transcript_obj.fetch()
            except Exception:
                try:
                    for transcript in transcripts:
                        transcript_obj = transcript
                        return transcript_obj.fetch()
                except Exception:
                    return None
    except Exception:
        return None

# --- Function to summarize text using Gemini ---
def summarize_text(text):
    prompt = f"""
    You are an expert summarizer. Your task is to provide a concise and clear summary of the following text. The transcript is from a YouTube video.
    Also, extract 5 main key points from the video. You can add more key points if you find them relevant.

    ---
    Video Transcript:
    {text}
    ---

    Please format your output as follows:

    **Summary:**
    [Your concise summary here]

    **Main Points:**
    * [Key Point 1]
    * [Key Point 2]
    * [Key Point 3]
    * ...
    """
    try:
        response = model.generate_content(prompt)
        # Access content via .text and handle potential errors
        return response.text
    except Exception as e:
        print(f"Error summarizing with Gemini: {e}")
        return f"Error: Could not summarize the content. {e}"

# --- Flask Routes ---

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        youtube_url = request.form['youtube_url']
        video_id = get_video_id(youtube_url)

        if not video_id:
            return render_template('summary.html', error="Invalid YouTube URL. Please provide a valid link.")

        transcript = get_youtube_transcript(video_id)

        if not transcript:
            return render_template('summary.html', error="Could not retrieve transcript for this video. It might not have one or be in a language without an available transcript.")

        summary_and_points = summarize_text(transcript)

        return render_template('summary.html', summary_content=summary_and_points, video_url=youtube_url)
    return render_template('summary.html', summary_content=None) # Initial GET request


if __name__ == '__main__':
    app.run(debug=True) # debug=True allows automatic reloading on code changes