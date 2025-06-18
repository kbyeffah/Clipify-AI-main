# #!/usr/bin/env python3
# """
# Complete Fast Video Analysis Script with Intelligent Chapter Generation
# Optimized for speed with Groq-powered content analysis and Whisper transcription
# """

# import sys
# import json
# import asyncio
# import os
# import tempfile
# import time
# import re
# from pathlib import Path
# from concurrent.futures import ThreadPoolExecutor
# from typing import Dict, List, Optional, Any
# import base64

# # Core dependencies
# import yt_dlp
# import whisper
# from youtube_transcript_api import YouTubeTranscriptApi
# from moviepy import VideoFileClip
# import numpy as np
# from PIL import Image
# from groq import Groq

# class FastVideoAnalyzer:
#     def __init__(self):
#         try:
#             self.temp_dir = tempfile.mkdtemp()
#             os.chmod(self.temp_dir, 0o755)  # Ensure write permissions
#             print(f"Temp directory created: {self.temp_dir}", file=sys.stderr)
#         except PermissionError as e:
#             print(f"Permission error creating temp dir: {e}, falling back to system temp", file=sys.stderr)
#             self.temp_dir = tempfile.gettempdir()
#         self.whisper_model = None
        
#         self.groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
#         if not os.getenv('GROQ_API_KEY'):
#             raise ValueError("GROQ_API_KEY environment variable is not set")
        
#         self.ydl_opts_base = {
#             'quiet': True,
#             'no_warnings': True,
#             'extract_flat': False,
#             'writesubtitles': False,
#             'writeautomaticsub': False,
#             'progress': False,
#             'noprogress': True,
#             'logtostderr': True,
#             'restrictfilenames': True,
#         }

#     def clean_text_for_json(self, text: str) -> str:
#         if not text:
#             return ""
#         text = text.replace('\u200b', '').replace('\u200c', '').replace('\u200d', '')
#         text = text.replace('\u200e', '').replace('\u200f', '').replace('…', '...')
#         text = re.sub(r'[^\x00-\x7F\u00A0-\u024F\u1E00-\u1EFF\u2000-\u206F\u2070-\u209F\u20A0-\u20CF\u2100-\u214F]', '', text)
#         return text.strip()

#     async def analyze_video(self, youtube_url: str) -> Dict[str, Any]:
#         start_time = time.time()
#         try:
#             print("🚀 Starting video analysis...", file=sys.stderr)
            
#             video_id = self.extract_video_id(youtube_url)
#             if not video_id:
#                 raise ValueError("Invalid YouTube URL")
            
#             print(f"📹 Video ID: {video_id}", file=sys.stderr)
            
#             metadata_task = self.get_metadata_fast(youtube_url)
#             transcript_task = self.get_transcript_fast(video_id)
#             download_task = self.download_video_optimized(youtube_url)
            
#             print("⏳ Launching async tasks...", file=sys.stderr)
#             metadata, transcript, video_path = await asyncio.gather(
#                 metadata_task, transcript_task, download_task
#             )
            
#             print(f"✅ Metadata fetched: {metadata.get('title', 'Unknown')[:50]}...", file=sys.stderr)
#             print(f"✅ Transcript fetched: {len(transcript)} segments (or none if disabled)", file=sys.stderr)
#             print(f"✅ Video downloaded: {bool(video_path)} at {video_path if video_path else 'None'}", file=sys.stderr)
            
