import type {FC} from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

export type TextOverlayProps = {
  /** The line shown in the lower third. Keep it short: one sentence max. */
  text: string;
  /** Scene length in frames. Default: 5 seconds at the composition's fps. */
  durationInFrames?: number;
  fadeInFrames?: number;
  fadeOutFrames?: number;
};

/**
 * Mighty Monk style lower third: one bold line, bottom of the frame, no
 * decoration beyond a short accent rule. Fades in and out, plus a tiny
 * upward slide so the text settles instead of popping.
 *
 * A soft bottom gradient is part of the component, so the text stays legible
 * over any photo without the caller adding a scrim.
 */
export const TextOverlay: FC<TextOverlayProps> = ({
  text,
  durationInFrames,
  fadeInFrames = 14,
  fadeOutFrames = 14,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const total = durationInFrames ?? Math.round(fps * 5);
  const lastFrame = Math.max(1, total - 1);

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

  const rise = interpolate(frame, [0, fadeInFrames + 6], [18, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{pointerEvents: 'none', opacity}}>
      {/* Legibility scrim: fades out before the text does, so the photo stays clean. */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 0,
          height: '58%',
          background:
            'linear-gradient(to top, rgba(0,0,0,0.78) 0%, rgba(0,0,0,0.38) 48%, rgba(0,0,0,0) 100%)',
        }}
      />

      <div
        style={{
          position: 'absolute',
          left: 96,
          right: 96,
          bottom: 170,
          transform: `translateY(${rise}px)`,
          fontFamily:
            'Inter, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
        }}
      >
        <div
          style={{
            width: 64,
            height: 4,
            backgroundColor: '#e8b04b',
            marginBottom: 28,
          }}
        />
        <div
          style={{
            maxWidth: 1180,
            color: '#ffffff',
            fontSize: 60,
            fontWeight: 700,
            lineHeight: 1.28,
            letterSpacing: '-0.01em',
            textShadow:
              '0 2px 26px rgba(0,0,0,0.55), 0 1px 3px rgba(0,0,0,0.45)',
            textWrap: 'balance',
          }}
        >
          {text}
        </div>
      </div>
    </AbsoluteFill>
  );
};
