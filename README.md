# YouTube to MP3 Converter

一个基于Flask的YouTube视频转MP3下载器。

## 功能特点

- 支持YouTube视频下载并转换为MP3
- 可以指定视频的开始和结束时间
- 自动获取视频时长
- 支持添加视频缩略图作为MP3封面
- 包含艺术家等元数据

## 部署要求

- Python 3.8+
- FFmpeg
- 其他依赖见 requirements.txt

## 本地运行步骤

1. 克隆仓库：
```bash
git clone [你的仓库URL]
cd [仓库名]
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 安装FFmpeg（如果还没有安装）

4. 运行应用：
```bash
python app.py
```

## 部署说明

本应用可以部署到支持Python的云平台，如Heroku：

1. 创建Heroku账号
2. 安装Heroku CLI
3. 登录Heroku
4. 创建新应用
5. 推送代码到Heroku

## 注意事项

- 确保服务器已安装FFmpeg
- 需要足够的存储空间用于临时文件
- 建议设置适当的超时时间 