#             partial_path = None
#             if video_path and os.path.exists(video_path):
#                 print(f"Verifying video file: {video_path}, size: {os.path.getsize(video_path)} bytes", file=sys.stderr)
#                 if not transcript:
#                     print("No transcript found, transcribing audio with Whisper...", file=sys.stderr)
#                     whisper_transcript = await self.transcribe_with_whisper(video_path)
#                     if whisper_transcript:
#                         transcript = whisper_transcript
#                         print(f"✅ Whisper transcription: {len(transcript)} segments", file=sys.stderr)
#                     else:
#                         print("⚠️ Whisper transcription failed, no transcript available.", file=sys.stderr)
#             elif any(f.startswith('video.') for f in os.listdir(self.temp_dir)):
#                 partial_path = next((os.path.join(self.temp_dir, f) for f in os.listdir(self.temp_dir) if f.startswith('video.')), None)
#                 if partial_path and os.path.getsize(partial_path) > 0:
#                     print(f"Verifying partial file: {partial_path}, size: {os.path.getsize(partial_path)} bytes", file=sys.stderr)
#                     print(f"Using partial file {partial_path} for Whisper transcription...", file=sys.stderr)
#                     whisper_transcript = await self.transcribe_with_whisper(partial_path)
#                     if whisper_transcript:
#                         transcript = whisper_transcript
#                         print(f"✅ Whisper transcription from partial file: {len(transcript)} segments", file=sys.stderr)
#                     else:
#                         print("⚠️ Whisper transcription from partial file failed.", file=sys.stderr)
#                 else:
#                     print("⚠️ No transcript available, skipping transcription.", file=sys.stderr)
#             else:
#                 print("⚠️ No transcript available, skipping transcription.", file=sys.stderr)
            
#             key_frames = []
#             if video_path and os.path.exists(video_path):
#                 print("🖼️ Extracting key frames...", file=sys.stderr)
#                 key_frames = await self.extract_key_frames(video_path)
#                 print(f"✅ Key frames: {len(key_frames)}", file=sys.stderr)
#             elif partial_path and os.path.exists(partial_path):
#                 print("🖼️ Extracting key frames from partial file...", file=sys.stderr)
#                 key_frames = await self.extract_key_frames(partial_path)
#                 print(f"✅ Key frames from partial file: {len(key_frames)}", file=sys.stderr)
#             else:
#                 print("⚠️ Skipping key frame extraction due to missing video.", file=sys.stderr)
            
#             print("🧠 Creating intelligent chapters based on content...", file=sys.stderr)
#             chapters = await self.analyze_content_and_create_chapters(transcript or [], metadata)
#             print(f"✅ Intelligent chapters: {len(chapters)}", file=sys.stderr)
            
#             result = {
#                 'success': True if video_path and os.path.exists(video_path) and transcript else False,
#                 'video_id': video_id,
#                 'metadata': metadata,
#                 'transcript': transcript,
#                 'chapters': chapters,
#                 'keyFrames': key_frames,
#                 'processing_time': time.time() - start_time,
#                 'stats': {
#                     'transcript_segments': len(transcript),
#                     'chapters_generated': len(chapters),
#                     'key_frames_extracted': len(key_frames),
#                     'transcript_source': 'whisper' if (video_path and whisper_transcript) or (partial_path and whisper_transcript) else 'youtube_api' if transcript else 'none',
#                     'chapter_method': 'llm_content_analysis'
#                 }
#             }
            
#             print(f"🎉 Analysis complete in {result['processing_time']:.1f}s", file=sys.stderr)
#             self.cleanup()  # Moved here to preserve files until result is processed
#             return result
#         except Exception as e:
#             error_result = {
#                 'success': False,
#                 'error': str(e),
#                 'video_id': video_id if 'video_id' in locals() else '',
#                 'processing_time': time.time() - start_time
#             }
#             print(f"❌ Analysis failed: {e}", file=sys.stderr)
#             self.cleanup()  # Cleanup on error
#             return error_result

#     def extract_video_id(self, url: str) -> Optional[str]:
#         patterns = [
#             r'(?:youtube\.com\/(?:watch\?v=|embed\/|v\/)|youtu\.be\/)([^&\n?#]+)',
#             r'youtube\.com\/watch\?.*v=([^&\n?#]+)',
#         ]
#         for pattern in patterns:
#             match = re.search(pattern, url)
#             if match:
#                 return match.group(1)
#         return None

#     async def get_metadata_fast(self, url: str) -> Dict[str, Any]:
#         loop = asyncio.get_event_loop()
        
#         def _extract_metadata():
#             try:
#                 ydl_opts = {
#                     **self.ydl_opts_base,
#                     'skip_download': True,
#                 }
                
#                 with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#                     info = ydl.extract_info(url, download=False)
#                     description = info.get('description', '') or ''
#                     description = self.clean_text_for_json(description)
                    
