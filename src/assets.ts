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
 * Resolved footage per scene id. This is the bridge between the timeline
 * (`scenes/sample.json`, which stores a search intent) and the actual file.
 * Once footage fetching is automated this map is what gets generated.
 */
export const SCENE_ASSETS: Record<number, SceneAsset> = {
  1: {
    src: staticFile('assets/voyager-1-launch-1977.jpg'),
    focalPoint: {x: 0.5, y: 0.42},
    zoomTo: 1.12,
  },
  2: {
    src: staticFile('assets/voyager-golden-record-gold-plating.jpg'),
    focalPoint: {x: 0.45, y: 0.5},
    zoomTo: 1.12,
  },
  3: {
    src: staticFile('assets/pale-blue-dot-1990.jpg'),
    focalPoint: {x: 0.5, y: 0.5},
    zoomTo: 1.1,
    timelineLabels: [
      {at: 0, label: '1977'},
      {at: 3.5, label: '1990'},
      {at: 7, label: '2012'},
    ],
  },
};
