from flask import Flask, request, send_file, render_template_string, jsonify
from yt_dlp import YoutubeDL
import os
import subprocess
import requests
import re
import shutil
import random
import time
from functools import wraps

app = Flask(__name__)

# 設置文件保存的路徑
DOWNLOAD_FOLDER = './downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# 用戶代理列表
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15'
]

# 添加更多请求头
HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'TE': 'trailers'
}

def get_headers():
    headers = HEADERS.copy()
    headers['User-Agent'] = get_random_user_agent()
    return headers

def retry_on_error(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        raise e
                    time.sleep(delay * retries)  # 指數退避
            return None
        return wrapper
    return decorator

# 獲取隨機用戶代理
def get_random_user_agent():
    return random.choice(USER_AGENTS)


# 截斷文件名過長的問題
def truncate_title(title, max_length=100):
    return title[:max_length]


# 清理檔名中的特殊字符
def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', '_', filename)


# 轉換秒數為 HH:MM:SS 格式
def seconds_to_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f'{int(hours):02}:{int(minutes):02}:{int(seconds):02}'


# 下載縮略圖
def download_thumbnail(thumbnail_url, output_path):
    response = requests.get(thumbnail_url, stream=True)
    if response.status_code == 200:
        with open(output_path, 'wb') as out_file:
            for chunk in response.iter_content(chunk_size=1024):
                out_file.write(chunk)
    else:
        raise Exception(
            f"Failed to download thumbnail: {response.status_code} - URL: {thumbnail_url}"
        )


# 清理下載資料夾
def clear_download_folder(folder_path):
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Failed to delete {file_path}: {e}")


@app.route('/')
def index():
    return render_template_string('''
        <html>
        <head>
            <title>YouTube to MP3 Converter</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background-color: #f4f4f9;
                    margin: 0;
                    padding: 0;
                }
                .container {
                    max-width: 600px;
                    margin: 50px auto;
                    background-color: #fff;
                    padding: 20px;
                    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
                    border-radius: 10px;
                    text-align: center;
                }
                h1 {
                    color: #333;
                    font-size: 24px;
                    margin-bottom: 20px;
                }
                label {
                    font-size: 16px;
                    color: #555;
                }
                input[type="text"] {
                    width: 100%;
                    padding: 10px;
                    margin: 10px 0;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    font-size: 16px;
                }
                button {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    font-size: 16px;
                    border-radius: 5px;
                    cursor: pointer;
                    margin-top: 20px;
                }
                button:hover {
                    background-color: #45a049;
                }
                .message {
                    color: #555;
                    font-size: 14px;
                    display: none;
                    margin-top: 20px;
                }
                .footer {
                    margin-top: 30px;
                    font-size: 14px;
                    color: #999;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>YouTube to MP3 Converter</h1>
                <form method="POST" action="/download">
                    <label for="url">YouTube Video URL:</label>
                    <input type="text" id="url" name="url" required><br>

                    <label for="start_time">Start Time (format: HH:MM:SS):</label>
                    <input type="text" id="start_time" name="start_time" placeholder="00:00:00"><br>

                    <label for="end_time">End Time (format: HH:MM:SS):</label>
                    <input type="text" id="end_time" name="end_time" placeholder="00:00:00"><br>

                    <input type="hidden" id="video_duration" name="video_duration" value="0">
                    <button type="submit">Download MP3</button>
                </form>

                <div class="message" id="processing-message">
                    <p>Processing your request, please wait...</p>
                </div>

                <div class="footer">
                    <p>Made by peter122701</p>
                </div>
            </div>

            <script>
                document.getElementById("url").addEventListener("blur", function() {
                    const url = this.value;
                    fetch("/get_video_info", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({ url: url })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.duration) {
                            document.getElementById("start_time").value = "00:00:00";
                            document.getElementById("end_time").value = data.duration;
                            document.getElementById("video_duration").value = data.duration;
                        }
                    });
                });

                document.querySelector("form").addEventListener("submit", function() {
                    document.getElementById("processing-message").style.display = "block";
                });
            </script>
        </body>
        </html>
    ''')


@app.route('/get_video_info', methods=['POST'])
@retry_on_error(max_retries=3)
def get_video_info():
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({'error': 'URL is required'}), 400

    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'no_color': True,
            'http_headers': get_headers(),
            'socket_timeout': 10,
            'retries': 3,
            'extractor_retries': 3,
            'fragment_retries': 3
        }

        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            if not info_dict:
                return jsonify({'error': 'Could not fetch video information'}), 400
            
            duration = info_dict.get('duration', 0)  # 影片時長（秒）
            if not duration:
                return jsonify({'error': 'Could not get video duration'}), 400

        duration_str = seconds_to_time(duration)
        return jsonify({'duration': duration_str})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/download', methods=['POST'])