#                     return {
#                         'id': info.get('id', ''),
#                         'title': self.clean_text_for_json(info.get('title', 'Unknown Title')),
#                         'author': self.clean_text_for_json(info.get('uploader', 'Unknown Author')),
#                         'duration': info.get('duration', 0),
#                         'view_count': info.get('view_count', 0),
#                         'upload_date': info.get('upload_date', ''),
#                         'description': description,
#                         'thumbnail': info.get('thumbnail', ''),
#                         'tags': [self.clean_text_for_json(tag) for tag in (info.get('tags', []) or [])[:10]],
#                     }
#             except Exception as e:
#                 print(f"Metadata extraction error: {e}", file=sys.stderr)
#                 return {
#                     'id': self.extract_video_id(url) or '',
#                     'title': 'Unknown Title',
#                     'author': 'Unknown Author',
#                     'duration': 0,
#                     'view_count': 0,
#                     'upload_date': '',
#                     'description': '',
#                     'thumbnail': '',
#                     'tags': [],
#                 }
        
#         return await loop.run_in_executor(None, _extract_metadata)

#     async def get_transcript_fast(self, video_id: str) -> List[Dict[str, Any]]:
#         loop = asyncio.get_event_loop()
        
#         def _get_transcript():
#             try:
#                 transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
#                 transcript = None
#                 for lang_code in ['en', 'en-US', 'en-GB']:
#                     try:
#                         transcript = transcript_list.find_generated_transcript([lang_code])
#                         break
#                     except:
#                         try:
#                             transcript = transcript_list.find_transcript([lang_code])
#                             break
#                         except:
#                             continue
                
#                 if not transcript:
#                     available = list(transcript_list)
#                     if available:
#                         transcript = available[0]
                
#                 if transcript:
#                     segments = transcript.fetch()
#                     return [
#                         {
#                             'text': self.clean_text_for_json(segment.text.strip()),
#                             'start': segment.start,
#                             'end': segment.start + segment.duration,
#                             'confidence': 1.0
#                         }
#                         for segment in segments
#                         if segment.text.strip()
#                     ]
#                 return []
#             except Exception as e:
#                 print(f"YouTube transcript error: {e}", file=sys.stderr)
#                 return []
        
#         try:
#             return await asyncio.wait_for(loop.run_in_executor(None, _get_transcript), timeout=10)
#         except asyncio.TimeoutError:
#             print("⏰ Transcript fetch timed out after 10 seconds", file=sys.stderr)
#             return []

#     async def download_video_optimized(self, url: str) -> Optional[str]:
#         loop = asyncio.get_event_loop()
        
#         def _download():
#             try:
#                 video_path = os.path.join(self.temp_dir, 'video.%(ext)s')
#                 ydl_opts = {
#                     **self.ydl_opts_base,
#                     'format': 'worst[height<=480]/worst[height<=720]/mp4',
#                     'outtmpl': video_path,
#                     'merge_output_format': 'mp4',
#                     'progress_hooks': [lambda d: print(f"📥 Download progress: {d.get('downloaded_bytes', 0)} bytes, status: {d.get('status', 'unknown')}", file=sys.stderr)],
#                     'retries': 10,
#                     'fragment_retries': 15,
#                     'continuedl': True,
#                     'quiet': True,
#                     'no_warnings': True,
#                     'socket_timeout': 60,
#                     'http_chunk_size': 10485760,
#                     'verbose': True,
#                     'extractor_retries': 5,
#                 }
#                 with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#                     print(f"📥 Attempting download with opts: {ydl_opts}", file=sys.stderr)
#                     ydl.download([url])
#                 for file in os.listdir(self.temp_dir):
#                     if file.startswith('video.') and file.endswith(('.mp4', '.webm', '.mkv')):
#                         full_path = os.path.join(self.temp_dir, file)
#                         if os.path.getsize(full_path) >= 10240000:  # Check if file is at least 10MB
#                             print(f"📥 Download complete: {file} at {full_path}, size: {os.path.getsize(full_path)} bytes", file=sys.stderr)
#                             return full_path
#                 print("⚠️ Partial or no valid video file found after download.", file=sys.stderr)
#                 return None
#             except Exception as e:
#                 print(f"Download error: {str(e)}", file=sys.stderr)
#                 return None
        
