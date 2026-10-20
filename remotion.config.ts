import {Config} from '@remotion/cli/config';
import {VIDEO_FPS, VIDEO_HEIGHT, VIDEO_WIDTH} from './src/video';

/** Where the project root component lives. */
Config.setEntryPoint('./src/index.ts');

/**
 * Canvas + frame rate for everything this project renders.
 * Exported so scripts and compositions can read the same values the
 * CLI uses instead of hard-coding them in two places.
 */
export const RENDER_DEFAULTS = {
  width: VIDEO_WIDTH,
  height: VIDEO_HEIGHT,
  fps: VIDEO_FPS,
} as const;

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