@retry_on_error(max_retries=3)
def download():
    url = request.form.get('url')
    start_time = request.form.get('start_time', '00:00:00')
    end_time = request.form.get('end_time', '')

    if not url:
        return "URL is required", 400

    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, 'one.%(ext)s'),
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'no_color': True,
            'http_headers': get_headers(),
            'socket_timeout': 10,
            'retries': 3,
            'extractor_retries': 3,
            'fragment_retries': 3,
            'external_downloader': 'aria2c',
            'external_downloader_args': ['--min-split-size=1M', '--max-connection-per-server=16']
        }

        # 確保下載目錄存在
        if not os.path.exists(DOWNLOAD_FOLDER):
            os.makedirs(DOWNLOAD_FOLDER)

        with YoutubeDL(ydl_opts) as ydl:
            # 先获取信息而不下载
            info_dict = ydl.extract_info(url, download=False)
            if not info_dict:
                return "Could not get video information", 400

            # 使用不同的选项进行下载
            download_opts = ydl_opts.copy()
            download_opts['format'] = 'bestaudio/best'
            with YoutubeDL(download_opts) as ydl_download:
                info_dict = ydl_download.extract_info(url, download=True)
                
            title = sanitize_filename(info_dict.get('title', 'video'))
            thumbnail_url = info_dict.get('thumbnail', None)
            uploader = info_dict.get('uploader', "Unknown Artist")
            original_audio_file = os.path.join(DOWNLOAD_FOLDER, "one.webm")
            output_mp3_file = os.path.join(DOWNLOAD_FOLDER, f"{title}.mp3")
            thumbnail_file = os.path.join(DOWNLOAD_FOLDER, f"{title}_thumb.jpg")

            if not os.path.exists(original_audio_file):
                return "Download failed", 400

        # 下載縮略圖
        if thumbnail_url:
            try:
                download_thumbnail(thumbnail_url, thumbnail_file)
            except Exception as e:
                print(f"Thumbnail download failed: {e}")
                # 繼續執行，縮略圖不是必需的

        try:
            # 使用 FFmpeg 剪輯指定時間範圍，並將縮略圖作為封面
            ffmpeg_audio_command = f'ffmpeg -y -i "{original_audio_file}" -ss {start_time} -to {end_time} -vn -c:a libmp3lame -b:a 192k -metadata artist="{uploader}" "{output_mp3_file}"'
            subprocess.run(ffmpeg_audio_command, shell=True, check=True)

            # 如果有縮略圖，嵌入到 MP3
            if os.path.exists(thumbnail_file):
                temp_mp3_file = os.path.join(DOWNLOAD_FOLDER, "temp.mp3")
                ffmpeg_cover_command = f'ffmpeg -y -i "{output_mp3_file}" -i "{thumbnail_file}" -map 0:a -map 1 -c:a copy -c:v mjpeg -id3v2_version 3 -metadata:s:v title="Album cover" -metadata:s:v comment="Cover (front)" "{temp_mp3_file}"'
                subprocess.run(ffmpeg_cover_command, shell=True, check=True)
                os.replace(temp_mp3_file, output_mp3_file)

            # 傳送文件
            if os.path.exists(output_mp3_file):
                response = send_file(output_mp3_file, as_attachment=True)
                clear_download_folder(DOWNLOAD_FOLDER)
                return response
            else:
                return "MP3 conversion failed", 500

        except subprocess.CalledProcessError as ffmpeg_error:
            return f"Error while processing audio with FFmpeg: {str(ffmpeg_error)}", 500
        except Exception as e:
            return f"Error: {str(e)}", 500

    except Exception as e:
        return f"Error: {str(e)}", 500

    finally:
        # 確保清理臨時文件
        try:
            clear_download_folder(DOWNLOAD_FOLDER)
        except:
            pass


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000) 