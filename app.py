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

def fetch_from_instance(instance, video_id):
    try:
        api_url = f"{instance}/api/v1/videos/{video_id}"
        res = requests.get(api_url, timeout=3) # Timeout nhanh để không bị treo
        if res.status_code == 200:
            vid_data = res.json()
            title = vid_data.get('title', 'YouTube Video')
            adaptive_streams = vid_data.get('adaptiveFormats', [])
            # Ưu tiên lấy stream mp4 độ phân giải cao vừa phải để chạy mượt trên xe
            for s in adaptive_streams:
                if s.get('type', '').startswith('video/mp4') and 'url' in s:
                    return {'title': title, 'stream_url': s.get('url')}
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

    result_data = None
    # Gọi đồng thời các server để lấy kết quả nhanh nhất (bỏ qua server chậm)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(fetch_from_instance, inst, video_id) for inst in invidious_instances]
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
    
    # Fallback dự phòng cuối cùng nếu quét instances mất kết nối
    return jsonify({
        'success': True,
        'is_embed': True,
        'title': 'YouTube Stream',
        'stream_url': f"https://www.youtube.com/embed/{video_id}?autoplay=1&enablejsapi=1"
    })

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
