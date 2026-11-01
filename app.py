from flask import Flask, render_template, request, jsonify
import yt_dlp
import json
import os
import requests

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

    ydl_opts = {
        'extract_flat': True,
        'no_warnings': True,
        'quiet': True,
        'playlistend': 12,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web']
            }
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch12:{query}", download=False)
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

@app.route('/api/resolve', methods=['POST'])
def resolve_video():
    data = request.get_json() or {}
    video_id = data.get('video_id', '').strip()
    
    if not video_id:
        return jsonify({'success': False, 'error': 'Thiếu Video ID'}), 400

    stream_url = None
    title = "YouTube Video"

# Danh sách Invidious instance công cộng hoạt động ổn định
    invidious_instances = [
        "https://invidious.privacyredirect.com",
        "https://vid.priv.au",
        "https://invidious.nerdvpn.de",
        "https://invidious.protokolla.fi"
    ]
    
    for instance in invidious_instances:
        try:
            api_url = f"{instance}/api/v1/videos/{video_id}"
            res = requests.get(api_url, timeout=3)
            if res.status_code == 200:
                vid_data = res.json()
                title = vid_data.get('title', title)
                adaptive_streams = vid_data.get('adaptiveFormats', [])
                for s in adaptive_streams:
                    if s.get('type', '').startswith('video/mp4') and '1080' in str(s.get('qualityLabel', '')):
                        stream_url = s.get('url')
                        break
                if not stream_url and adaptive_streams:
                    stream_url = adaptive_streams[0].get('url')
                if stream_url:
                    break
        except Exception:
            continue

    # 2. Dự phòng bằng Piped API
    if not stream_url:
        piped_instances = [
            "https://pipedapi.kavin.rocks",
            "https://pipedapi.projectsegfau.lt"
        ]
        for instance in piped_instances:
            try:
                api_url = f"{instance}/streams/{video_id}"
                res = requests.get(api_url, timeout=3)
                if res.status_code == 200:
                    vid_data = res.json()
                    title = vid_data.get('title', title)
                    video_streams = vid_data.get('videoStreams', [])
                    for s in video_streams:
                        if s.get('quality') == '1080p' and s.get('url'):
                            stream_url = s.get('url')
                            break
                    if not stream_url and video_streams:
                        stream_url = video_streams[0].get('url')
                    if stream_url:
                        break
            except Exception:
                continue

    # 3. Phương án dự phòng cuối cùng: Trả về link trực tiếp trang nhúng YouTube nếu các API đều nghẽn
    if not stream_url:
        # Sử dụng link embed chính hãng để giao diện web tự động hiển thị iframe phát video mượt mà không lo chết API
        return jsonify({
            'success': True,
            'is_embed': True,
            'title': title,
            'stream_url': f"https://www.youtube.com/embed/{video_id}?autoplay=1&enablejsapi=1"
        })

    return jsonify({
        'success': True,
        'is_embed': False,
        'title': title,
        'stream_url': stream_url
    })

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
