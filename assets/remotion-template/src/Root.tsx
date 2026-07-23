import {Composition} from 'remotion';
import {HanddrawnStory, storyboard, totalFrames} from './Story';

export const RemotionRoot: React.FC = () => (
  <Composition
    id="HanddrawnStory"
    component={HanddrawnStory}
    durationInFrames={totalFrames}
    fps={storyboard.fps}
    width={storyboard.width}
    height={storyboard.height}
    defaultProps={{}}
  />
);
