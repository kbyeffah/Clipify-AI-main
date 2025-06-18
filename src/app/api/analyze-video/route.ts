import { NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs/promises';
import os from 'os';

const TEMP_DIR = path.join(process.cwd(), 'public', 'temp');

const PYTHON_COMMAND = os.platform() === 'win32'
  ? path.join(process.cwd(), 'venv', 'Scripts', 'python.exe')
  : 'python3';

function cleanOutput(output: string): string {
  const jsonMatch = output.match(/\{[\s\S]*\}/);
  return jsonMatch ? jsonMatch[0] : output;
}

function extractVideoId(url: string): string {
  const patterns = [
    /(?:youtube\.com\/(?:watch\?v=|embed\/|v\/)|youtu\.be\/)([^&\n?#]+)/,
    /youtube\.com\/watch\?.*v=([^&\n?#]+)/,
  ];
  for (const pattern of patterns) {
    const match = url.match(pattern);
    if (match) return match[1];
  }
  return 'unknown';
}

export async function POST(req: Request): Promise<NextResponse> {
  try {
    const { url } = await req.json();
    const videoId = extractVideoId(url);
    console.log('Received:', { url, videoId });

    if (videoId === 'unknown') {
      throw new Error('Invalid YouTube URL');
    }

    await fs.mkdir(TEMP_DIR, { recursive: true });

    const scriptPath = path.join(process.cwd(), 'scripts', 'fast_video_analysis.py');
    console.log('Using analysis script:', scriptPath);

    if (!process.env.GROQ_API_KEY) {
      throw new Error('GROQ_API_KEY environment variable is not set');
    }

    if (!(await fs.access(scriptPath).then(() => true).catch(() => false))) {
      throw new Error(`Python script not found at: ${scriptPath}`);
    }

    if (os.platform() === 'win32' && !(await fs.access(PYTHON_COMMAND).then(() => true).catch(() => false))) {
      throw new Error(`Python executable not found at: ${PYTHON_COMMAND}`);
    }

    const pythonProcess = spawn(PYTHON_COMMAND, [scriptPath, url, videoId], {
      env: {
        ...process.env,
        GROQ_API_KEY: process.env.GROQ_API_KEY,
        PYTHONIOENCODING: 'utf-8',
      },
    });

    let output = '';
    let error = '';

    pythonProcess.stdout.on('data', (data) => {
      const chunk = data.toString();
      output += chunk;
      console.log('Python stdout:', chunk);
    });

    pythonProcess.stderr.on('data', (data) => {
      const chunk = data.toString();
      error += chunk;
      console.error('Python stderr:', chunk);
    });

    return new Promise<NextResponse>((resolve) => {
      pythonProcess.on('close', (code) => {
        console.log('Raw Python output:', output);
        console.log('Raw Python error:', error);
        if (code !== 0) {
          console.error('Python script error:', error);
          resolve(
            NextResponse.json(
              { error: `Failed to analyze video: ${error || 'Unknown Python error'}` },
              { status: 500 }
            )
          );
          return;
        }

        try {
          const cleanedOutput = cleanOutput(output);
          console.log('Cleaned output:', cleanedOutput);
          const analysisResult = JSON.parse(cleanedOutput);

          if (!analysisResult.success) {
            resolve(
              NextResponse.json(
                { error: analysisResult.error || 'Analysis failed' },
                { status: 500 }
              )
            );
            return;
          }

          console.log('Transcript Data:', {
            totalSegments: analysisResult.transcript?.length || 0,
            firstSegment: analysisResult.transcript?.[0],
            lastSegment: analysisResult.transcript?.[analysisResult.transcript.length - 1],
          });

          resolve(NextResponse.json(analysisResult));
        } catch (e) {
          console.error('Failed to parse analysis result:', e);
          resolve(
            NextResponse.json(
              { error: `Failed to parse analysis result: ${e instanceof Error ? e.message : 'Unknown error'}` },
              { status: 500 }
            )
          );
        }
      });
    });
  } catch (error) {
    console.error('Error in analyze-video route:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}