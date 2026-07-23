import type {CSSProperties} from 'react';
import {useCurrentFrame} from 'remotion';
import {revealProgress} from './easing';

type TextWipeProps = {
  text: string;
  startFrame: number;
  durationFrames: number;
};

const fallbackFontSize = (text: string) => {
  const lines = text.split('\n').filter(Boolean);
  const lineCount = Math.max(1, lines.length);
  const longestLine = Math.max(...lines.map((line) => line.length), 1);
  const widthLimited = Math.floor(850 / (longestLine * 1.08));
  const heightLimited = Math.floor(306 / (lineCount * 1.28));
  return Math.max(48, Math.min(82, widthLimited, heightLimited));
};

const textStyle = (fontSize: number): CSSProperties => ({
  fontFamily: '"Ma Shan Zheng", "STKaiti", "KaiTi", cursive',
  fontSize,
  fontWeight: 400,
  lineHeight: 1.34,
  letterSpacing: '0.025em',
  color: '#171714',
  WebkitTextStroke: '0.7px #171714',
  margin: 0,
  maxWidth: 852,
  textAlign: 'left',
  whiteSpace: 'pre-line',
  transform: 'rotate(-0.35deg)',
});

export const TextWipe: React.FC<TextWipeProps> = ({
  text,
  startFrame,
  durationFrames,
}) => {
  const frame = useCurrentFrame();
  const progress = revealProgress(frame, startFrame, durationFrames);
  return (
    <div
      style={{
        position: 'absolute',
        zIndex: 40,
        top: 92,
        left: 104,
        right: 96,
        display: 'flex',
        justifyContent: 'flex-start',
        clipPath: `inset(0 ${100 - progress * 100}% 0 0)`,
      }}
    >
      <p style={textStyle(fallbackFontSize(text))}>{text}</p>
    </div>
  );
};
