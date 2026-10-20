import type {FC} from 'react';
import {Composition} from 'remotion';
import {HelloWorld, type HelloWorldProps} from './HelloWorld';
import {
  VIDEO_DURATION_IN_FRAMES,
  VIDEO_FPS,
  VIDEO_HEIGHT,
  VIDEO_WIDTH,
} from './video';

const defaultProps: HelloWorldProps = {
  title: 'Hello, Remotion!',
  subtitle: '5 second baseline composition · 1920×1080 · 30 fps',
};

/**
 * Every composition in the project is registered here.
 * The file is the entry point's root component (see src/index.ts).
 */
export const RemotionRoot: FC = () => {
  return (
    <Composition
      id="HelloWorld"
      component={HelloWorld}
      durationInFrames={VIDEO_DURATION_IN_FRAMES} // 150 frames = 5s @ 30fps
      fps={VIDEO_FPS}
      width={VIDEO_WIDTH}
      height={VIDEO_HEIGHT}
      defaultProps={defaultProps}
    />
  );
};
