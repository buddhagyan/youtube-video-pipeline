import sampleJson from '../scenes/sample.json';
import {VIDEO_FPS} from './video';

export type SourcePreference = 'nasa' | 'wikimedia' | 'archive';

/**
 * Locked to the six-film measurements (scenes/mighty-monk-master-analysis.json):
 * footage scenes 3-6 s, still_card 6-45 s, end_card 6-20 s, cuts only.
 */
export type AnimationType =
  | 'ken_burns_zoom'
  | 'text_overlay'
  | 'timeline_bar'
  | 'still_card'
  | 'date_label'
  | 'end_card';

export type Scene = {
  id: number;
  start: number;
  end: number;
  duration: number;
  footage_query: string;
  source_preference: SourcePreference;
  animation_type: AnimationType;
  text_overlay: string | null;
  card_image: string | null;
  sfx_cue: string | null;
  transition_in: 'cut';
};

/** Measured pacing window per animation type, in seconds. */
export const DURATION_POLICY: Record<AnimationType, [number, number]> = {
  ken_burns_zoom: [3, 6],
  text_overlay: [3, 6],
  timeline_bar: [3, 6],
  date_label: [2, 4],
  still_card: [6, 45],
  // The reference films close on 10-21 s cards; the 20 s test compresses this.
  end_card: [2, 20],
};

const SOURCES: readonly string[] = ['nasa', 'wikimedia', 'archive'];
const ANIMATIONS = Object.keys(DURATION_POLICY);
const TRANSITIONS: readonly string[] = ['cut'];

const EPSILON = 1e-6;

const fail = (message: string): never => {
  throw new Error(`scenes/sample.json is invalid: ${message}`);
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

/**
 * Validates the timeline against scenes/schema.json plus the invariants JSON
 * Schema cannot express: no gaps, no overlaps, first scene starts at 0,
 * duration === end - start, and a card scene must name its card image.
 * Fails loudly at bundle time instead of producing a silently broken video.
 */
export const parseScenes = (input: unknown): Scene[] => {
  if (!isRecord(input) || !Array.isArray(input.scenes)) {
    return fail('expected an object with a "scenes" array');
  }

  const seenIds = new Set<number>();
  let expectedStart = 0;

  const scenes = input.scenes.map((raw, index) => {
    const at = `scenes[${index}]`;
    if (!isRecord(raw)) {
      return fail(`${at} is not an object`);
    }

    const {id, start, end, duration, footage_query, source_preference} = raw;
    const {animation_type, text_overlay, card_image, sfx_cue, transition_in} = raw;

    if (typeof id !== 'number' || !Number.isInteger(id) || id < 1) {
      return fail(`${at}.id must be a positive integer`);
    }
    if (seenIds.has(id)) {
      return fail(`${at}.id ${id} is used more than once`);
    }
    seenIds.add(id);

    if (typeof start !== 'number' || start < 0) {
      return fail(`${at}.start must be a number >= 0`);
    }
    if (typeof end !== 'number' || end <= start) {
      return fail(`${at}.end must be a number > start`);
    }
    if (typeof duration !== 'number' || duration <= 0) {
      return fail(`${at}.duration must be a number > 0`);
    }

    if (Math.abs(duration - (end - start)) > EPSILON) {
      return fail(
        `${at}.duration (${duration}) does not equal end - start (${end - start})`,
      );
    }
    if (Math.abs(start - expectedStart) > EPSILON) {
      return fail(
        `${at}.start is ${start} but the previous scene ends at ${expectedStart} ` +
          `(scenes must be contiguous, so expect no gap and no overlap)`,
      );
    }
    expectedStart = end;

    if (typeof footage_query !== 'string' || footage_query.trim() === '') {
      return fail(`${at}.footage_query must be a non-empty string`);
    }
    if (
      typeof source_preference !== 'string' ||
      !SOURCES.includes(source_preference)
    ) {
      return fail(`${at}.source_preference must be one of ${SOURCES.join(', ')}`);
    }
    if (
      typeof animation_type !== 'string' ||
      !ANIMATIONS.includes(animation_type)
    ) {
      return fail(`${at}.animation_type must be one of ${ANIMATIONS.join(', ')}`);
    }
    if (text_overlay !== null && text_overlay !== undefined && typeof text_overlay !== 'string') {
      return fail(`${at}.text_overlay must be a string or null`);
    }
    if (card_image !== null && card_image !== undefined && typeof card_image !== 'string') {
      return fail(`${at}.card_image must be a string or null`);
    }
    if (sfx_cue !== null && sfx_cue !== undefined && typeof sfx_cue !== 'string') {
      return fail(`${at}.sfx_cue must be a string or null`);
    }

    const transition = transition_in ?? 'cut';
    if (typeof transition !== 'string' || !TRANSITIONS.includes(transition)) {
      return fail(
        `${at}.transition_in must be "cut" — the reference films use hard cuts only`,
      );
    }

    const type = animation_type as AnimationType;
    if (type === 'still_card' && !card_image) {
      return fail(`${at} is a still_card but has no card_image`);
    }
    if (type === 'date_label' && !text_overlay) {
      return fail(`${at} is a date_label but has no text_overlay (the date)`);
    }

    return {
      id,
      start,
      end,
      duration,
      footage_query,
      source_preference: source_preference as SourcePreference,
      animation_type: type,
      text_overlay: text_overlay ?? null,
      card_image: card_image ?? null,
      sfx_cue: sfx_cue ?? null,
      transition_in: 'cut' as const,
    };
  });

  if (scenes.length === 0) {
    return fail('at least one scene is required');
  }

  // Pacing drift is reported, not fatal: a card may legitimately run long.
  for (const scene of scenes) {
    const [lo, hi] = DURATION_POLICY[scene.animation_type];
    if (scene.duration < lo || scene.duration > hi) {
      console.warn(
        `[scenes] scene ${scene.id} (${scene.animation_type}) is ${scene.duration}s, ` +
          `outside the measured ${lo}-${hi}s window.`,
      );
    }
  }

  return scenes;
};

/** The validated timeline, shared by every composition that renders it. */
export const SAMPLE_SCENES: Scene[] = parseScenes(sampleJson);

/** Total runtime in frames, derived from the timeline (never hard-coded). */
export const SAMPLE_SCENES_DURATION_IN_FRAMES = Math.round(
  SAMPLE_SCENES[SAMPLE_SCENES.length - 1].end * VIDEO_FPS,
);
