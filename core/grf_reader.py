import datetime
import os
import subprocess

import ffmpeg
from PIL import Image
from moviepy.editor import VideoFileClip

from utils.path import add_to_system_path, get_abs_path
from utils.platform import get_sys_platform
from utils.timestamp import get_time

FFMPEG_FILE = '../executable/' + get_sys_platform() + '/ffmpeg'
FFMPEG_FILE = get_abs_path(__file__, FFMPEG_FILE)
FFPROBE_FILE = '../executable/' + get_sys_platform() + '/ffprobe'
FFPROBE_FILE = get_abs_path(__file__, FFPROBE_FILE)
add_to_system_path(FFMPEG_FILE)

FFMPEG_LOGLEVEL = 'warning'


def create_image(width, height, color=(0, 0, 0)):
    img = Image.new('RGB', (int(width), int(height)), color)
    return img


def format_time_s(t):
    return datetime.timedelta(seconds=float(t)).__str__()


class GrfReader(object):
    def __init__(self):
        self._movie = None

    def read(self, filename):
        assert os.path.exists(filename)

        self._movie = VideoFileClip(filename)
        return self._movie


class FfmpegQuerier(object):
    def __init__(self):
        self._info = {}

    @property
    def info(self):
        return self.info

    def __call__(self, input):
        if not input:
            return

        self._info = ffmpeg.probe(input, cmd=FFPROBE_FILE)

        return self

    @property
    def only_audio(self):
        codec_types = list(map(lambda x: x['codec_type'], self._info['streams']))

        if 'audio' in codec_types and 'video' not in codec_types:
            return True
        return False

    @property
    def duration(self):
        return self._info['format']['duration']

    @property
    def width(self):
        vs = list(filter(lambda x: x['codec_type'] == 'video', self._info['streams']))
        if vs:
            return vs[0]['width']

    @property
    def height(self):
        vs = list(filter(lambda x: x['codec_type'] == 'video', self._info['streams']))
        if vs:
            return vs[0]['height']

    @property
    def size(self):
        vs = list(filter(lambda x: x['codec_type'] == 'video', self._info['streams']))
        if vs:
            return int(vs[0]['width']), int(vs[0]['height'])


class GrfTransformer(object):
    def __init__(self, loglevel=FFMPEG_LOGLEVEL):
        self._log_level = loglevel
        self._gq = FfmpegQuerier()
        self._tmp_img_file = 'bg.png'
        self._default_bg_color = (0, 0, 0)

    def _create_bg(self, width, height):
        if not os.path.exists(self._tmp_img_file):
            img = create_image(width, height, self._default_bg_color)
            img.save(self._tmp_img_file)

    def __call__(self, input, output=None, width='320', height='240', starttimestamp='', stoptimestamp=''):
        if not output:
            output = input[:input.rindex('.')] + '.mp4'

        only_audio = self._gq(input).only_audio

        if only_audio:
            self._create_bg(width, height)
            # TODO: ffmpegic
            self._merge_image_and_audio(self._tmp_img_file, input, output,
                                        starttimestamp=starttimestamp, stoptimestamp=stoptimestamp)
        else:
            stream = ffmpeg.input(input)
            # fix frame r(rate) 10

            # fixed 'Too many packets buffered for output stream 0:0.'
            # -max_muxing_queue_size 9999
            # refer: https://stackoverflow.com/questions/49686244/ffmpeg-too-many-packets-buffered-for-output-stream-01

            # force size width x height
            stream = ffmpeg.output(stream, output, loglevel=self._log_level,
                                   **{'r': '10', 's': '%sx%s' % (width, height),
                                      'max_muxing_queue_size': '9999'})
            out, err = ffmpeg.run(stream, cmd=FFMPEG_FILE, overwrite_output=True)
            return out

    def _merge_image_and_audio(self, image_file, audio_file, output, **kwargs):

        parameters = [FFMPEG_FILE, '-loop', '1', '-i', image_file, '-i', audio_file,
                      '-c:v', 'libx264', '-tune', 'stillimage', '-shortest', '-r', '10',
                      '-max_muxing_queue_size', '9999', '-pix_fmt', 'yuv420p', '-strict', '-2',
                      '-loglevel', self._log_level, '-y', output]
        if 'starttimestamp' in kwargs and kwargs['starttimestamp']:
            starttimestamp = format_time_s(kwargs['starttimestamp'])

            parameters.insert(-1, '-ss')
            parameters.insert(-1, starttimestamp)

        if 'stoptimestamp' in kwargs and kwargs['stoptimestamp']:
            stoptimestamp = format_time_s(kwargs['stoptimestamp'])
            parameters.insert(-1, '-to')
            parameters.insert(-1, stoptimestamp)

        subprocess.call(parameters)


class MP4Merger(object):
    def __init__(self, loglevel=FFMPEG_LOGLEVEL):
        self._log_level = loglevel
        # generate temp filename
        self.tmp_file = '%s.tmp' % get_time()
        self.reserve_tmp_file = True

    def merge(self, ordered_filenames, folder, output):
        # get abs filenames
        ordered_filenames = list(map(lambda x: os.path.abspath(os.path.join(folder, x)), ordered_filenames))
        # write ordered filenames to tmp_file
        self._write_tmp_file(ordered_filenames)
        # remove output if existing
        if os.path.exists(output):
            os.remove(output)
        # subprocess
        self._call(output)
        # remove tmp file
        if not self.reserve_tmp_file:
            os.remove(self.tmp_file)

    def _write_tmp_file(self, filenames):
        with open(self.tmp_file, 'w') as f:
            f.write('\n'.join(list(map(lambda x: "file '{}'".format(x), filenames))))

    def _call(self, output):
        # this method will change fps, discard
        # subprocess.call([FFMPEG_FILE, '-f', 'concat', '-safe', '0', '-i', self.tmp_file, '-c', 'copy',
        #                  '-r', '10', '-strict', '-2', '-loglevel', self._log_level, '-y', output])

        # force fps = 10
        parameters = [FFMPEG_FILE, '-f', 'concat', '-safe', '0', '-i', self.tmp_file, '-c:v', 'libx264',
                      '-framerate', '10', '-vf', 'fps=10', '-strict', '-2', '-pix_fmt', 'yuv420p',
                      '-loglevel', self._log_level, '-y', output]
        subprocess.call(parameters)

    def merge_using_record_xml_of_grf(self, record_xml, folder, output):
        from core.xml_reader import RecordXml
        rx = RecordXml()
        rx.read(record_xml)
        rx.parse()
        grfs = rx.grfs
        # change *.grf to *.mp4
        mp4s = list(map(lambda x: x.get('multimedia').replace('grf', 'mp4'), grfs))
        # call merge
        self.merge(mp4s, folder, output)

    def merge_using_record_xml_of_swf(self, record_xml, folder, output):
        from core.xml_reader import RecordXml
        rx = RecordXml()
        rx.read(record_xml)
        rx.parse()
        swfs = rx.swfs
        # change *.grf to *.mp4
        # use unique filename
        mp4s = list(map(lambda x: x.get('ufilename').replace('swf', 'mp4'), swfs))
        # call merge
        self.merge(mp4s, folder, output)
