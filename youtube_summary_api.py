from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import requests
import re
import openai  # Optional
import sys

app = Flask(__name__)

# Optional: Set your OpenAI key
openai.api_key = 'YOUR_OPENAI_API_KEY'  # Or use env vars

def extract_video_id(url):
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
    return match.group(1) if match else None

def get_video_title(video_id):
    try:
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        response = requests.get(oembed_url)
        if response.status_code == 200:
            return response.json().get('title', 'Unknown Title')
        return "Unknown Title"
    except Exception as e:
        print("Title fetch error:", e)
        return "Unknown Title"

def get_transcript(video_id):
    print("In get_transcript", file=sys.stderr, flush=True)
    try:
        print("Available transcripts:", file=sys.stderr, flush=True)
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        for transcript in transcript_list:
            print(f" - {transcript.language} (auto-generated: {transcript.is_generated})", file=sys.stderr, flush=True)

        transcript = transcript_list.find_transcript(['en', 'en-US'])
        return ' '.join([entry.text for entry in transcript.fetch()])
    except (NoTranscriptFound):
        print("NoTranscriptFound error", file=sys.stderr, flush=True)
        return None
    except (TranscriptsDisabled):
        print("TranscriptsDisabled error", file=sys.stderr, flush=True)
        return None
    except Exception as e:
        print("Transcript fetch error:", e)
        return None

def summarize_with_openai(transcript):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant who summarizes YouTube transcripts."},
            {"role": "user", "content": f"Please summarize the following transcript:\n\n{transcript}"}
        ]
    )
    return response.choices[0].message.content.strip()

@app.route('/summarize', methods=['POST'])
def summarize():
    data = request.get_json()
    if not data or 'youtube_url' not in data:
        return jsonify({'error': 'Invalid or missing JSON body'}), 400

    url = data['youtube_url']
    video_id = extract_video_id(url)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL'}), 400

    title = get_video_title(video_id)
    transcript = get_transcript(video_id)

    if not transcript:
        return jsonify({'error': 'Transcript not available'}), 404

    # Return full transcript with title
    return jsonify({'title': title, 'transcript': transcript})

    # Or return summarized transcript:
    # summary = summarize_with_openai(transcript)
    # return jsonify({'title': title, 'summary': summary})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
