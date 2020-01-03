import os
import re

from utils.path import get_abs_path, get_abs_dir
from utils.platform import is_windows

template_file = '../src/template.html'
template_file = get_abs_path(__file__, template_file)

template_dir = get_abs_dir(template_file)


class TemplateUpdater(object):
    def __init__(self, template_file=template_file):
        self._tempate_file = template_file
        self._swf_pattern = re.compile('(src=")([^"]+)(")')
        self._width_pattern = re.compile('(width[:=" ]+)(\d+)(px)')
        self._height_pattern = re.compile('(height[:=" ]+)(\d+)(px)')

    def _read_file(self, filename):
        with open(filename, 'r') as f:
            return f.read()

    def _write_file(self, filename, data):
        with open(filename, 'w') as f:
            f.write(data)

    def __call__(self, filename, width, height):
        # chdir
        os.chdir(os.path.dirname(template_dir))
        data = self._read_file(self._tempate_file)
        if not data:
            return
        # convert to path, relative to tempate_dir
        if is_windows():
            new_file = os.path.abspath(filename).replace(template_dir + '\\', '').replace('\\', '/')
        else:
            new_file = os.path.abspath(filename).replace(template_dir + '/', '')
        data = self._swf_pattern.sub('\g<1>%s\g<3>' % new_file, data)
        data = self._width_pattern.sub('\g<1>%s\g<3>' % width, data)
        data = self._height_pattern.sub('\g<1>%s\g<3>' % height, data)

        self._write_file(self._tempate_file, data)


template_updater = TemplateUpdater()
