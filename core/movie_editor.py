import os
import re
import textwrap
import subprocess

import click
from PIL import Image, ImageDraw
from moviepy.video.io.ffmpeg_reader import FFMPEG_VideoReader
from moviepy.video.io.ffmpeg_writer import FFMPEG_VideoWriter

from core.chat_editor import default_font
from core.grf_reader import FfmpegQuerier
from core.grf_reader import FFMPEG_FILE
from core.grf_reader import FFMPEG_LOGLEVEL
from core.xml_reader import AnnoCommand
from core.xml_reader import AnnoXml
from utils.timestamp import timestamp2frame
from utils.timestamp import get_time


class MovieEditor(object):
    def __init__(self, input, output, width=None, height=None, log_level=FFMPEG_LOGLEVEL):
        self._reader = FFMPEG_VideoReader(input)
        self._fps = self._reader.fps
        # self.cur_frame = 1
        # self._frame = None
        self._querier = FfmpegQuerier()
        self._info = self._querier(input)
        self._duration = self._querier.duration
        self.draw_dict = {}
        self._resize = (int(width), int(height)) if (width and height) else None
        self._loglevel = log_level
        self._output = output
        self._tmp_file = self._make_tmp_file(input) if self._resize else None
        self._writer = FFMPEG_VideoWriter(
            self._tmp_file if self.need_resize else output,
            size=self._reader.size,
            fps=self._reader.fps)

    @property
    def need_resize(self):
        return self._resize and list(self._resize) != list(self._reader.size)

    # for resizing
    def _make_tmp_file(self, input):
        return '%s-%s.mp4' % (input, get_time())

    def _remove_tmp_file(self):
        if os.path.exists(self._tmp_file):
            os.remove(self._tmp_file)

    # approximate frame count
    def get_total_frame(self):
        return timestamp2frame(self._duration, self._fps)

    # def seek_frame(self, index):
    #     self._reader.skip_frames(index - self.cur_frame)
    #     self._frame = self._reader.read_frame()
    #
    # def seek_timestamp(self, timestamp):
    #     index = FrameEditor.which_frame(timestamp, self._fps)
    #     self.seek_frame(index)
    #
    # def draw_anno(self, anno):
    #     if self._frame is not None:
    #         self._frame_editor.frame = self._frame
    #         self._frame_editor.draw_anno(anno)

    def draw_anno_file(self, anno_filename):
        # parse anno file
        ax = AnnoXml()
        ax.read(anno_filename)
        ax.parse()
        commands = ax.command

        fps = self._fps
        frame = self._reader.read_frame()
        self._writer.write_frame(frame)
        # total frame
        total_frame = self.get_total_frame()
        with click.progressbar(length=total_frame, label='Processing...') as bar:
            # current
            frame_index = 1
            bar.update(1)
            for command in commands:
                pageid = command.pageid
                command_frame = CommandParser.get_frame_index(command, fps)
                if pageid in self.draw_dict:
                    frame_editor = self.draw_dict[pageid]
                else:
                    frame_editor = FrameEditor(fps=fps, pageid=pageid)
                    self.draw_dict[pageid] = frame_editor
                # before
                while frame_index < command_frame:
                    if not frame_editor.commands:
                        frame = self.read_frame()
                        self.write_frame(frame)
                    else:
                        frame = self.read_frame()
                        frame_editor.draw(frame)
                        self.write_frame(frame_editor.image)
                    frame_index += 1
                    bar.update(1)
                # append
                frame_editor.append_command(command)
                # current
                frame = self.read_frame()
                frame_editor.draw(frame)
                self.write_frame(frame_editor.image)
                frame_index += 1
                bar.update(1)
            # write left frames
            while frame_index < total_frame:
                self.write_frame(self.read_frame())
                frame_index += 1
                bar.update(1)
        # close stream
        self.close()
        # resize if needed
        if self.need_resize:
            self.resize()
            self._remove_tmp_file()

    def read_frame(self):
        return self._reader.read_frame()

    def write_frame(self, frame):
        # if self._resize:
        #     if not isinstance(frame, Image.Image):
        #         frame = Image.fromarray(frame.astype('uint8'))
        # Here's a bug.
        #     frame = frame.resize(self._resize, Image.ANTIALIAS)
        self._writer.write_frame(frame)

    def resize(self):
        parameters = [FFMPEG_FILE, '-i', self._tmp_file,
                      '-s', '{w}*{h}'.format(w=self._resize[0], h=self._resize[1]),
                      '-loglevel', self._loglevel, '-y', self._output]

        subprocess.call(parameters)

    def close(self):
        self._reader.close()
        self._writer.close()


