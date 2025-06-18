'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';

declare global {
  interface Window {
    onYouTubeIframeAPIReady: () => void;
    YT: {
      Player: new (element: HTMLElement, config: unknown) => unknown;
      PlayerState: { PLAYING: number };
    };
  }
}

export function VideoUploader({ onVideoSubmit }: { onVideoSubmit: (url: string) => void }) {
  const [url, setUrl] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Function to extract YouTube video ID and validate URL
  const extractVideoId = (url: string): string | null => {
    const patterns = [
      /(?:youtube\.com\/(?:watch\?v=|embed\/|v\/)|youtu\.be\/)([^&\n?#]+)/,
      /youtube\.com\/watch\?.*v=([^&\n?#]+)/,
    ];
    for (const pattern of patterns) {
      const match = url.match(pattern);
      if (match) return match[1];
    }
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const videoId = extractVideoId(url);
    if (!videoId) {
      setError('Invalid YouTube URL. Please use a valid format (e.g., https://www.youtube.com/watch?v=...).');
      return;
    }

    try {
      await onVideoSubmit(url); // Pass the full URL to the parent
    } catch (err) {
      setError('Failed to submit video. Please try again.');
      console.error('Submission error:', err);
    }
  };

  return (
    <Card className="p-6 w-full max-w-2xl mx-auto">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <h2 className="text-2xl font-bold">Upload YouTube Video</h2>
          <p className="text-gray-500">Enter a YouTube video URL to analyze</p>
        </div>
        <div className="flex gap-2">
          <Input
            type="url"
            placeholder="https://www.youtube.com/watch?v=..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="flex-1"
            aria-invalid={!!error}
            aria-describedby={error ? 'url-error' : undefined}
          />
          <Button type="submit">Analyze</Button>
        </div>
        {error && (
          <p id="url-error" className="text-red-500 text-sm">
            {error}
          </p>
        )}
      </form>
    </Card>
  );
}