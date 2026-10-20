import type {FC} from 'react';
import {AbsoluteFill, Composition, staticFile} from 'remotion';
import {HelloWorld, type HelloWorldProps} from './HelloWorld';
import {SampleScenes} from './SampleScenes';
import {KenBurnsZoom} from './components/KenBurnsZoom';
import {TextOverlay} from './components/TextOverlay';
import {TimelineBar} from './components/TimelineBar';
import {SAMPLE_SCENES_DURATION_IN_FRAMES} from './scenes';
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

/** 5 second push-in on a real photo — the KenBurnsZoom smoke test. */
const KenBurnsTest: FC = () => {
  return (
    <KenBurnsZoom
      src={staticFile('assets/voyager-golden-record-gold-plating.jpg')}
      durationInFrames={150}
      zoomFrom={1}
      zoomTo={1.14}
      focalPoint={{x: 0.45, y: 0.5}}
    />
  );
};

/** 5 second lower third over a moving photo — the TextOverlay smoke test. */
const TextOverlayTest: FC = () => {
  return (
    <AbsoluteFill>
      <KenBurnsZoom
        src={staticFile('assets/voyager-golden-record-gold-plating.jpg')}
        durationInFrames={150}
        zoomTo={1.12}
        focalPoint={{x: 0.45, y: 0.5}}
      />
      <TextOverlay
        text="The Golden Record — a message to the stars"
        durationInFrames={150}
      />
    </AbsoluteFill>
  );
};

/** 5 second progress bar with year markers — the TimelineBar smoke test. */
const TimelineBarTest: FC = () => {
  return (
    <AbsoluteFill>
      <KenBurnsZoom
        src={staticFile('assets/pale-blue-dot-1990.jpg')}
        durationInFrames={150}
        zoomTo={1.1}
        focalPoint={{x: 0.5, y: 0.5}}
      />
      <TimelineBar
        durationInFrames={150}
        labels={[
          {at: 0, label: '1977'},
          {at: 2.5, label: '1990'},
          {at: 5, label: '2012'},
        ]}
      />
    </AbsoluteFill>
  );
};

/**
 * Every composition in the project is registered here.
 * The file is the entry point's root component (see src/index.ts).
 */
export const RemotionRoot: FC = () => {
  return (
    <>
      <Composition
        id="HelloWorld"
        component={HelloWorld}
        durationInFrames={VIDEO_DURATION_IN_FRAMES} // 150 frames = 5s @ 30fps
        fps={VIDEO_FPS}
        width={VIDEO_WIDTH}
        height={VIDEO_HEIGHT}
        defaultProps={defaultProps}
      />
      <Composition
        id="SampleScenes"
        component={SampleScenes}
        // Derived from scenes/sample.json (last scene's end × fps), not hard-coded.
        durationInFrames={SAMPLE_SCENES_DURATION_IN_FRAMES}
        fps={VIDEO_FPS}
        width={VIDEO_WIDTH}
        height={VIDEO_HEIGHT}
      />
      <Composition
        id="KenBurnsTest"
        component={KenBurnsTest}
        durationInFrames={150} // 5s @ 30fps
        fps={VIDEO_FPS}
        width={VIDEO_WIDTH}
        height={VIDEO_HEIGHT}
      />
      <Composition
        id="TextOverlayTest"
        component={TextOverlayTest}
        durationInFrames={150} // 5s @ 30fps
        fps={VIDEO_FPS}
        width={VIDEO_WIDTH}
        height={VIDEO_HEIGHT}
      />
      <Composition
        id="TimelineBarTest"
        component={TimelineBarTest}
        durationInFrames={150} // 5s @ 30fps
        fps={VIDEO_FPS}
        width={VIDEO_WIDTH}
        height={VIDEO_HEIGHT}
      />
    </>
  );
};
