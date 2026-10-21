import type {FC} from 'react';
import {AbsoluteFill, Sequence, staticFile} from 'remotion';
import {SCENE_ASSETS} from './assets';
import {DateLabel} from './components/DateLabel';
import {EndCard} from './components/EndCard';
import {KenBurnsZoom} from './components/KenBurnsZoom';
import {NewsCard} from './components/NewsCard';
import {TextOverlay} from './components/TextOverlay';
import {TimelineBar} from './components/TimelineBar';
import {SAMPLE_SCENES, type Scene} from './scenes';
import {VIDEO_FPS} from './video';

const framesOf = (scene: Scene) => Math.round(scene.duration * VIDEO_FPS);

/** Footage scenes: Ken Burns photo + optional lower third / timeline bar. */
const FootageScene: FC<{scene: Scene}> = ({scene}) => {
  const asset = SCENE_ASSETS[scene.id];
  if (!asset) {
    throw new Error(
      `No footage mapped for scene ${scene.id} in src/assets.ts. ` +
        `Add the resolved file for "${scene.footage_query}".`,
    );
  }
  const durationInFrames = framesOf(scene);

  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      <KenBurnsZoom
        src={asset.src}
        durationInFrames={durationInFrames}
        zoomTo={asset.zoomTo}
        focalPoint={asset.focalPoint}
        fadeInFrames={0}
        fadeOutFrames={0}
      />
      {scene.text_overlay ? (
        <TextOverlay text={scene.text_overlay} durationInFrames={durationInFrames} />
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
 * One scene, one component. The animation_type in scenes/sample.json decides
 * which one - no fallbacks, so an unknown type fails at bundle time.
 */
const SceneLayer: FC<{scene: Scene}> = ({scene}) => {
  const durationInFrames = framesOf(scene);

  switch (scene.animation_type) {
    case 'date_label':
      return (
        <DateLabel
          date={scene.text_overlay ?? ''}
          durationInFrames={durationInFrames}
        />
      );

    case 'still_card': {
      if (!scene.card_image) {
        throw new Error(`Scene ${scene.id} is a still_card without a card_image`);
      }
      return (
        <NewsCard
          src={staticFile(scene.card_image)}
          durationInFrames={durationInFrames}
        />
      );
    }

    case 'end_card':
      return (
        <EndCard
          title={scene.text_overlay ?? 'ARCHIVE'}
          subtitle="Subscribe"
          footnote="A new film every Sunday"
        />
      );

    case 'ken_burns_zoom':
    case 'text_overlay':
    case 'timeline_bar':
      return <FootageScene scene={scene} />;

    default: {
      const exhaustive: never = scene.animation_type;
      throw new Error(`Unhandled animation_type: ${exhaustive}`);
    }
  }
};

/**
 * Renders scenes/sample.json as a Remotion <Sequence> per scene, cutting
 * between them with hard cuts. Timing comes from the JSON, so editing the
 * timeline needs no code change.
 */
export const SampleScenes: FC = () => {
  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      {SAMPLE_SCENES.map((scene) => (
        <Sequence
          key={scene.id}
          name={`Scene ${scene.id} · ${scene.animation_type}`}
          from={Math.round(scene.start * VIDEO_FPS)}
          durationInFrames={framesOf(scene)}
        >
          <SceneLayer scene={scene} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
