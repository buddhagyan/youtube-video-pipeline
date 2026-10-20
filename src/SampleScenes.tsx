import type {FC} from 'react';
import {AbsoluteFill, Sequence} from 'remotion';
import {SCENE_ASSETS} from './assets';
import {KenBurnsZoom} from './components/KenBurnsZoom';
import {TextOverlay} from './components/TextOverlay';
import {TimelineBar} from './components/TimelineBar';
import {SAMPLE_SCENES, type Scene} from './scenes';
import {VIDEO_FPS} from './video';

/**
 * One scene = a Ken Burns photo, plus the layers the timeline asks for:
 * a lower third when the scene carries text, and a timeline bar when the
 * scene's `animation_type` is `timeline_bar`.
 */
const SceneLayer: FC<{scene: Scene}> = ({scene}) => {
  const durationInFrames = Math.round(scene.duration * VIDEO_FPS);
  const asset = SCENE_ASSETS[scene.id];

  if (!asset) {
    throw new Error(
      `No footage mapped for scene ${scene.id} in src/assets.ts. ` +
        `Add the resolved file for "${scene.footage_query}".`,
    );
  }

  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      <KenBurnsZoom
        src={asset.src}
        durationInFrames={durationInFrames}
        zoomTo={asset.zoomTo}
        focalPoint={asset.focalPoint}
        fadeInFrames={16}
        fadeOutFrames={16}
      />

      {scene.text_overlay ? (
        <TextOverlay
          text={scene.text_overlay}
          durationInFrames={durationInFrames}
        />
      ) : null}

      {scene.animation_type === 'timeline_bar' ? (
        <TimelineBar
          durationInFrames={durationInFrames}
          labels={asset.timelineLabels}
        />
      ) : null}
    </AbsoluteFill>
  );
};

/**
 * Renders scenes/sample.json as a Remotion <Sequence> per scene.
 * Timing comes from the JSON, so editing the timeline needs no code change.
 */
export const SampleScenes: FC = () => {
  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      {SAMPLE_SCENES.map((scene) => (
        <Sequence
          key={scene.id}
          name={`Scene ${scene.id} · ${scene.animation_type}`}
          from={Math.round(scene.start * VIDEO_FPS)}
          durationInFrames={Math.round(scene.duration * VIDEO_FPS)}
        >
          <SceneLayer scene={scene} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
