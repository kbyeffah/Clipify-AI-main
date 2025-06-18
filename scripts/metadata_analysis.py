#!/usr/bin/env python3
"""
Enhanced Metadata-Only Video Analysis with YouTube Transcript API
"""

import sys
import json
import asyncio
import os
import time
import re
from typing import Dict, List, Optional, Any
from pathlib import Path
import tempfile

# Core dependencies
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from faster_whisper import WhisperModel
from groq import Groq

class EnhancedMetadataAnalyzer:
    def __init__(self):
        self.whisper_model = None  # Load only if needed
        self.groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        if not os.getenv('GROQ_API_KEY'):
            raise ValueError("GROQ_API_KEY environment variable is not set")
        
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'writeinfojson': False,
            'writethumbnail': False,
            'progress': False,
            'noprogress': True,
        }

    def clean_text_for_json(self, text: str) -> str:
        if not text:
            return ""
        
        text = text.replace('\u200b', '').replace('\u200c', '').replace('\u200d', '')
        text = text.replace('\u200e', '').replace('\u200f', '').replace('…', '...')
        text = re.sub(r'[^\x00-\x7F\u00A0-\u024F\u1E00-\u1EFF\u2000-\u206F\u2070-\u209F\u20A0-\u20CF\u2100-\u214F]', '', text)
        return text.strip()

    async def analyze_video_enhanced(self, youtube_url: str) -> Dict[str, Any]:
        start_time = time.time()
        
        try:
            print("🚀 Starting enhanced metadata analysis...", file=sys.stderr)
            
            video_id = self.extract_video_id(youtube_url)
            if not video_id:
                raise ValueError("Invalid YouTube URL")
            
            print(f"📹 Video ID: {video_id}", file=sys.stderr)
            
            metadata_task = self.get_metadata_only(youtube_url)
            transcript_task = self.get_youtube_transcript(video_id)
            
            metadata, transcript = await asyncio.gather(metadata_task, transcript_task)
            
            print(f"✅ Metadata: {metadata['title'][:50]}...", file=sys.stderr)
            print(f"✅ Transcript: {len(transcript)} segments", file=sys.stderr)
            
            if not transcript:
                print("🔄 Falling back to Faster-Whisper transcription...", file=sys.stderr)
                video_path = await self.download_video_optimized(youtube_url)
                if video_path:
                    transcript = await self.transcribe_with_faster_whisper(video_path)
                    print(f"✅ Faster-Whisper transcript: {len(transcript)} segments", file=sys.stderr)
            
            print("🧠 Creating intelligent chapters based on content...", file=sys.stderr)
            chapters = await self.create_smart_chapters(transcript, metadata)
            print(f"✅ Intelligent chapters: {len(chapters)}", file=sys.stderr)
            
            result = {
                'success': True,
                'video_id': video_id,
                'metadata': metadata,
                'transcript': transcript,
                'chapters': chapters,
                'keyFrames': [],
                'processing_time': time.time() - start_time,
                'analysis_method': 'enhanced_metadata_youtube',
                'stats': {
                    'transcript_segments': len(transcript),
                    'chapters_generated': len(chapters),
                    'key_frames_extracted': 0,
                    'transcript_source': 'youtube_api' if transcript and not self.whisper_model else 'faster_whisper',
                    'chapter_method': 'smart_content_analysis',
                    'video_downloaded': bool(self.whisper_model)
                }
            }
            
            print(f"🎉 Analysis complete in {result['processing_time']:.1f}s", file=sys.stderr)
            return result
            
        except Exception as e:
            error_result = {
                'success': False,
                'error': str(e),
                'video_id': video_id if 'video_id' in locals() else '',
                'processing_time': time.time() - start_time,
                'analysis_method': 'enhanced_metadata_youtube'
            }
            print(f"❌ Analysis failed: {e}", file=sys.stderr)
            return error_result

    def extract_video_id(self, url: str) -> Optional[str]:
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
            r'youtube\.com\/watch\?.*v=([^&\n?#]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    async def get_metadata_only(self, url: str) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        
        def _extract_metadata():
            try:
                print("🔍 Extracting video metadata...", file=sys.stderr)
                with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    description = self.clean_text_for_json(info.get('description', '') or '')
                    return {
                        'id': info.get('id', ''),
                        'title': self.clean_text_for_json(info.get('title', 'Unknown Title')),
                        'author': self.clean_text_for_json(info.get('uploader', 'Unknown Author')),
                        'channel': self.clean_text_for_json(info.get('channel', '')),
                        'duration': info.get('duration', 0),
                        'view_count': info.get('view_count', 0),
                        'like_count': info.get('like_count', 0),
                        'upload_date': info.get('upload_date', ''),
                        'description': description,
                        'thumbnail': info.get('thumbnail', ''),
                        'tags': [self.clean_text_for_json(tag) for tag in (info.get('tags', []) or [])[:15]],
                        'category': info.get('category', ''),
                        'webpage_url': info.get('webpage_url', ''),
                    }
            except Exception as e:
                print(f"Metadata extraction error: {e}", file=sys.stderr)
                return {
                    'id': self.extract_video_id(url) or '',
                    'title': 'Video Analysis',
                    'author': 'Unknown',
                    'channel': '',
                    'duration': 0,
                    'view_count': 0,
                    'like_count': 0,
                    'upload_date': '',
                    'description': '',
                    'thumbnail': '',
                    'tags': [],
                    'category': '',
                    'webpage_url': url,
                }
        
        return await loop.run_in_executor(None, _extract_metadata)

    async def get_youtube_transcript(self, video_id: str) -> List[Dict[str, Any]]:
        loop = asyncio.get_event_loop()
        
        def _get_transcript():
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                transcript = None
                for lang_code in ['en', 'en-US', 'en-GB']:
                    try:
                        transcript = transcript_list.find_generated_transcript([lang_code])
                        break
                    except:
                        try:
                            transcript = transcript_list.find_transcript([lang_code])
                            break
                        except:
                            continue
                
                if not transcript:
                    available = list(transcript_list)
                    if available:
                        transcript = available[0]
                
                if transcript:
                    segments = transcript.fetch()
                    return [
                        {
                            'text': self.clean_text_for_json(segment['text'].strip()),
                            'start': segment['start'],
                            'end': segment['start'] + segment['duration'],
                            'confidence': 1.0,
                            'duration': segment['duration'],
                            'source': 'youtube_api',
                            'language': 'en',
                            'is_generated': False
                        }
                        for segment in segments
                        if segment['text'].strip()
                    ]
                return []
            except Exception as e:
                print(f"YouTube transcript error: {e}", file=sys.stderr)
                return []
        
        return await loop.run_in_executor(None, _get_transcript)

    async def download_video_optimized(self, url: str) -> Optional[str]:
        loop = asyncio.get_event_loop()
        
        def _download():
            try:
                video_path = os.path.join(tempfile.mkdtemp(), 'video.%(ext)s')
                ydl_opts = {
                    **self.ydl_opts,
                    'format': 'worst[height<=480]/worst[height<=720]/worst',
                    'outtmpl': video_path,
                    'merge_output_format': 'mp4',
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                for file in os.listdir(os.path.dirname(video_path)):
                    if file.startswith('video.') and file.endswith(('.mp4', '.webm', '.mkv')):
                        return os.path.join(os.path.dirname(video_path), file)
                return None
            except Exception as e:
                print(f"Download error: {e}", file=sys.stderr)
                return None
        
        return await loop.run_in_executor(None, _download)

    async def transcribe_with_faster_whisper(self, video_path: str) -> List[Dict[str, Any]]:
        loop = asyncio.get_event_loop()
        
        def _transcribe():
            try:
                if not self.whisper_model:
                    print("Loading Faster-Whisper model...", file=sys.stderr)
                    self.whisper_model = WhisperModel("base", device="cpu")
                
                print("Transcribing with Faster-Whisper...", file=sys.stderr)
                segments, _ = self.whisper_model.transcribe(video_path, language='en')
                return [
                    {
                        'text': self.clean_text_for_json(segment.text.strip()),
                        'start': segment.start,
                        'end': segment.end,
                        'confidence': 0.8,
                        'duration': segment.end - segment.start,
                        'source': 'faster_whisper',
                        'language': 'en',
                        'is_generated': True
                    }
                    for segment in segments
                    if segment.text.strip()
                ]
            except Exception as e:
                print(f"Faster-Whisper transcription error: {e}", file=sys.stderr)
                return []
        
        return await loop.run_in_executor(None, _transcribe)

    async def create_smart_chapters(self, transcript: List[Dict], metadata: Dict) -> List[Dict[str, Any]]:
        description_chapters = self.parse_description_chapters(metadata.get('description', ''))
        if description_chapters:
            print(f"📚 Found {len(description_chapters)} chapters in description", file=sys.stderr)
            return description_chapters
        
        if transcript and len(transcript) > 10:
            content_chapters = await self.create_content_based_chapters(transcript, metadata)
            if content_chapters:
                print(f"🤖 Created {len(content_chapters)} content-based chapters", file=sys.stderr)
                return content_chapters
        
        time_chapters = self.create_time_chapters(metadata.get('duration', 0))
        print(f"⏰ Created {len(time_chapters)} time-based chapters", file=sys.stderr)
        return time_chapters

    def parse_description_chapters(self, description: str) -> List[Dict[str, Any]]:
        chapters = []
        patterns = [
            r'(\d{1,2}:\d{2}(?::\d{2})?)\s*[-–]?\s*(.+?)(?=\n|$|\d{1,2}:\d{2})',
            r'(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+?)(?=\n|$|\d{1,2}:\d{2})',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, description, re.MULTILINE | re.IGNORECASE)
            if len(matches) >= 2:
                for i, (timestamp, title) in enumerate(matches):
                    start_seconds = self.timestamp_to_seconds(timestamp)
                    end_seconds = (
                        self.timestamp_to_seconds(matches[i + 1][0]) 
                        if i + 1 < len(matches) 
                        else None
                    )
                    clean_title = self.clean_text_for_json(title.strip())
                    if clean_title and len(clean_title) > 3:
                        chapters.append({
                            'id': f'desc_chapter_{i}',
                            'title': clean_title[:80],
                            'start_time': start_seconds,
                            'end_time': end_seconds or 0,
                            'summary': f'Chapter covering: {clean_title}'[:200],
                            'key_topics': self.extract_keywords(clean_title),
                            'word_count': len(clean_title.split()),
                            'main_topic': clean_title[:100],
                            'source': 'description_timestamps'
                        })
                if chapters:
                    return chapters
        return []

    async def create_content_based_chapters(self, transcript: List[Dict], metadata: Dict) -> List[Dict[str, Any]]:
        try:
            chunk_size = max(20, len(transcript) // 8)
            chunks = []
            for i in range(0, len(transcript), chunk_size):
                chunk = transcript[i:i + chunk_size]
                chunk_text = ' '.join([seg['text'] for seg in chunk])
                chunk_start = chunk[0]['start']
                chunk_end = chunk[-1]['end']
                chunks.append({
                    'text': chunk_text,
                    'start': chunk_start,
                    'end': chunk_end,
                    'segment_count': len(chunk)
                })
            
            duration_minutes = metadata.get('duration', 0) / 60
            prompt = f"""Analyze this {duration_minutes:.1f}-minute video transcript and create logical chapters based on natural topic changes and content flow.

Video: "{metadata.get('title', 'Unknown')}" by {metadata.get('author', 'Unknown')}

Transcript chunks with timestamps:
"""
            for i, chunk in enumerate(chunks[:6]):
                start_min = int(chunk['start'] // 60)
                start_sec = int(chunk['start'] % 60)
                prompt += f"\n[{start_min}:{start_sec:02d}] {chunk['text'][:300]}..."
            
            prompt += """

Create chapters in this exact JSON format:
{
  "chapters": [
    {
      "title": "Engaging Chapter Title",
      "start_seconds": 0,
      "end_seconds": 180,
      "summary": "Brief description of this section's content",
      "main_topic": "Key theme or subject"
    }
  ]
}
"""

            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing video content and creating logical chapter divisions. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            content = response.choices[0].message.content.strip()
            if content.startswith('```'):
                content = content.split('```')[1].lstrip('json')
            
            result = json.loads(content)
            chapters_data = result.get('chapters', [])
            
            formatted_chapters = []
            for i, chapter in enumerate(chapters_data):
                start_time = float(chapter.get('start_seconds', i * 60))
                end_time = float(chapter.get('end_seconds', (i + 1) * 60))
                chapter_text = self.get_transcript_text_for_timerange(transcript, start_time, end_time)
                word_count = len(chapter_text.split()) if chapter_text else 0
                
                formatted_chapters.append({
                    'id': f'content_chapter_{i}',
                    'title': self.clean_text_for_json(chapter.get('title', f'Chapter {i+1}'))[:80],
                    'start_time': start_time,
                    'end_time': end_time,
                    'summary': self.clean_text_for_json(chapter.get('summary', ''))[:200],
                    'key_topics': self.extract_keywords(chapter.get('main_topic', '') + ' ' + chapter.get('title', '')),
                    'word_count': word_count,
                    'main_topic': self.clean_text_for_json(chapter.get('main_topic', ''))[:100],
                    'source': 'content_analysis'
                })
            return formatted_chapters
        except Exception as e:
            print(f"Content-based chapter creation error: {e}", file=sys.stderr)
            return []

    def get_transcript_text_for_timerange(self, transcript: List[Dict], start_time: float, end_time: float) -> str:
        text_parts = [seg['text'] for seg in transcript if seg['start'] >= start_time and seg['end'] <= end_time]
        return ' '.join(text_parts)

    def timestamp_to_seconds(self, timestamp: str) -> float:
        try:
            parts = timestamp.split(':')
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            return 0.0
        except:
            return 0.0

    def extract_keywords(self, text: str) -> List[str]:
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        common_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'boy', 'did', 'man', 'men', 'say', 'she', 'too', 'use'}
        unique_words = [word for word in set(words) if word not in common_words]
        return unique_words[:5]

    def create_time_chapters(self, duration: float) -> List[Dict[str, Any]]:
        if duration <= 0:
            return []
        
        if duration < 180:
            num_chapters = 2
        elif duration < 600:
            num_chapters = 3
        elif duration < 1800:
            num_chapters = 5
        else:
            num_chapters = 6
        
        chapter_length = duration / num_chapters
        chapters = []
        
        for i in range(num_chapters):
            start_time = i * chapter_length
            end_time = min((i + 1) * chapter_length, duration)
            chapters.append({
                'id': f'time_chapter_{i}',
                'title': f'Part {i + 1}',
                'start_time': start_time,
                'end_time': end_time,
                'summary': f'Content from {self.seconds_to_timestamp(start_time)} to {self.seconds_to_timestamp(end_time)}',
                'key_topics': [],
                'word_count': 0,
                'main_topic': f'Time segment {i + 1}',
                'source': 'time_based'
            })
        return chapters

    def seconds_to_timestamp(self, seconds: float) -> str:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"

async def main():
    if len(sys.argv) != 2:
        print(json.dumps({
            'success': False,
            'error': 'Usage: python metadata_analysis.py <youtube_url>'
        }, ensure_ascii=True))
        sys.exit(1)
    
    youtube_url = sys.argv[1]
    if 'youtube.com' not in youtube_url and 'youtu.be' not in youtube_url:
        print(json.dumps({
            'success': False,
            'error': 'Invalid YouTube URL'
        }, ensure_ascii=True))
        sys.exit(1)
    
    try:
        analyzer = EnhancedMetadataAnalyzer()
        result = await analyzer.analyze_video_enhanced(youtube_url)
        json_str = json.dumps(result, ensure_ascii=True, separators=(',', ':'))
        print(json_str)
        sys.exit(0 if result.get('success') else 1)
    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': f'Analysis error: {str(e)}'
        }, ensure_ascii=True))
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())