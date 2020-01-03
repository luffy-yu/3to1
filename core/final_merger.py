import click
import numpy as np
from moviepy.video.io.ffmpeg_reader import FFMPEG_VideoReader
from moviepy.video.io.ffmpeg_writer import FFMPEG_VideoWriter

from core.grf_reader import FfmpegQuerier


class FinalMerger(object):
    """
    merge 3 mp4 files to one mp4 file,
    in other words, 3to1.

    layout:
     ---------------
    |        |      |
    |        | grf  |
    |  swf    ------
    |        |      |
    |        | chat |
     ---------------
    """

    def __init__(self, swf_mp4, grf_mp4, chat_mp4, output, fps=10):
        self._swf_mp4 = swf_mp4
        self._grf_mp4 = grf_mp4
        self._chat_mp4 = chat_mp4
        self._fq = FfmpegQuerier()
        self._swf_reader = FFMPEG_VideoReader(swf_mp4)
        self._grf_reader = FFMPEG_VideoReader(grf_mp4)
        self._chat_reader = FFMPEG_VideoReader(chat_mp4)
        self._output = output
        self._fps = fps
        self._output_size = self.cal_output_size()
        self._writer = FFMPEG_VideoWriter(output, self._output_size, fps, audiofile=grf_mp4)

    def get_duration(self, filename) -> float:
        self._fq(filename)
        return float(self._fq.duration)

    def get_size(self, filename) -> (int, int):
        self._fq(filename)
        return self._fq.size

    def cal_output_size(self):
        swf_size = self.get_size(self._swf_mp4)
        grf_size = self.get_size(self._grf_mp4)
        return swf_size[0] + grf_size[0], swf_size[1]

    def _merge_frame(self, swf_frame, grf_frame, chat_frame):
        sf = swf_frame.astype('uint8')
        gf = grf_frame.astype('uint8')
        cf = chat_frame.astype('uint8')
        return np.column_stack([sf, np.row_stack([gf, cf])])

    def merge(self):
        # get durations
        durations = list(map(lambda x: self.get_duration(x),
                             [self._swf_mp4, self._grf_mp4, self._chat_mp4]
                             ))
        max_duration = max(durations)
        # max frames
        max_frames = int(max_duration * self._fps)

        with click.progressbar(length=max_frames, label='Processing...') as bar:
            index = 0
            while index < max_frames:
                sf = self.read_swf_frame()
                gf = self.read_grf_frame()
                cf = self.read_chat_frame()
                frame = self._merge_frame(sf, gf, cf)
                self.write_frame(frame)
                index += 1
                bar.update(1)

    def read_swf_frame(self):
        return self._swf_reader.read_frame()

    def read_grf_frame(self):
        return self._grf_reader.read_frame()

    def read_chat_frame(self):
        return self._chat_reader.read_frame()

    def write_frame(self, frame):
        self._writer.write_frame(frame)

    def close(self):
        for one in (self._swf_reader, self._grf_reader, self._chat_reader, self._writer):
            one.close()
