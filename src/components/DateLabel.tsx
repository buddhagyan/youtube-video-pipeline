import type {FC} from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

export type DateLabelProps = {
  /** The date as it should read on screen: "18'TH MAY 1974", "12 MARCH 1993". */
  date: string;
  /** Scene length in frames. Default: 3.5 seconds at the composition's fps. */
  durationInFrames?: number;
  /** Optional line above the date, e.g. the place. */
  kicker?: string;
  /** Optional line below the date, e.g. what the date means. */
  subtitle?: string;
};

/**
 * The Mighty Monk date stamp: huge white type on a near-black field, held for a
 * beat before the story starts. The only motion is a 3% scale settle, so the
 * frame reads as a cut-in title card rather than an animation.
 */
export const DateLabel: FC<DateLabelProps> = ({
  date,
  durationInFrames,
  kicker,
  subtitle,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const total = durationInFrames ?? Math.round(fps * 3.5);
  const lastFrame = Math.max(1, total - 1);
  const scale = interpolate(frame, [0, lastFrame], [1.035, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        background:
          'radial-gradient(115% 90% at 50% 42%, #17140f 0%, #0b0a09 58%, #050505 100%)',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'Inter, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
      }}
    >
      <div style={{transform: `scale(${scale})`, textAlign: 'center', padding: '0 8%'}}>
        {kicker ? (
          <div
            style={{
              fontSize: 30,
              letterSpacing: '0.34em',
              textTransform: 'uppercase',
              color: 'rgba(247,245,239,0.55)',
              marginBottom: 34,
            }}
          >
            {kicker}
          </div>
        ) : null}

        <div
          style={{
            fontSize: 158,
            fontWeight: 800,
            letterSpacing: '-0.02em',
            lineHeight: 1,
            color: '#f7f5ef',
            textShadow: '0 8px 60px rgba(0,0,0,0.8)',
          }}
        >
          {date}
        </div>

        <div
          style={{
            width: 120,
            height: 3,
            background: '#e8b04b',
            margin: '40px auto 0',
          }}
        />

        {subtitle ? (
          <div
            style={{
              marginTop: 34,
              fontSize: 34,
              color: 'rgba(247,245,239,0.72)',
              letterSpacing: '0.02em',
            }}
          >
            {subtitle}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