#         try:
#             return await asyncio.wait_for(loop.run_in_executor(None, _download), timeout=120)
#         except asyncio.TimeoutError:
#             print("⏰ Video download timed out after 120 seconds", file=sys.stderr)
#             return None

#     async def transcribe_with_whisper(self, video_path: str) -> List[Dict[str, Any]]:
#         loop = asyncio.get_event_loop()
        
#         def _transcribe():
#             try:
#                 if not os.path.exists(video_path):
#                     print(f"❌ Video file not found: {video_path}", file=sys.stderr)
#                     return []
#                 print("Loading Whisper model (base)...", file=sys.stderr)
#                 import whisper
#                 model = whisper.load_model("base")
#                 print("Transcribing with Whisper...", file=sys.stderr)
#                 result = model.transcribe(video_path)
#                 print(f"Transcription completed, processing result...", file=sys.stderr)
#                 segments = []
#                 text = result["text"]
#                 words = text.split()
#                 chunk_size = max(1, len(words) // 10)  # Aim for ~10 segments
#                 for i in range(0, len(words), chunk_size):
#                     chunk = ' '.join(words[i:i + chunk_size])
#                     segments.append({
#                         'text': self.clean_text_for_json(chunk.strip()),
#                         'start': i * chunk_size * 0.1,  # Rough estimate
#                         'end': (i + chunk_size) * 0.1,  # Rough estimate
#                         'confidence': 0.9
#                     })
#                 return segments if segments else [{'text': self.clean_text_for_json(text), 'start': 0, 'end': 0, 'confidence': 0.9}]
#             except Exception as e:
#                 print(f"Whisper transcription error: {e}", file=sys.stderr)
#                 return []
        
#         try:
#             return await asyncio.wait_for(loop.run_in_executor(None, _transcribe), timeout=120)
#         except asyncio.TimeoutError:
#             print("⏰ Whisper transcription timed out after 120 seconds", file=sys.stderr)
#             return []

#     async def extract_key_frames(self, video_path: str) -> List[Dict[str, Any]]:
#         loop = asyncio.get_event_loop()
        
#         def _extract():
#             try:
#                 clip = VideoFileClip(video_path)
#                 duration = clip.duration
#                 interval = 30 if duration < 300 else 60
#                 frame_times = np.arange(0, duration, interval)[:5]
#                 key_frames = []
                
#                 for i, t in enumerate(frame_times):
#                     try:
#                         frame = clip.get_frame(t)
#                         img = Image.fromarray(frame)
#                         img.thumbnail((320, 180), Image.Resampling.LANCZOS)
#                         frame_filename = f'frame_{i}_{int(t)}.jpg'
#                         frame_path = os.path.join(self.temp_dir, frame_filename)
#                         img.save(frame_path, quality=75, optimize=True)
                        
#                         key_frames.append({
#                             'timestamp': float(t),
#                             'filename': frame_filename,
#                             'description': f"Frame at {int(t//60)}:{int(t%60):02d}",
#                             'path': frame_path
#                         })
#                     except Exception as e:
#                         print(f"Frame extraction error at {t}s: {e}", file=sys.stderr)
                
#                 clip.close()
#                 return key_frames
#             except Exception as e:
#                 print(f"Key frame extraction error: {e}", file=sys.stderr)
#                 return []
        
#         return await loop.run_in_executor(None, _extract)

#     def describe_keyframe(self, image_path: str) -> str:
#         try:
#             with open(image_path, "rb") as image_file:
#                 base64_image = base64.b64encode(image_file.read()).decode("utf-8")
#             response = self.groq_client.chat.completions.create(
#                 model="llava-v1.5-7b-4096-preview",
#                 messages=[
#                     {
#                         "role": "user",
#                         "content": [
#                             {"type": "text", "text": "Describe the content of this image."},
#                             {"type": "image_url", "image_url": f"data:image/jpeg;base64,{base64_image}"}
#                         ]
#                     }
#                 ],
#                 max_tokens=100
#             )
#             return self.clean_text_for_json(response.choices[0].message.content)
#         except Exception as e:
#             print(f"Keyframe description error: {e}", file=sys.stderr)
#             return f"Frame at {int(t//60)}:{int(t%60):02d}"

