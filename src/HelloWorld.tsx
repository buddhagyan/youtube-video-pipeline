import type {FC} from 'react';
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

export type HelloWorldProps = {
  title: string;
  subtitle: string;
};

/**
 * 5 second (150 frame @ 30 fps) title card:
 * spring-in title, delayed subtitle, animated progress bar.
 */
export const HelloWorld: FC<HelloWorldProps> = ({title, subtitle}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();

  // Spring drives both scale and opacity of the title.
  const enter = spring({
    frame,
    fps,
    config: {damping: 200, mass: 0.8, stiffness: 100},
    durationInFrames: 30,
  });

  const scale = interpolate(enter, [0, 1], [0.86, 1]);
  const titleOpacity = interpolate(enter, [0, 1], [0, 1]);

  const subtitleOpacity = interpolate(frame, [25, 55], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const progress = interpolate(frame, [0, durationInFrames - 1], [0, 1], {
    extrapolateRight: 'clamp',
  });

  // Slow decorative glow that never fully stops moving.
  const glow = interpolate(frame, [0, durationInFrames], [0.35, 0.6]);

  return (
    <AbsoluteFill
      style={{
        background:
          'linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #312e81 100%)',
        color: '#f8fafc',
        fontFamily:
          'Inter, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
      }}
    >
      <AbsoluteFill
        style={{
          alignItems: 'center',
          justifyContent: 'center',
          flexDirection: 'column',
          gap: 28,
          padding: '0 96px',
        }}
      >
        <div
          style={{
            position: 'absolute',
            width: 560,
            height: 560,
            borderRadius: '50%',
            background:
              'radial-gradient(circle, rgba(99,102,241,0.55) 0%, rgba(99,102,241,0) 70%)',
            opacity: glow,
          }}
        />
        <h1
          style={{
            position: 'relative',
            margin: 0,
            transform: `scale(${scale})`,
            opacity: titleOpacity,
            fontSize: 132,
            fontWeight: 800,
            letterSpacing: '-0.03em',
            textAlign: 'center',
            lineHeight: 1.05,
          }}
        >
          {title}
        </h1>
        <p
          style={{
            position: 'relative',
            margin: 0,
            opacity: subtitleOpacity,
            fontSize: 44,
            fontWeight: 400,
            color: '#a5b4fc',
            textAlign: 'center',
          }}
        >
          {subtitle}
        </p>
      </AbsoluteFill>

      <div
        style={{
          position: 'absolute',
          left: 96,
          right: 96,
          bottom: 72,
          height: 8,
          borderRadius: 999,
          background: 'rgba(148, 163, 184, 0.25)',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: `${progress * 100}%`,
            height: '100%',
            background: 'linear-gradient(90deg, #6366f1, #22d3ee)',
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
