import {staticFile} from 'remotion';
import type {TimelineBarLabel} from './components/TimelineBar';

export type SceneAsset = {
  /** Resolved local image for the scene's `footage_query`. */
  src: string;
  /** Where the Ken Burns push is anchored, 0-1 across the image. */
  focalPoint: {x: number; y: number};
  zoomTo: number;
  /** Optional year markers for `timeline_bar` scenes. */
  timelineLabels?: TimelineBarLabel[];
};

/**
 * Resolved picture per scene id for the footage scenes. Date cards, news cards
 * and end cards carry their image (or lack of one) in scenes/sample.json itself
 * (`card_image`), so they are not listed here.
 *
 * This is the bridge between the timeline (which stores a search intent) and the
 * actual file; once footage fetching is automated, this map is what gets written.
 */
export const SCENE_ASSETS: Record<number, SceneAsset> = {
  2: {
    src: staticFile('assets/voyager-golden-record-gold-plating.jpg'),
    focalPoint: {x: 0.45, y: 0.5},
    zoomTo: 1.1,
  },
};
