import { NextResponse } from 'next/server';
import axios from 'axios';

export async function POST(req: Request) {
  try {
    const { question, video } = await req.json();

    // Validate GROQ_API_KEY
    if (!process.env.GROQ_API_KEY) {
      throw new Error('GROQ_API_KEY environment variable is not set');
    }

    // Compose a prompt with explicit title, description, and more transcript
    const prompt = `
You are an expert video assistant.

Title:
${video.metadata?.title || ''}

Description:
${video.metadata?.description || ''}

Metadata:
${JSON.stringify(video.metadata, null, 2)}

Video Uploader/ Channel: 
${video.metadata?.author || ''}
${video.metadata?.channel || ''}

Transcript (partial):
${video.transcript.slice(0, 100).map((t: { text: string }) => t.text).join(' ')}

Chapters:
${video.chapters.map((c: { title: string, summary: string }) => `${c.title}: ${c.summary}`).join('\n')}

User question: ${question}
User question: ${question}
Answer as helpfully as possible in as much detail as possible. You may use internet sources to try and understand the video/scene/topics involved in the video.
Avoid phrases like "based on the transcript" or "based on the title" or "based on the description" or "based on the metadata."
If the user asks about the owner, check information from the internet. For many answers, reference the timestamps/scenes from the video.
`;

    const response = await axios.post(
      'https://api.groq.com/openai/v1/chat/completions',
      {
        model: 'llama-3.3-70b-versatile',
        messages: [{ role: 'user', content: prompt }],
        max_tokens: 500,
        temperature: 0.7,
      },
      {
        headers: {
          'Authorization': `Bearer ${process.env.GROQ_API_KEY}`,
          'Content-Type': 'application/json'
        }
      }
    );

    const answer = response.data.choices[0]?.message?.content || 'No answer from agent.';
    return NextResponse.json({ answer });
  } catch (error) {
    console.error('Error in video-chat route:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to process chat request.' },
      { status: 500 }
    );
  }
}