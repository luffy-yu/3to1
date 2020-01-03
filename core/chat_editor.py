import random
import re
import textwrap

import click
from PIL import Image, ImageDraw, ImageFont
from moviepy.video.io.ffmpeg_writer import FFMPEG_VideoWriter

from core.xml_reader import ChatXml, Chat
from utils.path import get_abs_path
from utils.timestamp import timestamp2frame

font_file = get_abs_path(__file__, 'simsun.ttc')

default_font = ImageFont.truetype(font=font_file, size=16, encoding="unic")

p1 = re.compile('(&nbsp;)|(\\n[ ]+)|(<img[^>]+/>)')
p2 = re.compile('(<SPAN[^>]+>)(.+)(</SPAN>)')


def clean_text(content):
    content = p1.sub(' ', content)
    content = p2.sub('\g<2>', content)
    return content


class ChatQueue(object):
    def __init__(self, maxsize):
        self._maxsize = maxsize
        self._queue = []

    def push(self, chat: Chat):
        if len(self._queue) == self._maxsize:
            self._pop()
        self._queue.append(chat)

    def _pop(self):
        if self._queue:
            self._queue.pop(0)

    def pop(self):
        return self._pop()

    def get_all(self):
        return self._queue


class ChatEditor(object):
    def __init__(self, width, height, filename, fps, maxsize, **kwargs):
        self._width = width
        self._height = height
        self._filename = filename
        self._fps = fps
        self._writer = FFMPEG_VideoWriter(filename, (width, height), fps)
        self._total_frame = 0  # init after loading chat xml
        self._chat_queue = ChatQueue(maxsize)
        self._draw = None
        self._image = None
        self._x_offset = kwargs.get('x_offset') or 0
        self._y_offset = kwargs.get('y_offset') or 0
        self._font = kwargs.get('font') or default_font
        self._bg_color = kwargs.get('bg_color') or (244, 244, 244)
        self._color_map = {}
        # max characters in one line
        self._max_characters = (self._width - self._x_offset) // self._font.size

    def init_color_map(self, chats):
        self._color_map = self.make_color_map(chats)

    def init_total_frame(self, duration):
        self._total_frame = int(float(duration) * self._fps)

    def get_color(self, senderid):
        # default white color
        return self._color_map.get(senderid, (10, 10, 10))

    def get_color_by_chat(self, chat: Chat):
        return self.get_color(chat.senderId)

    def chat_to_show(self):
        return self._chat_queue.get_all()

    def draw_chat(self, chat, x, y) -> int:
        self._image = Image.new('RGB', (self._width, self._height), color=self._bg_color)
        self._draw = ImageDraw.Draw(self._image)
        content = self._format_chat(chat)
        color = self.get_color_by_chat(chat)
        y_pos = self._draw_text(self._draw, content, x, y, color=color)
        self.write_frame(self._image)
        return y_pos

    def draw_chats(self, chats):
        # draw all chats in chat queue
        self._image = Image.new('RGB', (self._width, self._height), color=self._bg_color)
        self._draw = ImageDraw.Draw(self._image)
        x_pos, y_pos = 0, 0
        for chat in chats:
            content = self._format_chat(chat)
            color = self.get_color_by_chat(chat)
            y_pos = self._draw_text(self._draw, content, x_pos, y_pos, color=color)
        self.write_frame(self._image)

    def foresee_chats(self, chats):
        if not chats:
            return
        # ensure full content of chats to be shown in the video,
        # if not, remove the former chats
        x_pos, y_pos = 0, 0
        remove_count = len(chats)
        for chat in chats[::-1]:
            content = self._format_chat(chat)
            y_pos = self._draw_text(self._draw, content, x_pos, y_pos, to_draw=False)
            # y_pos > height, to remove chat
            if y_pos > self._height:
                break
            remove_count -= 1
        # remove
        while remove_count > 0:
            self._chat_queue.pop()
            remove_count -= 1

    def write_frame(self, frame):
        self._writer.write_frame(frame)

    def close(self):
        self._writer.close()

    def _draw_text(self, draw, text, x, y, color=None, to_draw=True):
        # refer: https://stackoverflow.com/questions/7698231/python-pil-draw-multiline-text-on-image
        lines = textwrap.wrap(text, width=self._max_characters)
        y_text = y + self._y_offset
        for line in lines:
            width, height = self._font.getsize(line)
            to_draw and draw.text((x + self._x_offset, y_text), line, font=self._font, fill=color or (0, 0, 0))
            y_text += height + self._y_offset
        return y_text

    def _format_chat(self, chat: Chat):
        name = chat.sender
        content = self.format_chat_content(chat.content)
        s = '[%s] %s' % (name, content)

        return s

    @staticmethod
    def format_chat_content(content):
        return clean_text(content)

    @staticmethod
    def make_color_map(chats):
        all_sender_id = list(set(list(map(lambda x: x.senderId, chats))))
        color_map = {
            _id: (
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255)
            )
            for _id in all_sender_id
        }
        return color_map

    def draw(self, chat_filename):
        cx = ChatXml()
        cx.read(chat_filename)
        cx.parse()

        chats = cx.chat

        # init total frame
        self.init_total_frame(cx.duration)

        # init color map
        self.init_color_map(chats)

        with click.progressbar(length=self._total_frame, label='Processing...') as bar:
            frame = 0
            for chat in chats:
                chat_frame = timestamp2frame(chat.timestamp, self._fps)
                self.foresee_chats(self._chat_queue.get_all())
                draw_chats = self._chat_queue.get_all()
                # before
                while frame < chat_frame:
                    self.draw_chats(draw_chats)
                    frame += 1
                    bar.update(1)
                # current
                self._chat_queue.push(chat)
                # forsee
                self.foresee_chats(self._chat_queue.get_all())
                self.draw_chats(self._chat_queue.get_all())
                frame += 1
                bar.update(1)
            # draw left
            while frame < self._total_frame:
                # forsee
                self.foresee_chats(self._chat_queue.get_all())
                self.draw_chats(self._chat_queue.get_all())
                frame += 1
                bar.update(1)
