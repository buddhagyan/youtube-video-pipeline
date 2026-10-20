import type {FC} from 'react';
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

export type TimelineBarLabel = {
  /** Seconds from the start of the scene. */
  at: number;
  /** Usually a year: "1977", "2012". */
  label: string;
};

export type TimelineBarProps = {
  /** Scene length in frames. Default: 5 seconds at the composition's fps. */
  durationInFrames?: number;
  /** Optional markers along the bar. Labels light up as the bar passes them. */
  labels?: TimelineBarLabel[];
  fadeInFrames?: number;
  fadeOutFrames?: number;
};

const ACCENT = '#e8b04b';
const TRACK = 'rgba(248, 250, 252, 0.26)';

/**
 * Thin progress line in the lower third: the fill grows with the scene, and
 * optional year markers light up as the playhead reaches them.
 *
 * The bar is drawn from `interpolate` over the scene length, so it is
 * frame-exact and resumes correctly on any render range.
 */
export const TimelineBar: FC<TimelineBarProps> = ({
  durationInFrames,
  labels = [],
  fadeInFrames = 10,
  fadeOutFrames = 10,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const total = durationInFrames ?? Math.round(fps * 5);
  const lastFrame = Math.max(1, total - 1);
  const seconds = total / fps;

  const progress = interpolate(frame, [0, lastFrame], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const opacity = Math.min(
    fadeInFrames > 0
      ? interpolate(frame, [0, fadeInFrames], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        })
      : 1,
    fadeOutFrames > 0
      ? interpolate(
          frame,
          [Math.max(0, lastFrame - fadeOutFrames), lastFrame],
          [1, 0],
          {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
        )
      : 1,
  );

  const anchor = (fraction: number): string =>
    fraction <= 0 ? '0%' : fraction >= 1 ? '-100%' : '-50%';

  return (
    <AbsoluteFill style={{pointerEvents: 'none', opacity}}>
      <div
        style={{
          position: 'absolute',
          left: 96,
          right: 96,
          bottom: 112,
          fontFamily:
            'Inter, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
        }}
      >
        {labels.map(({at, label}) => {
          const fraction = Math.min(1, Math.max(0, at / seconds));
          const reached = progress >= fraction - 1e-4;
          const labelOpacity = interpolate(
            progress,
            [fraction - 0.015, fraction + 0.015],
            [0.4, 1],
            {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
          );

          return (
            <div
              key={`${at}-${label}`}
              style={{
                position: 'absolute',
                left: `${fraction * 100}%`,
                bottom: 26,
                transform: `translateX(${anchor(fraction)})`,
                display: 'flex',
                flexDirection: 'column',
                alignItems:
                  fraction <= 0
                    ? 'flex-start'
                    : fraction >= 1
                      ? 'flex-end'
                      : 'center',
                gap: 8,
                opacity: labelOpacity,
              }}
            >
              <span
                style={{
                  fontSize: 24,
                  fontWeight: reached ? 600 : 400,
                  letterSpacing: '0.1em',
                  color: reached ? '#f8fafc' : 'rgba(248, 250, 252, 0.55)',
                  textShadow: '0 1px 12px rgba(0,0,0,0.7)',
                  whiteSpace: 'nowrap',
                }}
              >
                {label}
              </span>
              <span
                style={{
                  width: 1,
                  height: 10,
                  backgroundColor: reached ? ACCENT : TRACK,
                }}
              />
            </div>
          );
        })}

        {/* Track */}
        <div
          style={{
            height: 3,
            borderRadius: 999,
            backgroundColor: TRACK,
            overflow: 'hidden',
          }}
        >
          {/* Fill: grows with time */}
          <div
            style={{
              width: `${progress * 100}%`,
              height: '100%',
              background: `linear-gradient(90deg, ${ACCENT}, #f6d79a)`,
            }}
          />
        </div>

        {/* Playhead */}
        <div
          style={{
            position: 'absolute',
            left: `${progress * 100}%`,
            bottom: -3,
            width: 10,
            height: 10,
            marginLeft: -5,
            borderRadius: '50%',
            backgroundColor: '#ffffff',
            boxShadow: '0 0 10px rgba(232, 176, 75, 0.9)',
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