#     async def analyze_content_and_create_chapters(self, transcript: List[Dict], metadata: Dict) -> List[Dict[str, Any]]:
#         if not transcript:
#             return []
        
#         print("🧠 Analyzing content structure with Groq...", file=sys.stderr)
#         condensed_transcript = self.create_condensed_transcript(transcript)
#         chapter_structure = await self.identify_chapter_breaks_with_llm(condensed_transcript, metadata)
#         detailed_chapters = await self.create_detailed_chapters(chapter_structure, transcript, metadata)
#         return detailed_chapters

#     def create_condensed_transcript(self, transcript: List[Dict], max_length: int = 4000) -> str:
#         full_text = ""
#         for segment in transcript:
#             timestamp = f"[{int(segment['start']//60)}:{int(segment['start']%60):02d}]"
#             full_text += f"{timestamp} {segment['text']} "
        
#         if len(full_text) > max_length:
#             chunk_size = max_length // 4
#             beginning = full_text[:chunk_size]
#             middle_start = len(full_text) // 2 - chunk_size // 2
#             middle = full_text[middle_start:middle_start + chunk_size]
#             end = full_text[-chunk_size:]
#             condensed = f"{beginning}\n\n[... MIDDLE SECTION ...]\n{middle}\n\n[... END SECTION ...]\n{end}"
#         else:
#             condensed = full_text
#         return condensed

#     async def identify_chapter_breaks_with_llm(self, condensed_transcript: str, metadata: Dict) -> List[Dict]:
#         video_context = f"""
#         Video Title: {metadata.get('title', 'Unknown')}
#         Author: {metadata.get('author', 'Unknown')}
#         Duration: {metadata.get('duration', 0)} seconds ({metadata.get('duration', 0)//60}:{metadata.get('duration', 0)%60:02d})
#         Description: {metadata.get('description', '')[:300]}
#         Tags: {', '.join(metadata.get('tags', []))}
#         """

#         prompt = f"""{video_context}

#         Analyze the available video information and identify logical chapter breaks based on the title, description, tags, and assumed content structure.

#         Transcript with timestamps: {condensed_transcript or 'No transcript available'}

#         Instructions:
#         1. Identify natural chapter breaks based on inferred topics from metadata or transcript.
#         2. Each chapter should cover a distinct theme or segment (e.g., intro, main content, outro).
#         3. Chapters should be at least 30 seconds long.
#         4. Create engaging, descriptive titles that capture the essence of each inferred section.

#         Respond in JSON format with an array of chapters:
#         {{"chapters": [
#           {{"start_timestamp": "0:00", "end_timestamp": "2:15", "title": "Engaging Chapter Title", "main_topic": "Brief description of what this section covers", "key_points": ["point1", "point2", "point3"]}}
#         ]}}
#         """

#         try:
#             response = self.groq_client.chat.completions.create(
#                 model="llama-3.3-70b-versatile",
#                 messages=[
#                     {"role": "system", "content": "You are an expert video content analyzer who creates logical chapter divisions based on metadata and transcript content. You always respond with valid JSON."},
#                     {"role": "user", "content": prompt}
#                 ],
#                 max_tokens=1500,
#                 temperature=0.3
#             )
#             content = response.choices[0].message.content.strip()
#             if content.startswith('```'):
#                 content = content.split('```')[1].lstrip('json')
#             print(f"Groq raw response: {content}", file=sys.stderr)
#             chapters = json.loads(content).get('chapters', [])
#             if not chapters:
#                 print("⚠️ No chapters from Groq, falling back to time-based chapters.", file=sys.stderr)
#                 return self.create_fallback_chapters(metadata.get('duration', 0))
#             return chapters
#         except Exception as e:
#             print(f"Groq chapter analysis error: {e}", file=sys.stderr)
#             return self.create_fallback_chapters(metadata.get('duration', 0))

