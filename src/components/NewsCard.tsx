import type {FC} from 'react';
import {AbsoluteFill, Img, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

export type NewsCardProps = {
  /** The article / newspaper screenshot to hold. */
  src: string;
  /** Scene length in frames. Default: 8 seconds at the composition's fps. */
  durationInFrames?: number;
  /** End scale of the slow push. Keep small: 1.03-1.08. */
  zoomTo?: number;
  /** Max width of the card as a share of the frame. */
  maxWidthPct?: number;
  /** Max height of the card as a share of the frame. */
  maxHeightPct?: number;
};

/**
 * Mighty Monk style news-card beat: the article screenshot sits still on a near
 * black field while the narrator reads it, with a very slow push so the frame is
 * never literally frozen. No fade in/out - the neighbouring scenes cut in and out.
 *
 * Sizing is height-or-width driven (`objectFit`-free), so a portrait newspaper
 * page and a landscape clipping both fit without distortion.
 */
export const NewsCard: FC<NewsCardProps> = ({
  src,
  durationInFrames,
  zoomTo = 1.05,
  maxWidthPct = 0.72,
  maxHeightPct = 0.86,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const total = durationInFrames ?? Math.round(fps * 8);
  const lastFrame = Math.max(1, total - 1);
  const scale = interpolate(frame, [0, lastFrame], [1, zoomTo], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#0a0a0b',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Img
        src={src}
        style={{
          maxWidth: `${maxWidthPct * 100}%`,
          maxHeight: `${maxHeightPct * 100}%`,
          width: 'auto',
          height: 'auto',
          display: 'block',
          transform: `scale(${scale})`,
          boxShadow:
            '0 30px 90px rgba(0,0,0,0.8), 0 0 0 1px rgba(255,255,255,0.05)',
        }}
      />
    </AbsoluteFill>
  );
};
