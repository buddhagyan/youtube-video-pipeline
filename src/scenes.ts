import sampleJson from '../scenes/sample.json';
import {VIDEO_FPS} from './video';

export type SourcePreference = 'nasa' | 'wikimedia' | 'archive';

export type AnimationType =
  | 'ken_burns_zoom'
  | 'text_overlay'
  | 'timeline_bar';

export type Scene = {
  id: number;
  start: number;
  end: number;
  duration: number;
  footage_query: string;
  source_preference: SourcePreference;
  animation_type: AnimationType;
  text_overlay: string | null;
  sfx_cue: string | null;
};

const SOURCES: readonly string[] = ['nasa', 'wikimedia', 'archive'];
const ANIMATIONS: readonly string[] = [
  'ken_burns_zoom',
  'text_overlay',
  'timeline_bar',
];

const EPSILON = 1e-6;

const fail = (message: string): never => {
  throw new Error(`scenes/sample.json is invalid: ${message}`);
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

/**
 * Validates the timeline against scenes/schema.json plus the invariants JSON
 * Schema cannot express: no gaps, no overlaps, first scene starts at 0, and
 * duration === end - start. Fails loudly at bundle time instead of producing a
 * silently broken video.
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
    const {animation_type, text_overlay, sfx_cue} = raw;

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
    if (text_overlay !== null && typeof text_overlay !== 'string') {
      return fail(`${at}.text_overlay must be a string or null`);
    }
    if (sfx_cue !== null && typeof sfx_cue !== 'string') {
      return fail(`${at}.sfx_cue must be a string or null`);
    }

    return {
      id,
      start,
      end,
      duration,
      footage_query,
      source_preference: source_preference as SourcePreference,
      animation_type: animation_type as AnimationType,
      text_overlay,
      sfx_cue,
    };
  });

  if (scenes.length === 0) {
    return fail('at least one scene is required');
  }

  return scenes;
};

/** The validated timeline, shared by every composition that renders it. */
export const SAMPLE_SCENES: Scene[] = parseScenes(sampleJson);

/** Total runtime in frames, derived from the timeline (never hard-coded). */
export const SAMPLE_SCENES_DURATION_IN_FRAMES = Math.round(
  SAMPLE_SCENES[SAMPLE_SCENES.length - 1].end * VIDEO_FPS,
);
