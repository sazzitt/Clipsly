import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  Play,
  Pause,
  Volume2,
  Volume1,
  VolumeX,
  Maximize,
  Minimize,
  RotateCcw,
  RotateCw,
  AlertCircle,
  Loader2,
  Settings,
} from "lucide-react";
import { Button } from "../../../components/ui/button";
import { api } from "../../../services/api";
import { cn } from "../../../lib/utils";

export interface VideoPlayerProps {
  videoId: string;
  title?: string;
  className?: string;
  autoPlay?: boolean;
}

const PLAYBACK_SPEEDS = [0.5, 0.75, 1, 1.25, 1.5, 2];

function formatPlayerTime(seconds: number): string {
  if (isNaN(seconds) || seconds < 0) return "0:00";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);

  if (h > 0) {
    return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  }
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({
  videoId,
  title,
  className,
  autoPlay = false,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const hideControlsTimerRef = useRef<NodeJS.Timeout | null>(null);

  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [duration, setDuration] = useState<number>(0);
  const [bufferedEnd, setBufferedEnd] = useState<number>(0);
  const [volume, setVolume] = useState<number>(1);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1);
  const [showSpeedMenu, setShowSpeedMenu] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [isBuffering, setIsBuffering] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [showControls, setShowControls] = useState<boolean>(true);
  const [isScrubbing, setIsScrubbing] = useState<boolean>(false);

  const streamUrl = api.videos.getStreamUrl(videoId);

  // Manage control visibility auto-hide during playback
  const resetHideControlsTimer = useCallback(() => {
    setShowControls(true);
    if (hideControlsTimerRef.current) {
      clearTimeout(hideControlsTimerRef.current);
      hideControlsTimerRef.current = null;
    }
    if (isPlaying && !isScrubbing) {
      hideControlsTimerRef.current = setTimeout(() => {
        setShowControls(false);
        setShowSpeedMenu(false);
      }, 2500);
    }
  }, [isPlaying, isScrubbing]);

  const handleMouseMove = () => {
    resetHideControlsTimer();
  };

  const handleMouseLeave = () => {
    if (isPlaying && !isScrubbing) {
      setShowControls(false);
      setShowSpeedMenu(false);
    }
  };

  // Play / Pause toggle
  const togglePlay = useCallback(() => {
    if (!videoRef.current) return;
    if (videoRef.current.paused || videoRef.current.ended) {
      const p = videoRef.current.play?.();
      if (p && typeof p.catch === "function") {
        p.catch((err) => {
          console.error("Playback error:", err);
        });
      }
    } else {
      videoRef.current.pause?.();
    }
  }, []);

  // Seek
  const handleSeekChange = (newTime: number) => {
    setCurrentTime(newTime);
    if (videoRef.current) {
      videoRef.current.currentTime = newTime;
    }
  };

  const skipSeconds = useCallback((delta: number) => {
    if (!videoRef.current) return;
    const target = Math.max(0, Math.min(videoRef.current.duration || 0, videoRef.current.currentTime + delta));
    videoRef.current.currentTime = target;
    setCurrentTime(target);
  }, []);

  // Volume
  const handleVolumeChange = useCallback((newVol: number) => {
    const clamped = Math.max(0, Math.min(1, newVol));
    setVolume(clamped);
    if (videoRef.current) {
      videoRef.current.volume = clamped;
      videoRef.current.muted = clamped === 0;
    }
    setIsMuted(clamped === 0);
  }, []);

  const toggleMute = useCallback(() => {
    if (!videoRef.current) return;
    const newMuted = !isMuted;
    setIsMuted(newMuted);
    videoRef.current.muted = newMuted;
    if (!newMuted && volume === 0) {
      setVolume(0.5);
      videoRef.current.volume = 0.5;
    }
  }, [isMuted, volume]);

  // Speed
  const handleSpeedSelect = (speed: number) => {
    setPlaybackSpeed(speed);
    if (videoRef.current) {
      videoRef.current.playbackRate = speed;
    }
    setShowSpeedMenu(false);
  };

  // Fullscreen
  const toggleFullscreen = useCallback(() => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen?.().catch((err) => {
        console.error("Fullscreen error:", err);
      });
    } else {
      document.exitFullscreen?.().catch((err) => {
        console.error("Exit fullscreen error:", err);
      });
    }
  }, []);

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () => {
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
    };
  }, []);

  // Reload on error / retry
  const handleRetry = () => {
    setError(null);
    setIsBuffering(true);
    if (videoRef.current) {
      videoRef.current.load?.();
      const p = videoRef.current.play?.();
      if (p && typeof p.catch === "function") {
        p.catch(() => {
          setIsBuffering(false);
        });
      }
    }
  };

  // Keyboard shortcut handler
  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    // Avoid intercepting when typing in inputs/textareas
    if (
      e.target instanceof HTMLInputElement ||
      e.target instanceof HTMLTextAreaElement ||
      e.target instanceof HTMLSelectElement
    ) {
      return;
    }

    switch (e.key) {
      case " ":
      case "k":
        e.preventDefault();
        togglePlay();
        break;
      case "ArrowLeft":
        e.preventDefault();
        skipSeconds(-5);
        break;
      case "ArrowRight":
        e.preventDefault();
        skipSeconds(5);
        break;
      case "ArrowUp":
        e.preventDefault();
        handleVolumeChange(volume + 0.1);
        break;
      case "ArrowDown":
        e.preventDefault();
        handleVolumeChange(volume - 0.1);
        break;
      case "m":
      case "M":
        e.preventDefault();
        toggleMute();
        break;
      case "f":
      case "F":
        e.preventDefault();
        toggleFullscreen();
        break;
      default:
        break;
    }
  };

  // Update buffer progress
  const updateBufferedProgress = () => {
    if (!videoRef.current) return;
    const buf = videoRef.current.buffered;
    if (buf.length > 0) {
      for (let i = buf.length - 1; i >= 0; i--) {
        if (buf.start(i) <= videoRef.current.currentTime) {
          setBufferedEnd(buf.end(i));
          break;
        }
      }
    }
  };

  const progressPercent = duration > 0 ? (currentTime / duration) * 100 : 0;
  const bufferedPercent = duration > 0 ? Math.min(100, (bufferedEnd / duration) * 100) : 0;

  return (
    <div
      ref={containerRef}
      tabIndex={0}
      onKeyDown={handleKeyDown}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className={cn(
        "group relative overflow-hidden rounded-xl bg-black border border-border/70 select-none outline-none focus-visible:ring-1 focus-visible:ring-primary shadow-xl",
        isFullscreen ? "h-screen w-screen rounded-none border-none" : "aspect-video w-full",
        className
      )}
      data-testid="video-player-container"
      aria-label={title ? `Video Player: ${title}` : "Video Player"}
    >
      {/* HTML5 Video Element */}
      <video
        ref={videoRef}
        src={streamUrl}
        preload="metadata"
        autoPlay={autoPlay}
        playsInline
        onClick={togglePlay}
        onTimeUpdate={() => {
          if (!isScrubbing && videoRef.current) {
            setCurrentTime(videoRef.current.currentTime);
          }
          updateBufferedProgress();
        }}
        onDurationChange={() => {
          if (videoRef.current) {
            setDuration(videoRef.current.duration || 0);
          }
        }}
        onProgress={updateBufferedProgress}
        onPlay={() => {
          setIsPlaying(true);
          resetHideControlsTimer();
        }}
        onPause={() => {
          setIsPlaying(false);
          setShowControls(true);
        }}
        onWaiting={() => setIsBuffering(true)}
        onPlaying={() => setIsBuffering(false)}
        onEnded={() => {
          setIsPlaying(false);
          setShowControls(true);
        }}
        onError={() => {
          setIsBuffering(false);
          setError("Failed to stream video. The file may be corrupt or the local server is unreachable.");
        }}
        className="h-full w-full object-contain cursor-pointer"
        data-testid="html5-video-element"
      />

      {/* Buffering Indicator */}
      {isBuffering && !error && (
        <div
          className="pointer-events-none absolute inset-0 flex items-center justify-center bg-black/40 backdrop-blur-[2px] transition-opacity"
          data-testid="video-buffering-spinner"
        >
          <div className="flex flex-col items-center gap-2 rounded-lg bg-zinc-900/90 border border-zinc-700/60 px-4 py-3 shadow-2xl">
            <Loader2 className="h-7 w-7 animate-spin text-primary" />
            <span className="text-xs font-mono text-zinc-300">Buffering Stream...</span>
          </div>
        </div>
      )}

      {/* Large Center Play Overlay (when paused & not buffering & no error) */}
      {!isPlaying && !isBuffering && !error && (
        <div
          onClick={togglePlay}
          className="absolute inset-0 flex items-center justify-center bg-black/30 cursor-pointer transition-all hover:bg-black/40"
          data-testid="center-play-button"
        >
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/90 text-primary-foreground shadow-2xl transition-transform hover:scale-110 active:scale-95">
            <Play className="h-8 w-8 ml-1" fill="currentColor" />
          </div>
        </div>
      )}

      {/* Stream Error Overlay */}
      {error && (
        <div
          className="absolute inset-0 flex flex-col items-center justify-center bg-zinc-950/95 p-6 text-center space-y-3 z-30"
          data-testid="video-stream-error"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/20 text-destructive">
            <AlertCircle className="h-6 w-6" />
          </div>
          <h4 className="text-sm font-semibold text-foreground">Video Stream Error</h4>
          <p className="text-xs text-muted-foreground max-w-sm">{error}</p>
          <Button
            size="sm"
            variant="outline"
            onClick={handleRetry}
            className="text-xs gap-1.5 h-8 border-zinc-700 hover:bg-zinc-800"
            data-testid="video-retry-button"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>Retry Stream</span>
          </Button>
        </div>
      )}

      {/* Title Bar (shown on hover or when paused) */}
      {title && (
        <div
          className={cn(
            "absolute top-0 inset-x-0 bg-gradient-to-b from-black/80 via-black/40 to-transparent px-4 py-3 transition-opacity duration-300 pointer-events-none z-20",
            showControls || !isPlaying ? "opacity-100" : "opacity-0"
          )}
        >
          <span className="text-xs font-medium text-zinc-200 line-clamp-1" data-testid="player-title">
            Preview: {title}
          </span>
        </div>
      )}

      {/* Custom Control Bar Overlay */}
      <div
        className={cn(
          "absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/95 via-black/75 to-transparent px-4 pt-8 pb-3 transition-opacity duration-300 z-20 flex flex-col gap-2",
          showControls || !isPlaying ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        )}
        data-testid="video-controls-bar"
      >
        {/* Scrubber / Seek Bar */}
        <div className="relative group/scrubber flex items-center h-4 cursor-pointer select-none">
          <input
            type="range"
            min={0}
            max={duration > 0 ? duration : 100}
            step={0.1}
            value={currentTime}
            onMouseDown={() => setIsScrubbing(true)}
            onMouseUp={() => setIsScrubbing(false)}
            onChange={(e) => handleSeekChange(Number(e.target.value))}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
            aria-label="Seek video position"
            data-testid="seek-slider"
          />

          {/* Track Background */}
          <div className="relative h-1.5 group-hover/scrubber:h-2.5 w-full rounded-full bg-zinc-800 transition-all overflow-hidden">
            {/* Buffered Bar */}
            <div
              className="absolute h-full bg-zinc-600/70 rounded-full transition-all"
              style={{ width: `${bufferedPercent}%` }}
              data-testid="seek-buffered-bar"
            />
            {/* Played Progress Bar */}
            <div
              className="absolute h-full bg-primary rounded-full transition-all"
              style={{ width: `${progressPercent}%` }}
              data-testid="seek-progress-bar"
            />
          </div>

          {/* Scrubber Thumb */}
          <div
            className="absolute h-3.5 w-3.5 rounded-full bg-primary border-2 border-white shadow-md transition-transform scale-0 group-hover/scrubber:scale-100 pointer-events-none -ml-1.5"
            style={{ left: `${progressPercent}%` }}
          />
        </div>

        {/* Lower Controls Row */}
        <div className="flex items-center justify-between gap-2 text-white text-xs">
          {/* Left Controls: Play, Skips, Time */}
          <div className="flex items-center gap-1.5">
            <button
              onClick={togglePlay}
              className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-white/10 active:scale-95 transition-all text-zinc-200 hover:text-white"
              aria-label={isPlaying ? "Pause video" : "Play video"}
              data-testid="play-pause-button"
            >
              {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4 fill-current" />}
            </button>

            <button
              onClick={() => skipSeconds(-5)}
              className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-white/10 active:scale-95 transition-all text-zinc-300 hover:text-white"
              title="Seek back 5 seconds (Left Arrow)"
              aria-label="Seek backward 5 seconds"
              data-testid="skip-back-button"
            >
              <RotateCcw className="h-3.5 w-3.5" />
            </button>

            <button
              onClick={() => skipSeconds(5)}
              className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-white/10 active:scale-95 transition-all text-zinc-300 hover:text-white"
              title="Seek forward 5 seconds (Right Arrow)"
              aria-label="Seek forward 5 seconds"
              data-testid="skip-forward-button"
            >
              <RotateCw className="h-3.5 w-3.5" />
            </button>

            {/* Volume Control */}
            <div className="group/vol flex items-center gap-1.5 ml-1">
              <button
                onClick={toggleMute}
                className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-white/10 active:scale-95 transition-all text-zinc-300 hover:text-white"
                aria-label={isMuted ? "Unmute video" : "Mute video"}
                data-testid="mute-button"
              >
                {isMuted || volume === 0 ? (
                  <VolumeX className="h-4 w-4 text-zinc-400" />
                ) : volume < 0.5 ? (
                  <Volume1 className="h-4 w-4" />
                ) : (
                  <Volume2 className="h-4 w-4" />
                )}
              </button>

              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={isMuted ? 0 : volume}
                onChange={(e) => handleVolumeChange(Number(e.target.value))}
                className="w-16 h-1 bg-zinc-700 accent-primary rounded-full cursor-pointer opacity-80 group-hover/vol:opacity-100 transition-opacity"
                aria-label="Volume slider"
                data-testid="volume-slider"
              />
            </div>

            {/* Time Display */}
            <div className="ml-2 font-mono text-[11px] text-zinc-300 tabular-nums" data-testid="time-display">
              <span>{formatPlayerTime(currentTime)}</span>
              <span className="text-zinc-500 mx-1">/</span>
              <span>{formatPlayerTime(duration)}</span>
            </div>
          </div>

          {/* Right Controls: Speed Selector, Fullscreen */}
          <div className="flex items-center gap-1.5 relative">
            {/* Speed Selector */}
            <div className="relative">
              <button
                onClick={() => setShowSpeedMenu(!showSpeedMenu)}
                className="flex h-8 items-center gap-1 px-2 rounded-lg hover:bg-white/10 active:scale-95 transition-all text-xs font-mono font-medium text-zinc-300 hover:text-white"
                aria-label="Playback speed"
                data-testid="speed-selector-button"
              >
                <Settings className="h-3 w-3 text-zinc-400" />
                <span>{playbackSpeed}x</span>
              </button>

              {showSpeedMenu && (
                <div
                  className="absolute bottom-10 right-0 rounded-lg bg-zinc-900 border border-zinc-700/80 p-1.5 shadow-2xl flex flex-col gap-0.5 min-w-[72px] z-30"
                  data-testid="speed-dropdown-menu"
                >
                  <span className="text-[10px] uppercase font-mono text-zinc-500 px-2 py-0.5">Speed</span>
                  {PLAYBACK_SPEEDS.map((s) => (
                    <button
                      key={s}
                      onClick={() => handleSpeedSelect(s)}
                      className={cn(
                        "px-2 py-1 text-left rounded text-xs font-mono transition-colors",
                        playbackSpeed === s
                          ? "bg-primary text-primary-foreground font-semibold"
                          : "text-zinc-300 hover:bg-zinc-800 hover:text-white"
                      )}
                      data-testid={`speed-option-${s}`}
                    >
                      {s}x
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Fullscreen Button */}
            <button
              onClick={toggleFullscreen}
              className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-white/10 active:scale-95 transition-all text-zinc-300 hover:text-white"
              aria-label={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
              data-testid="fullscreen-button"
            >
              {isFullscreen ? <Minimize className="h-4 w-4" /> : <Maximize className="h-4 w-4" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
