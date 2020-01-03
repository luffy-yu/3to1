import os
import subprocess

from PIL import Image
from swf.movie import SWF

from core.grf_reader import FFMPEG_FILE, FFMPEG_LOGLEVEL
from utils.chrome_driver import ChromeDriver
from utils.path import get_abs_path
from utils.platform import get_sys_platform
from utils.simple_server import index_page as INDEX_PAGE
from utils.simple_server import start_server
from utils.template_updater import template_updater

CHROMEDRIVER_PATH = '../executable/' + get_sys_platform() + '/chromedriver'
CHROMEDRIVER_PATH = get_abs_path(__file__, CHROMEDRIVER_PATH)


class SwfReader(object):
    def __init__(self):
        self._swf = None

    def read(self, filename):
        assert os.path.exists(filename)

        self._swf = None

        with open(filename, 'rb') as f:
            self._swf = SWF(f)
            return self._swf

    '''
    def export_png(self, filename):
        from swf.export import SVGExporter
        import cairosvg
        if not self._swf:
            return
        svg_exporter = SVGExporter()
        svg = self._swf.export(svg_exporter)
        open(filename, 'wb').write(svg.read())
        cairosvg.surface.PNGSurface.convert(svg.read(), write_to=filename)
    '''

    @property
    def swf(self):
        return self._swf

    def tags(self):
        return self.swf.tags

    def get_images(self):
        tags = self.tags()
        jpegs = list(filter(lambda x: x.name in ('DefineBitsJPEG2',
                                                 'DefineBitsJPEG3',
                                                 ), tags))
        images = list(map(lambda x: Image.open(x.bitmapData), jpegs))
        return images

    def get_shapes(self):
        tags = self.tags()
        shapes = list(filter(lambda x: x.name in ('DefineShape3',), tags))
        return shapes


class SwfExporter(object):
    def __init__(self, default_width=None, default_height=None):
        self._default_width = default_width or 960
        self._default_height = default_height or 540

    @property
    def default_width(self):
        return self._default_width

    @property
    def default_height(self):
        return self._default_height

    # fixed window's scale problem in high dpi
    def ensure_image_size(self, filename, width, height):
        img = Image.open(filename)
        if img.width != width or img.height != height:
            img = img.resize((width, height), Image.ANTIALIAS)
            img.save(filename)
        img.close()

    def __call__(self, filename, to=None, width=None, height=None):
        # cwd for save images
        cwd = os.getcwd()
        # update template
        # first use default size, then resize to target size
        template_updater(filename, width=self.default_width, height=self.default_height)
        # start server
        start_server()
        # start chrome
        cd = ChromeDriver(CHROMEDRIVER_PATH)
        # open page
        cd.get_flash_url(INDEX_PAGE)
        # save to png
        os.chdir(cwd)
        if not to:
            to = filename[:filename.rindex('.')] + '.png'
        cd.save_screenshot(to)
        # ensure image size
        self.ensure_image_size(to, int(width), int(height))
        cd.quit_driver()


class PngTransformer(object):
    def __init__(self, loglevel=FFMPEG_LOGLEVEL):
        self._loglevel = loglevel

    def __call__(self, filename, output=None, duration_s='1'):
        if not output:
            output = filename[: filename.rindex('.')] + '.mp4'

        # refer: https://stackoverflow.com/questions/20847674/ffmpeg-libx264-height-not-divisible-by-2
        parameters = [FFMPEG_FILE, '-framerate', '1', '-loop', '1', '-i', filename,
                      '-c:v', 'libx264', '-tune', 'stillimage', '-r', '10', '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2',
                      '-pix_fmt', 'yuv420p', '-strict', '-2', '-loglevel', self._loglevel,
                      '-t', duration_s, '-y', output]

        subprocess.call(parameters)
