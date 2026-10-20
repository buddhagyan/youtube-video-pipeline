/**
 * Single source of truth for the canvas size and frame rate.
 * Imported by both the compositions (src/Root.tsx) and the CLI config
 * (remotion.config.ts), so `npx remotion studio` and `npx remotion render`
 * always agree.
 */
export const VIDEO_WIDTH = 1920;
export const VIDEO_HEIGHT = 1080;
export const VIDEO_FPS = 30;

/** 5 seconds at 30 fps. */
export const VIDEO_DURATION_IN_FRAMES = 5 * VIDEO_FPS;
