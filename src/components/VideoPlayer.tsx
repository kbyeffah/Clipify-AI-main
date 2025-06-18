'use client';

import React, { forwardRef, useImperativeHandle, useRef, useEffect } from 'react';

export interface YouTubePlayerHandle {
  seekTo: (seconds: number) => void;
}

interface YouTubePlayerProps {
  videoId: string;
  onTimeUpdate: (time: number) => void;
}

const YouTubePlayer = forwardRef<YouTubePlayerHandle, YouTubePlayerProps>(({ videoId, onTimeUpdate }, ref) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Poll iframe for current time
    intervalRef.current = setInterval(() => {
      if (iframeRef.current) {
        iframeRef.current.contentWindow?.postMessage(
          JSON.stringify({ event: 'command', func: 'getCurrentTime' }),
          'https://www.youtube.com'
        );
      }
    }, 1000);

    // Listen for messages from iframe
    const handleMessage = (event: MessageEvent) => {
      if (event.origin !== 'https://www.youtube.com') return;
      try {
        const data = JSON.parse(event.data);
        if (data.event === 'infoDelivery' && data.info?.currentTime) {
          onTimeUpdate(data.info.currentTime);
        }
      } catch {}
    };

    window.addEventListener('message', handleMessage);
    return () => {
      window.removeEventListener('message', handleMessage);
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [onTimeUpdate]);

  useImperativeHandle(ref, () => ({
    seekTo: (seconds: number) => {
      if (iframeRef.current) {
        iframeRef.current.contentWindow?.postMessage(
          JSON.stringify({ event: 'command', func: 'seekTo', args: [seconds, true] }),
          'https://www.youtube.com'
        );
      }
    },
  }));

  return (
    <div className="relative w-full aspect-video">
      <iframe
        ref={iframeRef}
        className="absolute top-0 left-0 w-full h-full"
        src={`https://www.youtube.com/embed/${videoId}?enablejsapi=1&origin=${encodeURIComponent(window.location.origin)}`}
        title="YouTube video player"
        frameBorder="0"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowFullScreen
      ></iframe>
    </div>
  );
});

YouTubePlayer.displayName = 'YouTubePlayer';

export default YouTubePlayer;