from flask import Flask, render_template, request, jsonify
import yt_dlp
import json
import os

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
                    # Lấy thumbnail chuẩn từ YouTube ID
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

    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Đã cập nhật định dạng ưu tiên chất lượng Full HD (1080p)
    ydl_opts = {
        'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]',
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'web']
            }
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            return jsonify({
                'success': True,
                'title': info.get('title'),
                'stream_url': info.get('url')
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)