#     def timestamp_to_seconds(self, timestamp: str) -> float:
#         try:
#             if ':' in timestamp:
#                 parts = timestamp.split(':')
#                 if len(parts) == 2:
#                     minutes, seconds = parts
#                     return int(minutes) * 60 + int(seconds)
#                 elif len(parts) == 3:
#                     hours, minutes, seconds = parts
#                     return int(hours) * 3600 + int(minutes) * 60 + int(seconds)
#             return float(timestamp)
#         except:
#             return 0.0

#     async def create_detailed_chapters(self, chapter_structure: List[Dict], transcript: List[Dict], metadata: Dict) -> List[Dict[str, Any]]:
#         if not chapter_structure:
#             return self.create_fallback_chapters(metadata.get('duration', 0))
        
#         detailed_chapters = []
#         for idx, chapter_info in enumerate(chapter_structure):
#             try:
#                 start_time = self.timestamp_to_seconds(chapter_info.get('start_timestamp', '0:00'))
#                 end_time = self.timestamp_to_seconds(chapter_info.get('end_timestamp', '0:00'))
#                 chapter_segments = [
#                     seg for seg in transcript 
#                     if start_time <= seg['start'] < end_time
#                 ]
#                 chapter_text = ' '.join([seg['text'] for seg in chapter_segments])
#                 chapter_summary = await self.generate_chapter_summary(chapter_text, chapter_info, metadata)
                
#                 detailed_chapters.append({
#                     'id': f'chapter_{idx}',
#                     'title': self.clean_text_for_json(chapter_info.get('title', f'Chapter {idx + 1}'))[:80],
#                     'start_time': start_time,
#                     'end_time': end_time,
#                     'summary': chapter_summary.get('summary', chapter_info.get('main_topic', ''))[:200],
#                     'key_topics': chapter_summary.get('key_topics', chapter_info.get('key_points', []))[:5],
#                     'word_count': len(chapter_text.split()) if chapter_text else 0,
#                     'main_topic': self.clean_text_for_json(chapter_info.get('main_topic', ''))[:100]
#                 })
#                 print(f"✅ Chapter {idx + 1}: {detailed_chapters[-1]['title']}", file=sys.stderr)
#             except Exception as e:
#                 print(f"Error creating chapter {idx + 1}: {e}", file=sys.stderr)
#                 continue
#         return detailed_chapters

#     async def generate_chapter_summary(self, chapter_text: str, chapter_info: Dict, metadata: Dict) -> Dict[str, Any]:
#         if not chapter_text.strip():
#             return {
#                 'summary': chapter_info.get('main_topic', 'No content available'),
#                 'key_topics': chapter_info.get('key_points', [])
#             }
        
#         prompt = f"""Analyze this chapter from "{metadata.get('title', 'Unknown Video')}" and create:

#         1. A concise summary (max 200 characters) of what's discussed
#         2. 3-5 key topics/themes covered

#         Chapter Title: {chapter_info.get('title', 'Unknown')}
#         Expected Topic: {chapter_info.get('main_topic', 'Unknown')}

#         Chapter Content:
#         {chapter_text[:1200]}

#         Respond in JSON format:
#         {{"summary": "Detailed summary here", "key_topics": ["topic1", "topic2", "topic3"]}}"""

#         try:
#             response = self.groq_client.chat.completions.create(
#                 model="llama-3.3-70b-versatile",
#                 messages=[
#                     {"role": "system", "content": "You create concise, informative summaries that capture the key points discussed in video segments."},
#                     {"role": "user", "content": prompt}
#                 ],
#                 max_tokens=300,
#                 temperature=0.5
#             )
#             content = response.choices[0].message.content.strip()
#             if content.startswith('```'):
#                 content = content.split('```')[1].lstrip('json')
#             result = json.loads(content)
#             return {
#                 'summary': self.clean_text_for_json(result.get('summary', chapter_info.get('main_topic', '')))[:200],
#                 'key_topics': [self.clean_text_for_json(topic)[:30] for topic in result.get('key_topics', [])][:5]
#             }
#         except Exception as e:
#             print(f"Summary generation error: {e}", file=sys.stderr)
#             return {
#                 'summary': chapter_info.get('main_topic', 'Content analysis unavailable'),
#                 'key_topics': chapter_info.get('key_points', [])[:5]
#             }

#     def create_fallback_chapters(self, duration: float) -> List[Dict[str, Any]]:
#         if duration <= 0:
#             return []
        
