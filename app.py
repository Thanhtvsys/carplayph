from flask import Flask, render_template, request, jsonify
import yt_dlp
import json
import os
import requests
import concurrent.futures

app = Flask(__name__)

def load_playlist():
    json_path = os.path.join(os.path.dirname(__file__), 'playlist.json')
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return []

@app.route('/')
def index():
    categories = load_playlist()
    return render_template('index.html', categories=categories)

@app.route('/api/search', methods=['GET'])
def search_videos():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'success': False, 'videos': []})

    if query == "FAVORITES_CUSTOM":
        return jsonify({'success': True, 'videos': []})

    ydl_opts = {
        'extract_flat': True,
        'no_warnings': True,
        'quiet': True,
        'playlistend': 15,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web']
            }
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch15:{query}", download=False)
            videos = []
            for entry in info.get('entries', []):
                vid = entry.get('id')
                if vid:
                    thumb = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
                    videos.append({
                        'id': vid,
                        'title': entry.get('title'),
                        'uploaderName': entry.get('uploader', 'YouTube'),
                        'thumbnail': thumb
                    })
            if videos:
                return jsonify({'success': True, 'videos': videos})
    except Exception:
        pass

    return jsonify({'success': False, 'videos': []})

def fetch_from_invidious(instance, video_id):
    try:
        api_url = f"{instance}/api/v1/videos/{video_id}"
        res = requests.get(api_url, timeout=2.5)
        if res.status_code == 200:
            vid_data = res.json()
            title = vid_data.get('title', 'YouTube Video')
            adaptive_streams = vid_data.get('adaptiveFormats', [])
            stream_url = None
            for s in adaptive_streams:
                if s.get('type', '').startswith('video/mp4') and '1080' in str(s.get('qualityLabel', '')):
                    stream_url = s.get('url')
                    break
            if not stream_url and adaptive_streams:
                stream_url = adaptive_streams[0].get('url')
            if stream_url:
                return {'title': title, 'stream_url': stream_url}
    except Exception:
        pass
    return None

def fetch_from_piped(instance, video_id):
    try:
        api_url = f"{instance}/streams/{video_id}"
        res = requests.get(api_url, timeout=2.5)
        if res.status_code == 200:
            vid_data = res.json()
            title = vid_data.get('title', 'YouTube Video')
            video_streams = vid_data.get('videoStreams', [])
            stream_url = None
            for s in video_streams:
                if s.get('quality') == '1080p' and s.get('url'):
                    stream_url = s.get('url')
                    break
            if not stream_url and video_streams:
                stream_url = video_streams[0].get('url')
            if stream_url:
                return {'title': title, 'stream_url': stream_url}
    except Exception:
        pass
    return None

@app.route('/api/resolve', methods=['POST'])
def resolve_video():
    data = request.get_json() or {}
    video_id = data.get('video_id', '').strip()
    
    if not video_id:
        return jsonify({'success': False, 'error': 'Thiếu Video ID'}), 400

    invidious_instances = [
        "https://invidious.privacyredirect.com",
        "https://vid.priv.au",
        "https://invidious.nerdvpn.de",
        "https://invidious.protokolla.fi"
    ]
    
    piped_instances = [
        "https://pipedapi.kavin.rocks",
        "https://pipedapi.projectsegfau.lt"
    ]

    result_data = None

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = []
        for inst in invidious_instances:
            futures.append(executor.submit(fetch_from_invidious, inst, video_id))
        for inst in piped_instances:
            futures.append(executor.submit(fetch_from_piped, inst, video_id))
            
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                result_data = res
                break

    if result_data and result_data.get('stream_url'):
        return jsonify({
            'success': True,
            'is_embed': False,
            'title': result_data['title'],
            'stream_url': result_data['stream_url']
        })
    
    return jsonify({
        'success': True,
        'is_embed': True,
        'title': 'YouTube Stream',
        'stream_url': f"https://www.youtube.com/embed/{video_id}?autoplay=1&enablejsapi=1"
    })

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
