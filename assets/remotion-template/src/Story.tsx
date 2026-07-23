import {Video} from '@remotion/media';
import {AbsoluteFill, Series, staticFile} from 'remotion';
import rawStoryboard from '../storyboard.json';
import {TextWipe} from './TextWipe';

export type SceneData = {
  id: string;
  caption: string;
  duration_frames: number;
  video: string;
};

export type Storyboard = {
  title: string;
  fps: number;
  width: number;
  height: number;
  scenes: SceneData[];
};

export const storyboard = rawStoryboard as Storyboard;
export const totalFrames = storyboard.scenes.reduce(
  (sum, scene) => sum + scene.duration_frames,
  0,
);

const Scene: React.FC<{scene: SceneData}> = ({scene}) => (
  <AbsoluteFill style={{backgroundColor: '#F6F1E3', overflow: 'hidden'}}>
    <div
      style={{
        position: 'absolute',
        top: 360,
        left: 0,
        width: 1080,
        height: 1080,
        overflow: 'hidden',
      }}
    >
      <Video
        src={staticFile(scene.video)}
        muted
        objectFit="contain"
        style={{
          display: 'block',
          width: '100%',
          height: '100%',
        }}
      />
    </div>
    <TextWipe
      text={scene.caption}
      startFrame={0}
      durationFrames={Math.max(1, Math.round(scene.duration_frames * 0.22))}
    />
  </AbsoluteFill>
);

export const HanddrawnStory: React.FC = () => (
  <Series>
    {storyboard.scenes.map((scene) => (
      <Series.Sequence
        key={scene.id}
        durationInFrames={scene.duration_frames}
        name={`Scene ${scene.id}`}
      >
        <Scene scene={scene} />
      </Series.Sequence>
    ))}
  </Series>
);