#         if duration < 300:
#             num_chapters = 3
#         elif duration < 900:
#             num_chapters = 4
#         elif duration < 1800:
#             num_chapters = 6
#         else:
#             num_chapters = 8
        
#         chapter_length = duration / num_chapters
#         chapters = []
        
#         for i in range(num_chapters):
#             start_time = i * chapter_length
#             end_time = min((i + 1) * chapter_length, duration)
#             chapters.append({
#                 'id': f'chapter_{i}',
#                 'title': f'Chapter {i + 1}',
#                 'start_time': start_time,
#                 'end_time': end_time,
#                 'summary': f'Content from {int(start_time//60)}:{int(start_time%60):02d} to {int(end_time//60)}:{int(end_time%60):02d}',
#                 'key_topics': [],
#                 'word_count': 0,
#                 'main_topic': 'Time-based chapter'
#             })
#         return chapters

#     def cleanup(self):
#         if os.path.exists(self.temp_dir):
#             try:
#                 import shutil
#                 shutil.rmtree(self.temp_dir, ignore_errors=True)
#             except Exception as e:
#                 print(f"Cleanup error: {e}", file=sys.stderr)

# async def main():
#     if len(sys.argv) != 2:
#         print(json.dumps({
#             'success': False,
#             'error': 'Usage: python fast_video_analysis.py <youtube_url>'
#         }, ensure_ascii=True))
#         sys.exit(1)
    
#     youtube_url = sys.argv[1]
#     if 'youtube.com' not in youtube_url and 'youtu.be' not in youtube_url:
#         print(json.dumps({
#             'success': False,
#             'error': 'Invalid YouTube URL'
#         }, ensure_ascii=True))
#         sys.exit(1)
    
#     try:
#         analyzer = FastVideoAnalyzer()
#         result = await analyzer.analyze_video(youtube_url)
#         json_str = json.dumps(result, ensure_ascii=True, separators=(',', ':'))
#         print(json_str)
#         sys.exit(0 if result.get('success') else 1)
#     except KeyboardInterrupt:
#         print(json.dumps({
#             'success': False,
#             'error': 'Analysis interrupted by user'
#         }, ensure_ascii=True))
#         sys.exit(1)
#     except Exception as e:
#         print(json.dumps({
#             'success': False,
#             'error': f'Unexpected error: {str(e)}'
#         }, ensure_ascii=True))
#         sys.exit(1)

# if __name__ == '__main__':
#     asyncio.run(main())


import asyncio
import os
import tempfile
import yt_dlp
import whisper
import cv2
import requests
import json
import sys
from datetime import datetime
import unicodedata

# Set UTF-8 encoding for stdout/stderr to handle Unicode characters
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

