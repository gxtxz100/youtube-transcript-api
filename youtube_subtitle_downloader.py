import re
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import os
import time

def extract_video_id(url):
    """从YouTube URL中提取视频ID"""
    try:
        # 处理多种可能的YouTube URL格式
        if "youtu.be" in url:
            return url.split("/")[-1]
        elif "youtube.com" in url:
            if "watch?v=" in url:
                return url.split("watch?v=")[1].split("&")[0]
            elif "embed/" in url:
                return url.split("embed/")[1].split("?")[0]
        return None
    except Exception:
        return None

def get_video_title(video_id):
    """获取视频标题（简化版，仅使用视频ID）"""
    return f"video_{video_id}"

def get_bilingual_subtitles(video_id):
    """获取双语字幕"""
    try:
        print(f"正在获取视频 {video_id} 的字幕...")
        
        # 获取字幕列表
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # 尝试获取英文字幕
        try:
            print("尝试获取英文字幕...")
            en_transcript = transcript_list.find_transcript(['en'])
            en_subs = en_transcript.fetch()
            print("成功获取英文字幕")
        except Exception as e:
            print(f"无法获取英文字幕 ({str(e)})，尝试使用自动翻译...")
            try:
                # 获取任意可用字幕并翻译成英文
                available_transcripts = list(transcript_list.transcript_data.keys())
                if not available_transcripts:
                    raise Exception("没有可用的字幕")
                    
                original = transcript_list.find_transcript(available_transcripts)
                en_subs = original.translate('en').fetch()
                print("成功通过翻译获取英文字幕")
            except Exception as e:
                print(f"获取英文字幕失败: {str(e)}")
                return None

        # 获取中文字幕（通过翻译英文字幕）
        print("正在获取中文字幕...")
        try:
            zh_subs = en_transcript.translate('zh-Hans').fetch()
            print("成功获取中文字幕")
        except Exception as e:
            print(f"获取中文字幕失败: {str(e)}")
            return None

        # 确保两个字幕列表长度相同
        if len(en_subs) != len(zh_subs):
            print(f"警告：英文字幕数量({len(en_subs)})和中文字幕数量({len(zh_subs)})不匹配！")
            print("尝试按时间戳对齐字幕...")
            # 返回字幕，让format_subtitles函数处理对齐
            return en_subs, zh_subs

        return en_subs, zh_subs

    except Exception as e:
        print(f"处理视频 {video_id} 时出错: {str(e)}")
        return None

def format_subtitles(en_subs, zh_subs):
    """格式化字幕输出"""
    formatted_text = "=== 双语字幕 ===\n\n"
    
    # 创建时间戳到字幕的映射
    en_dict = {sub['start']: sub for sub in en_subs}
    zh_dict = {sub['start']: sub for sub in zh_subs}
    
    # 获取所有时间戳并排序
    all_timestamps = sorted(set(en_dict.keys()) | set(zh_dict.keys()))
    
    for timestamp in all_timestamps:
        formatted_text += f"[{format_time(timestamp)}]\n"
        
        # 获取最接近的英文字幕
        en_sub = en_dict.get(timestamp, {'text': '[未找到对应英文]'})
        # 获取最接近的中文字幕
        zh_sub = zh_dict.get(timestamp, {'text': '[未找到对应中文]'})
        
        formatted_text += f"EN: {en_sub['text']}\n"
        formatted_text += f"中文: {zh_sub['text']}\n\n"
    
    return formatted_text

def format_time(seconds):
    """将秒数转换为时:分:秒格式"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def main():
    print("\n=== YouTube双语字幕下载工具 ===\n")
    
    # 获取输入文件路径
    while True:
        input_file = input("请输入包含YouTube链接的txt文件路径: ").strip()
        if os.path.exists(input_file):
            break
        print("文件不存在，请重新输入！")

    # 创建输出目录
    output_dir = "youtube_subtitles"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"\n创建输出目录: {output_dir}")

    # 读取并处理每个URL
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            urls = [url.strip() for url in f.readlines() if url.strip()]
        
        if not urls:
            print("输入文件为空！")
            return
            
        print(f"\n找到 {len(urls)} 个YouTube链接")
        
        success_count = 0
        for index, url in enumerate(urls, 1):
            print(f"\n处理第 {index}/{len(urls)} 个视频")
            print(f"URL: {url}")
            
            video_id = extract_video_id(url)
            if not video_id:
                print("无效的YouTube URL，跳过...")
                continue

            # 获取字幕
            result = get_bilingual_subtitles(video_id)
            if not result:
                print("获取字幕失败，跳过...")
                continue

            en_subs, zh_subs = result
            
            # 格式化并保存字幕
            output_text = format_subtitles(en_subs, zh_subs)
            output_file = os.path.join(output_dir, f"{get_video_title(video_id)}.txt")
            
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(output_text)
                print(f"字幕已保存到: {output_file}")
                success_count += 1
            except Exception as e:
                print(f"保存字幕文件时出错: {str(e)}")
            
            # 添加短暂延迟，避免请求过快
            time.sleep(1)

        print(f"\n处理完成！成功下载 {success_count}/{len(urls)} 个视频的字幕")
        print(f"字幕文件保存在 '{output_dir}' 目录下")

    except Exception as e:
        print(f"读取输入文件时出错: {str(e)}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序已被用户中断")
    except Exception as e:
        print(f"\n程序发生错误: {str(e)}")
    finally:
        input("\n按回车键退出...") 