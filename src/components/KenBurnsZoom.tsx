import type {CSSProperties, FC} from 'react';
import {
  AbsoluteFill,
  Easing,
  Img,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

export type KenBurnsZoomProps = {
  /** Image to move over. Local `staticFile(...)` path or any absolute URL. */
  src: string;
  /** Scene length in frames. Default: 5 seconds at the composition's fps. */
  durationInFrames?: number;
  /** Scale at the first frame (1 = fits the frame, no extra zoom). */
  zoomFrom?: number;
  /** Scale at the last frame. Keep <= ~1.25 so the photo never looks soft. */
  zoomTo?: number;
  /** Zoom anchor as a fraction of the image, 0-1. Default: dead centre. */
  focalPoint?: {x: number; y: number};
  /** Frames spent fading in from black. 0 disables the fade. */
  fadeInFrames?: number;
  /** Frames spent fading out to black. 0 disables the fade. */
  fadeOutFrames?: number;
  style?: CSSProperties;
};

/**
 * Mighty Monk style still: a real photo with a slow, continuous push-in.
 *
 * - Zoom is driven by `interpolate` over the scene length, so it is frame-exact
 *   and identical on every render (no CSS animation, no timers).
 * - `transformOrigin` puts the anchor on the focal point, which gives a natural
 *   push instead of a drift.
 * - Fades are opacity-only, so the image never jumps size at the cut.
 */
export const KenBurnsZoom: FC<KenBurnsZoomProps> = ({
  src,
  durationInFrames,
  zoomFrom = 1,
  zoomTo = 1.14,
  focalPoint = {x: 0.5, y: 0.5},
  fadeInFrames = 12,
  fadeOutFrames = 12,
  style,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const total = durationInFrames ?? Math.round(fps * 5);
  const lastFrame = Math.max(1, total - 1);

  const scale = interpolate(frame, [0, lastFrame], [zoomFrom, zoomTo], {
    easing: Easing.inOut(Easing.cubic),
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const fadeIn =
    fadeInFrames > 0
      ? interpolate(frame, [0, fadeInFrames], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        })
      : 1;

  const fadeOut =
    fadeOutFrames > 0
      ? interpolate(
          frame,
          [Math.max(0, lastFrame - fadeOutFrames), lastFrame],
          [1, 0],
          {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
        )
      : 1;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#000',
        overflow: 'hidden',
        opacity: Math.min(fadeIn, fadeOut),
        ...style,
      }}
    >
      <Img
        src={src}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transform: `scale(${scale})`,
          transformOrigin: `${focalPoint.x * 100}% ${focalPoint.y * 100}%`,
        }}
      />
    </AbsoluteFill>
  );
};