class FastVideoAnalyzer:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables.")
        self.groq_api_url = "https://api.x.ai/v1/chat/completions"
        self.temp_dir = tempfile.mkdtemp()
        print(f"Temp directory created: {self.temp_dir}")

    def _sanitize_text(self, text):
        """Replace non-ASCII characters with their closest ASCII equivalent or '?'."""
        if not isinstance(text, str):
            text = str(text)
        return unicodedata.normalize('NFKD', text).encode('ascii', 'replace').decode('ascii')

    async def download_video_optimized(self, video_url, video_id):
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'best[height<=720][ext=mp4]/best[height<=480][ext=mp4]/mp4',
            'outtmpl': os.path.join(self.temp_dir, 'video.%(ext)s'),
            'merge_output_format': 'mp4',
            'retries': 15,
            'fragment_retries': 20,
            'continuedl': True,
            'socket_timeout': 90,
            'http_chunk_size': 10485760,
            'verbose': False,
            'progress_hooks': [self._download_hook],
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            video_path = os.path.join(self.temp_dir, 'video.mp4')
            if os.path.exists(video_path) and self._verify_video(video_path):
                print(f"Video downloaded: {video_path}")
                return video_path
            else:
                print("Warning: Partial or no valid video file found after download.")
                return video_path if os.path.exists(video_path) else None
        except Exception as e:
            print(f"Download error: {self._sanitize_text(e)}")
            return None

    def _download_hook(self, d):
        if d['status'] == 'downloading':
            print(f"Download progress: {d.get('downloaded_bytes', 0)} bytes")
        elif d['status'] == 'finished':
            print(f"Download completed: {d.get('downloaded_bytes', 0)} bytes")

    def _verify_video(self, video_path):
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return False
            ret, _ = cap.read()
            cap.release()
            return ret
        except Exception:
            return False

    async def transcribe_video(self, video_path):
        if not video_path:
            print("No video file to transcribe.")
            return []
        print(f"Transcribing file: {video_path}")
        try:
            model = whisper.load_model("base")
            print("Loading Whisper model (base)...")
            result = model.transcribe(video_path, fp16=False)
            # Sanitize transcript text
            for segment in result['segments']:
                segment['text'] = self._sanitize_text(segment['text'])
            print(f"Whisper transcription completed: {len(result['segments'])} segments")
            return result['segments']
        except Exception as e:
            print(f"Transcription error: {self._sanitize_text(e)}")
            return []

    async def extract_key_frames(self, video_path):
        if not video_path:
            print("No video file for frame extraction.")
            return []
        print("Extracting key frames...")
        try:
            cap = cv2.VideoCapture(video_path)
            frames = []
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            interval = int(fps * 10)  # Extract frame every 10 seconds
            for i in range(0, frame_count, interval):
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                ret, frame = cap.read()
                if ret:
                    frames.append(frame.tolist())  # Convert to list for JSON
            cap.release()
            print(f"Key frames extracted: {len(frames)}")
            return frames
        except Exception as e:
            print(f"Frame extraction error: {self._sanitize_text(e)}")
            return []

    async def generate_chapters(self, transcript_segments):
        transcript = " ".join([seg['text'] for seg in transcript_segments])
        if not transcript:
            print("No transcript available for chapter generation.")
            return []
        print("Generating chapters with Grok...")
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "grok-3",
            "messages": [
                {"role": "system", "content": "Generate chapters for the given transcript, including start/end timestamps, titles, main topics, and key points. Return in JSON format."},
                {"role": "user", "content": self._sanitize_text(transcript)}
            ],
            "max_tokens": 500
        }
        try:
            response = requests.post(self.groq_api_url, json=payload, headers=headers)
            response.raise_for_status()
            chapters_text = response.json()["choices"][0]["message"]["content"]
            chapters = json.loads(self._sanitize_text(chapters_text))
            print(f"Chapters generated: {len(chapters)}")
            return chapters
        except Exception as e:
            print(f"Grok chapter generation error: {self._sanitize_text(e)}")
            return []

    async def analyze_video(self, video_url, video_id):
        start_time = datetime.now()
        print(f"Starting video analysis for Video ID: {self._sanitize_text(video_id)}")
        print("Launching async tasks...")

        video_path = await self.download_video_optimized(video_url, video_id)
        transcript_task = self.transcribe_video(video_path)
        frames_task = self.extract_key_frames(video_path)
        transcript, frames = await asyncio.gather(transcript_task, frames_task)
        chapters = await self.generate_chapters(transcript)

        result = {
            "success": True,
            "video_path": video_path,
            "transcript": transcript,
            "frames": frames,
            "chapters": chapters,
            "duration_seconds": (datetime.now() - start_time).total_seconds()
        }
        print(f"Analysis completed in {result['duration_seconds']:.1f}s")
        return result

    def cleanup(self):
        try:
            for file in os.listdir(self.temp_dir):
                os.remove(os.path.join(self.temp_dir, file))
            os.rmdir(self.temp_dir)
            print("Cleaned up temporary files.")
        except Exception as e:
            print(f"Cleanup error: {self._sanitize_text(e)}")

async def main():
    try:
        video_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.youtube.com/watch?v=UIvgOuj-AA0"
        video_id = sys.argv[2] if len(sys.argv) > 2 else "UIvgOuj-AA0"
        analyzer = FastVideoAnalyzer()
        result = await analyzer.analyze_video(video_url, video_id)
        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)})) 
    finally:
        if 'analyzer' in locals():
            analyzer.cleanup()

if __name__ == "__main__":
    asyncio.run(main())