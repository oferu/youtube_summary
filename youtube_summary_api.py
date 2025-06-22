from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import openai
import re
import os

app = Flask(__name__)

# Set your OpenAI API key as environment variable before running
openai.api_key = os.getenv("OPENAI_API_KEY")

def extract_video_id(url):
    # Extracts video ID from YouTube URL (supports various formats)
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(regex, url)
    if match:
        return match.group(1)
    return None

def get_video_title(video_id):
    # Simple way to get video title by calling YouTube oEmbed API (no auth needed)
    import requests
    oembed_url = f"https://www.youtube.com/oembed?url=http://www.youtube.com/watch?v={video_id}&format=json"
    resp = requests.get(oembed_url)
    if resp.status_code == 200:
        return resp.json().get("title")
    return None

def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        return ' '.join([entry.text for entry in transcript])
    except (TranscriptsDisabled, NoTranscriptFound):
        return None
    except Exception as e:
        print("Error fetching transcript:", e)
        return None

def summarize_with_openai(text):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant who summarizes YouTube video transcripts."},
                {"role": "user", "content": f"Summarize this transcript briefly:\n\n{text}"}
            ],
            max_tokens=150,
            temperature=0.7,
        )
        summary = response.choices[0].message['content'].strip()
        return summary
    except Exception as e:
        print("OpenAI API error:", e)
        return None

@app.route('/summarize', methods=['POST'])
def summarize():
    data = request.get_json()
    if not data or 'youtube_url' not in data:
        return jsonify({'error': 'Missing youtube_url in request'}), 400

    url = data['youtube_url']
    video_id = extract_video_id(url)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL'}), 400

    title = get_video_title(video_id)
    if not title:
        title = "Unknown Title"

    transcript = get_transcript(video_id)
    if not transcript:
        return jsonify({'error': 'Transcript not available'}), 404

    summary = summarize_with_openai(transcript)
    if not summary:
        return jsonify({'error': 'Failed to summarize transcript'}), 500

    return jsonify({
        'title': title,
        'summary': summary
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
