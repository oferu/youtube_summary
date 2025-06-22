from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import yt_dlp
import re
import openai  # Optional

app = Flask(__name__)

# Optional: Set your OpenAI key
openai.api_key = 'YOUR_OPENAI_API_KEY'  # Or use env vars

def extract_video_id(url):
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
    return match.group(1) if match else None

def get_video_title(video_id):
    ydl_opts = {'quiet': True, 'skip_download': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
        return info.get('title', 'Unknown Title')

def get_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = transcript_list.find_transcript(['en', 'en-US'])
        return ' '.join([entry.text for entry in transcript.fetch()])
    except (TranscriptsDisabled, NoTranscriptFound) as e:
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
    url = data.get('youtube_url')
    if not url:
        return jsonify({'error': 'Missing youtube_url'}), 400

    video_id = extract_video_id(url)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL'}), 400

    title = get_video_title(video_id)
    transcript = get_transcript(video_id)

    if not transcript:
        return jsonify({'error': 'Transcript not available'}), 404

    # If you want just the transcript:
    return jsonify({'title': title, 'transcript': transcript})

    # Or if you want the summary:
    # summary = summarize_with_openai(transcript)
    # return jsonify({'title': title, 'summary': summary})

#if __name__ == '__main__':
#    app.run(debug=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