class CommandParser(object):
    def __init__(self):
        self._point_pair_pattern = re.compile('\((\d+\.?\d+?),(\d+\.?\d+?)\)')

    def not_remove(self, commmand: AnnoCommand):
        return commmand.removed == ''

    # parse
    def __call__(self, command: AnnoCommand):
        _id = command.id
        if self.not_remove(command):
            c = command.color.split(',')[0]
            w = command.linesize
            p = self._parse_points(command.p)
            t = command.timestamp
            return DrawObject(_id, c, w, p, t, command.type, command.tail)
        else:
            r = command.removed
            return RemoveObject(_id, r)

    def _parse_points(self, p):
        li = self._point_pair_pattern.findall(p)
        return list(map(lambda x: (int(float(x[0])), int(float(x[1]))), li))

    @staticmethod
    def get_frame_index(command: AnnoCommand, fps):
        return timestamp2frame(command.timestamp, fps)


command_parser = CommandParser()


class DrawObject(object):
    def __init__(self, _id, color, width, points, timestamp, type, tail):
        self._id = _id
        self._color = color
        self._width = width
        self._points = points
        self._timestamp = timestamp
        self._type = type
        self._tail = tail

    @property
    def id(self):
        return self._id

    @property
    def color(self):
        return self._color

    @property
    def width(self):
        return self._width

    @property
    def points(self):
        return self._points

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def type(self):
        return self._type

    @property
    def tail(self):
        return self._tail

    def __eq__(self, other):
        return self.id == other.id


class RemoveObject(DrawObject):
    def __init__(self, _id, remove_id):
        self._id = _id
        self._remve_id = remove_id

    @property
    def remove_id(self):
        return self._remve_id


class DrawType(object):
    free_line = '2'
    remove = '3'
    text = '4'
    rectangle = '6'
    line = '8'
    unknown = '9'


class FrameEditor(object):
    def __init__(self, fps=None, cp=command_parser, pageid='', font=default_font):
        self._frame = None
        self._fps = fps
        self._image = None
        self._draw = None
        self._commands = []
        # command parser
        self._cp = cp
        self._pageid = pageid
        # supported types
        self._supported_types = [
            DrawType.free_line,  # free line(multi-points)
            DrawType.remove,  # remove
            DrawType.text,  # text
            DrawType.rectangle,  # rectangle
            DrawType.line,  # line(two-points)
        ]
        self._font = font

    @property
    def pageid(self):
        return self.pageid

    @property
    def commands(self):
        return self._commands

    @property
    def frame(self):
        return self._frame

    @frame.setter
    def frame(self, f):
        self._frame = f
        self._image = Image.fromarray(f.astype('uint8'))
        self._draw = ImageDraw.Draw(self._image)

    def _draw_line(self, p1, p2, width, color):
        self._draw.line([p1, p2], fill=color, width=width)

    def _draw_rectangle(self, p1, p2, width, color):
        self._draw.rectangle([p1, p2], width=int(width), outline=color)

    def _draw_text(self, p1, p2, text, color):
        width = (p2[0] - p1[0]) // self._font.size
        lines = textwrap.wrap(text, width=width)
        x = p1[0]
        y_text = p1[1]
        for line in lines:
            width, height = self._font.getsize(line)
            self._draw.text((x, y_text), line, font=self._font, fill=color or (0, 0, 0))
            y_text += height

    def _draw_points(self, points, width, color):
        point_count = len(points)
        for i in range(point_count - 1):
            p1, p2 = points[i], points[i + 1]
            # for i, p1 in enumerate(points):
            #     p2 = points[(i + 1) % point_count]
            self._draw_line(p1, p2, int(width), color)

    def get_all_command_ids(self):
        if not self.commands:
            return
        return list(map(lambda x: x.id, self.commands))

    def append_command(self, command: AnnoCommand):
        # type '2' --> free line
        # type '3' --> remove
        # type '4' --> text
        # type '6' --> rectangle
        # type '8' --> line
        # type '9' --> unknown

        if command.type not in self._supported_types:
            return

        c = self._cp(command)
        if isinstance(c, RemoveObject):
            _id = c.remove_id
            self._commands = list(filter(lambda x: x.id != _id, self.commands))
        else:
            self._commands.append(c)

    def draw_command(self, obj: DrawObject, frame):
        self.frame = frame
        ps = obj.points
        color = obj.color
        width = obj.width
        self._draw_points(ps, width, color)

    def draw(self, frame):
        self.frame = frame
        for obj in self.commands:
            ps = obj.points
            color = obj.color
            width = obj.width
            type = obj.type
            tail = obj.tail
            if type == DrawType.text:
                self._draw_text(ps[0], ps[1], tail, color)
            elif type == DrawType.rectangle:
                self._draw_rectangle(ps[0], ps[1], width, color)
            else:
                self._draw_points(ps, width, color)

    @staticmethod
    def which_frame(timestamp, fps):
        return timestamp2frame(timestamp, fps)

    @property
    def image(self):
        return self._image
