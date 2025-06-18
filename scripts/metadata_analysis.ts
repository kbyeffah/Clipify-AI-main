#!/usr/bin/env ts-node
/**
 * Enhanced Metadata-Only Video Analysis with YouTube Transcript API
 */

import { spawn } from 'child_process';
import { config } from 'dotenv';
import axios from 'axios';
import ytdl from 'ytdl-core';

// Load environment variables
config();

interface TranscriptSegment {
  text: string;
  start: number;
  end: number;
  confidence: number;
  duration: number;
  source: string;
  language: string;
  is_generated: boolean;
}

interface Chapter {
  id: string;
  title: string;
  start_time: number;
  end_time: number;
  summary: string;
  key_topics: string[];
  word_count: number;
  main_topic: string;
  source: string;
}

interface AnalysisResult {
  success: boolean;
  video_id: string;
  metadata: any;
  transcript: TranscriptSegment[];
  chapters: Chapter[];
  keyFrames: any[];
  processing_time: number;
  analysis_method: string;
  stats: {
    transcript_segments: number;
    chapters_generated: number;
    key_frames_extracted: number;
    transcript_source: string;
    chapter_method: string;
    video_downloaded: boolean;
  };
}

class EnhancedMetadataAnalyzer {
  private groqApiKey: string;
  private groqBaseUrl: string;

  constructor() {
    this.groqApiKey = process.env.GROQ_API_KEY || '';
    if (!this.groqApiKey) {
      throw new Error('GROQ_API_KEY environment variable is not set');
    }
    this.groqBaseUrl = 'https://api.groq.com/openai/v1/chat/completions';
  }

  private cleanTextForJson(text: string): string {
    if (!text) return '';
    text = text.replace(/[\u200b\u200c\u200d\u200e\u200f]/g, '').replace(/…/g, '...');
    text = text.replace(/[^\x00-\x7F\u00A0-\u024F\u1E00-\u1EFF\u2000-\u206F\u2070-\u209F\u20A0-\u20CF\u2100-\u214F]/g, '');
    return text.trim();
  }

