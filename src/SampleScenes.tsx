import type {FC} from 'react';
import {
  AbsoluteFill,
  Sequence,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {SAMPLE_SCENES, type Scene} from './scenes';
import {VIDEO_FPS} from './video';

/**
 * Placeholder card for one scene. The real per-animation components
 * (ken_burns_zoom, text_overlay, timeline_bar, map_draw) land next; this
 * version only proves the timeline wiring: correct order, correct in/out
 * points, metadata carried through from scenes/sample.json.
 */
const ScenePlaceholder: FC<{scene: Scene; index: number; total: number}> = ({
  scene,
  index,
  total,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const sceneFrames = Math.round(scene.duration * fps);
  const progress = interpolate(frame, [0, sceneFrames], [0, 1], {
    extrapolateRight: 'clamp',
  });
  const fadeIn = interpolate(frame, [0, 8], [0, 1], {
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        background:
          'linear-gradient(160deg, #0b1120 0%, #111c33 55%, #1b2a4a 100%)',
        color: '#e2e8f0',
        fontFamily:
          'Inter, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
        padding: 96,
        justifyContent: 'space-between',
        opacity: fadeIn,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: 30,
          letterSpacing: '0.16em',
          textTransform: 'uppercase',
          color: '#7c8db5',
        }}
      >
        <span>
          Scene {scene.id} / {total}
        </span>
        <span style={{color: '#22d3ee'}}>{scene.animation_type}</span>
      </div>

      <div style={{maxWidth: 1500}}>
        <div
          style={{
            fontSize: 104,
            fontWeight: 800,
            lineHeight: 1.05,
            letterSpacing: '-0.03em',
            marginBottom: 36,
          }}
        >
          {scene.text_overlay ?? `Scene ${scene.id}`}
        </div>

        <div style={{display: 'flex', gap: 48, fontSize: 32, color: '#94a3b8'}}>
          <span>
            <span style={{color: '#64748b'}}>footage </span>
            {scene.footage_query}
          </span>
          <span>
            <span style={{color: '#64748b'}}>source </span>
            {scene.source_preference}
          </span>
        </div>

        <div style={{marginTop: 18, fontSize: 28, color: '#64748b'}}>
          {scene.start}s → {scene.end}s ({scene.duration}s) ·{' '}
          {scene.sfx_cue ?? 'no sfx'}
        </div>
      </div>

      {/* Whole-timeline strip: every scene as a segment, playhead on the current one. */}
      <div>
        <div style={{display: 'flex', gap: 8}}>
          {SAMPLE_SCENES.map((s) => {
            const isCurrent = s.id === scene.id;
            return (
              <div
                key={s.id}
                style={{
                  flex: s.duration,
                  height: 14,
                  borderRadius: 999,
                  background: isCurrent
                    ? 'linear-gradient(90deg, #6366f1, #22d3ee)'
                    : 'rgba(148, 163, 184, 0.22)',
                  position: 'relative',
                  overflow: 'hidden',
                }}
              >
                {isCurrent ? (
                  <div
                    style={{
                      width: `${progress * 100}%`,
                      height: '100%',
                      background: 'rgba(255, 255, 255, 0.55)',
                    }}
                  />
                ) : null}
              </div>
            );
          })}
        </div>
        <div
          style={{
            marginTop: 14,
            fontSize: 24,
            color: '#475569',
            letterSpacing: '0.08em',
          }}
        >
          placeholder render · scene {index + 1} of {SAMPLE_SCENES.length} ·{' '}
          {VIDEO_FPS} fps
        </div>
      </div>
    </AbsoluteFill>
  );
};

/**
 * Renders scenes/sample.json as a Remotion <Sequence> per scene.
 * Timing comes from the JSON, so editing the timeline needs no code change.
 */
export const SampleScenes: FC = () => {
  return (
    <AbsoluteFill style={{backgroundColor: '#0b1120'}}>
      {SAMPLE_SCENES.map((scene, index) => (
        <Sequence
          key={scene.id}
          name={`Scene ${scene.id} · ${scene.animation_type}`}
          from={Math.round(scene.start * VIDEO_FPS)}
          durationInFrames={Math.round(scene.duration * VIDEO_FPS)}
        >
          <ScenePlaceholder
            scene={scene}
            index={index}
            total={SAMPLE_SCENES.length}
          />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
