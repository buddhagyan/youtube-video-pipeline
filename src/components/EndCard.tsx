import type {FC} from 'react';
import {AbsoluteFill} from 'remotion';

export type EndCardProps = {
  /** Channel / series name. */
  title: string;
  /** Line under the title, usually the call to action. */
  subtitle?: string;
  /** Small print at the bottom, e.g. "new film every Sunday". */
  footnote?: string;
};

/**
 * The last 10-20 seconds of a Mighty Monk film: a still channel card with the
 * logo line and a subscribe prompt. No motion at all — the outgoing scene cuts
 * to it and the film simply ends.
 */
export const EndCard: FC<EndCardProps> = ({title, subtitle, footnote}) => {
  return (
    <AbsoluteFill
      style={{
        background:
          'radial-gradient(110% 90% at 50% 45%, #1a1712 0%, #0a0a0b 60%, #050505 100%)',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'Inter, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
        textAlign: 'center',
      }}
    >
      <div
        style={{
          width: 96,
          height: 3,
          background: '#e8b04b',
          marginBottom: 46,
        }}
      />
      <div
        style={{
          fontSize: 96,
          fontWeight: 800,
          letterSpacing: '0.02em',
          color: '#f7f5ef',
          textTransform: 'uppercase',
        }}
      >
        {title}
      </div>
      {subtitle ? (
        <div
          style={{
            marginTop: 30,
            fontSize: 34,
            letterSpacing: '0.24em',
            textTransform: 'uppercase',
            color: 'rgba(247,245,239,0.66)',
          }}
        >
          {subtitle}
        </div>
      ) : null}
      {footnote ? (
        <div
          style={{
            marginTop: 90,
            fontSize: 24,
            letterSpacing: '0.16em',
            textTransform: 'uppercase',
            color: 'rgba(247,245,239,0.35)',
          }}
        >
          {footnote}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