  private extractVideoId(url: string): string | null {
    const patterns = [
      /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)/,
      /youtube\.com\/watch\?.*v=([^&\n?#]+)/,
    ];
    for (const pattern of patterns) {
      const match = url.match(pattern);
      if (match) return match[1];
    }
    return null;
  }

  private async getMetadataOnly(url: string): Promise<any> {
    try {
      console.error('🔍 Extracting video metadata...');
      const info = await ytdl.getInfo(url);
      return {
        id: info.videoDetails.videoId,
        title: this.cleanTextForJson(info.videoDetails.title),
        author: this.cleanTextForJson(info.videoDetails.author.name),
        channel: this.cleanTextForJson(info.videoDetails.author.id),
        duration: parseInt(info.videoDetails.lengthSeconds),
        view_count: parseInt(info.videoDetails.viewCount),
        like_count: parseInt(String(info.videoDetails.likes || '0')),
        upload_date: info.videoDetails.uploadDate,
        description: this.cleanTextForJson(info.videoDetails.description || ''),
        thumbnail: info.videoDetails.thumbnails[0]?.url,
        tags: info.videoDetails.keywords?.slice(0, 15).map(tag => this.cleanTextForJson(tag)) || [],
        category: info.videoDetails.category,
        webpage_url: info.videoDetails.video_url,
      };
    } catch (error) {
      console.error('Metadata extraction error:', error);
      return {
        id: this.extractVideoId(url) || '',
        title: 'Video Analysis',
        author: 'Unknown',
        channel: '',
        duration: 0,
        view_count: 0,
        like_count: 0,
        upload_date: '',
        description: '',
        thumbnail: '',
        tags: [],
        category: '',
        webpage_url: url,
      };
    }
  }

  private async getYouTubeTranscript(youtubeUrl: string): Promise<TranscriptSegment[]> {
    try {
      console.error('📜 Fetching transcript via YouTube API...');
      const videoId = this.extractVideoId(youtubeUrl);
      if (!videoId) throw new Error('Invalid YouTube URL');
      
      // Call Python script for transcript (to reuse existing logic)
      const pythonProcess = spawn('python3', ['metadata_analysis.py', youtubeUrl]);
      let output = '';
      let errorOutput = '';
      
      pythonProcess.stdout.on('data', (data) => output += data.toString());
      pythonProcess.stderr.on('data', (data) => errorOutput += data.toString());
      
      const result = await new Promise((resolve, reject) => {
        pythonProcess.on('close', (code) => {
          if (code !== 0) {
            console.error('Python transcript error:', errorOutput);
            reject(new Error(errorOutput));
          } else {
            try {
              const parsed = JSON.parse(output);
              resolve(parsed.transcript || []);
            } catch (e) {
              reject(e);
            }
          }
        });
      });
      
      return result as TranscriptSegment[];
    } catch (error) {
      console.error('YouTube transcript error:', error);
      return [];
    }
  }

  public async analyzeVideo(youtubeUrl: string): Promise<AnalysisResult> {
    const startTime = Date.now();
    try {
      console.error('🚀 Starting enhanced metadata analysis...');
      const videoId = this.extractVideoId(youtubeUrl);
      if (!videoId) {
        throw new Error('Invalid YouTube URL');
      }
      console.error(`📹 Video ID: ${videoId}`);
      
      const [metadata, transcript] = await Promise.all([
        this.getMetadataOnly(youtubeUrl),
        this.getYouTubeTranscript(youtubeUrl)
      ]);
      
      console.error(`✅ Metadata: ${metadata.title.substring(0, 50)}...`);
      console.error(`✅ Transcript: ${transcript.length} segments`);
      
      console.error('🧠 Creating intelligent chapters based on content...');
      const chapters = await this.createSmartChapters(transcript, metadata);
      console.error(`✅ Intelligent chapters: ${chapters.length}`);
      
      const result: AnalysisResult = {
        success: true,
        video_id: videoId,
        metadata,
        transcript,
        chapters,
        keyFrames: [],
        processing_time: (Date.now() - startTime) / 1000,
        analysis_method: 'enhanced_metadata_youtube',
        stats: {
          transcript_segments: transcript.length,
          chapters_generated: chapters.length,
          key_frames_extracted: 0,
          transcript_source: transcript.length > 0 ? 'youtube_api' : 'none',
          chapter_method: 'smart_content_analysis',
          video_downloaded: false
        }
      };
      
      console.error(`🎉 Analysis complete in ${result.processing_time.toFixed(1)}s`);
      return result;
    } catch (error) {
      console.error('❌ Analysis failed:', error);
      return {
        success: false,
        video_id: this.extractVideoId(youtubeUrl) || '',
        metadata: {},
        transcript: [],
        chapters: [],
        keyFrames: [],
        processing_time: (Date.now() - startTime) / 1000,
        analysis_method: 'enhanced_metadata_youtube',
        stats: {
          transcript_segments: 0,
          chapters_generated: 0,
          key_frames_extracted: 0,
          transcript_source: 'none',
          chapter_method: 'none',
          video_downloaded: false
        }
      };
    }
  }

  private async createSmartChapters(transcript: TranscriptSegment[], metadata: any): Promise<Chapter[]> {
    try {
      const descriptionChapters = this.parseDescriptionChapters(metadata.description);
      if (descriptionChapters.length > 0) {
        console.error(`📚 Found ${descriptionChapters.length} chapters in description`);
        return descriptionChapters;
      }
      
      if (transcript.length > 10) {
        const contentChapters = await this.createContentBasedChapters(transcript, metadata);
        if (contentChapters.length > 0) {
          console.error(`🤖 Created ${contentChapters.length} content-based chapters`);
          return contentChapters;
        }
      }
      
      const timeChapters = this.createTimeChapters(metadata.duration);
      console.error(`⏰ Created ${timeChapters.length} time-based chapters`);
      return timeChapters;
    } catch (error) {
      console.error('Chapter creation error:', error);
      return this.createTimeChapters(metadata.duration);
    }
  }

  private parseDescriptionChapters(description: string): Chapter[] {
    const chapters: Chapter[] = [];
    const patterns = [
      /(\d{1,2}:\d{2}(?::\d{2})?)\s*[-–]?\s*(.+?)(?=\n|$|\d{1,2}:\d{2})/g,
      /(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+?)(?=\n|$|\d{1,2}:\d{2})/g,
    ];
    
    for (const pattern of patterns) {
      const matches = Array.from(description.matchAll(pattern));
      if (matches.length >= 2) {
        for (let i = 0; i < matches.length; i++) {
          const [_, timestamp, title] = matches[i];
          const startSeconds = this.timestampToSeconds(timestamp);
          const endSeconds = i + 1 < matches.length 
            ? this.timestampToSeconds(matches[i + 1][1])
            : undefined;
          
          const cleanTitle = this.cleanTextForJson(title.trim());
          if (cleanTitle && cleanTitle.length > 3) {
            chapters.push({
              id: `desc_chapter_${i}`,
              title: cleanTitle.slice(0, 80),
              start_time: startSeconds,
              end_time: endSeconds || 0,
              summary: `Chapter covering: ${cleanTitle}`.slice(0, 200),
              key_topics: this.extractKeywords(cleanTitle),
              word_count: cleanTitle.split(/\s+/).length,
              main_topic: cleanTitle.slice(0, 100),
              source: 'description_timestamps'
            });
          }
        }
        if (chapters.length > 0) {
          return chapters;
        }
      }
    }
    return [];
  }

  private async createContentBasedChapters(transcript: TranscriptSegment[], metadata: any): Promise<Chapter[]> {
    try {
      const chunkSize = Math.max(20, Math.floor(transcript.length / 8));
      const chunks = [];
      
      for (let i = 0; i < transcript.length; i += chunkSize) {
        const chunk = transcript.slice(i, i + chunkSize);
        const chunkText = chunk.map(seg => seg.text).join(' ');
        const chunkStart = chunk[0].start;
        const chunkEnd = chunk[chunk.length - 1].end;
        
        chunks.push({
          text: chunkText,
          start: chunkStart,
          end: chunkEnd,
          segment_count: chunk.length
        });
      }
      
      const durationMinutes = metadata.duration / 60;
      let prompt = `Analyze this ${durationMinutes.toFixed(1)}-minute video transcript and create logical chapters based on natural topic changes and content flow.

Video: "${metadata.title}" by ${metadata.author}

Transcript chunks with timestamps:
`;
      
      for (let i = 0; i < Math.min(chunks.length, 6); i++) {
        const chunk = chunks[i];
        const startMin = Math.floor(chunk.start / 60);
        const startSec = Math.floor(chunk.start % 60);
        prompt += `\n[${startMin}:${startSec.toString().padStart(2, '0')}] ${chunk.text.slice(0, 300)}...`;
      }
      
      prompt += `\n\nCreate chapters in this exact JSON format:
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
`;

      const response = await axios.post(this.groqBaseUrl, {
        model: "llama-3.3-70b-versatile",
        messages: [
          {
            role: "system",
            content: "You are an expert at analyzing video content and creating logical chapter divisions. Always respond with valid JSON."
          },
          { role: "user", content: prompt }
        ],
        max_tokens: 1000,
        temperature: 0.3
      }, {
        headers: {
          'Authorization': `Bearer ${this.groqApiKey}`,
          'Content-Type': 'application/json'
        }
      });
      
      let content = response.data.choices[0].message.content.trim();
      if (content.startsWith('```')) {
        content = content.split('```')[1].trim();
        if (content.startsWith('json')) {
          content = content.slice(4);
        }
      }
      
      const result = JSON.parse(content);
      const chaptersData = result.chapters || [];
      
      const formattedChapters: Chapter[] = [];
      for (let i = 0; i < chaptersData.length; i++) {
        const chapter = chaptersData[i];
        const startTime = parseFloat(chapter.start_seconds);
        const endTime = parseFloat(chapter.end_seconds);
        const chapterText = this.getTranscriptTextForTimerange(transcript, startTime, endTime);
        const wordCount = chapterText.split(/\s+/).length;
        
        formattedChapters.push({
          id: `content_chapter_${i}`,
          title: this.cleanTextForJson(chapter.title).slice(0, 80),
          start_time: startTime,
          end_time: endTime,
          summary: this.cleanTextForJson(chapter.summary).slice(0, 200),
          key_topics: this.extractKeywords(chapter.main_topic + ' ' + chapter.title),
          word_count: wordCount,
          main_topic: this.cleanTextForJson(chapter.main_topic).slice(0, 100),
          source: 'content_analysis'
        });
      }
      
      return formattedChapters;
    } catch (error) {
      console.error('Content-based chapter creation error:', error);
      return [];
    }
  }

  private getTranscriptTextForTimerange(transcript: TranscriptSegment[], startTime: number, endTime: number): string {
    return transcript
      .filter(segment => segment.start >= startTime && segment.end <= endTime)
      .map(segment => segment.text)
      .join(' ');
  }

  private timestampToSeconds(timestamp: string): number {
    try {
      const parts = timestamp.split(':');
      if (parts.length === 2) {
        return parseInt(parts[0]) * 60 + parseInt(parts[1]);
      } else if (parts.length === 3) {
        return parseInt(parts[0]) * 3600 + parseInt(parts[1]) * 60 + parseInt(parts[2]);
      }
      return 0;
    } catch {
      return 0;
    }
  }

  private extractKeywords(text: string): string[] {
    const words = text.toLowerCase().match(/\b[a-zA-Z]{3,}\b/g) || [];
    const commonWords = new Set([
      'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had',
      'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his',
      'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'boy',
      'did', 'man', 'men', 'say', 'she', 'too', 'use'
    ]);
    const uniqueWords = [...new Set(words)].filter(word => !commonWords.has(word));
    return uniqueWords.slice(0, 5);
  }

  private createTimeChapters(duration: number): Chapter[] {
    if (duration <= 0) return [];
    
    let numChapters: number;
    if (duration < 180) {
      numChapters = 2;
    } else if (duration < 600) {
      numChapters = 3;
    } else if (duration < 1800) {
      numChapters = 5;
    } else {
      numChapters = 6;
    }
    
    const chapterLength = duration / numChapters;
    const chapters: Chapter[] = [];
    
    for (let i = 0; i < numChapters; i++) {
      const startTime = i * chapterLength;
      const endTime = Math.min((i + 1) * chapterLength, duration);
      
      chapters.push({
        id: `time_chapter_${i}`,
        title: `Part ${i + 1}`,
        start_time: startTime,
        end_time: endTime,
        summary: `Content from ${this.secondsToTimestamp(startTime)} to ${this.secondsToTimestamp(endTime)}`,
        key_topics: [],
        word_count: 0,
        main_topic: `Time segment ${i + 1}`,
        source: 'time_based'
      });
    }
    
    return chapters;
  }

  private secondsToTimestamp(seconds: number): string {
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  }
}

async function main() {
  if (process.argv.length !== 3) {
    console.error(JSON.stringify({
      success: false,
      error: 'Usage: ts-node metadata_analysis.ts <youtube_url>'
    }));
    process.exit(1);
  }
  
  const youtubeUrl = process.argv[2];
  if (!youtubeUrl.includes('youtube.com') && !youtubeUrl.includes('youtu.be')) {
    console.error(JSON.stringify({
      success: false,
      error: 'Invalid YouTube URL'
    }));
    process.exit(1);
  }
  
  try {
    const analyzer = new EnhancedMetadataAnalyzer();
    const result = await analyzer.analyzeVideo(youtubeUrl);
    console.log(JSON.stringify(result));
    process.exit(result.success ? 0 : 1);
  } catch (error) {
    console.error(JSON.stringify({
      success: false,
      error: `Analysis error: ${error}`
    }));
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}