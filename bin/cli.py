import os

import click

try:
    from core.swf_reader import SwfExporter
    from core.grf_reader import GrfTransformer
    from core.xml_reader import RecordXml
    from core.grf_reader import MP4Merger
    from core.swf_reader import PngTransformer
    from core.movie_editor import MovieEditor
    from core.chat_editor import ChatEditor
    from core.final_merger import FinalMerger
except:
    print('Please config the environment first.')
    import traceback

    print(traceback.format_exc())
    exit(1)


def shutdown_server():
    from utils.simple_server import httpd
    if httpd:
        httpd.shutdown()


@click.group()
def command():
    pass


@command.command(help='Convert swf to png')
@click.option('-s', '--swf_file', required=True, type=click.Path(file_okay=True, dir_okay=False, exists=True),
              help='SWF file')
@click.option('-p', '--png_file', required=False, type=click.Path(file_okay=True, dir_okay=False),
              help='PNG file')
@click.option('-w', '--width', required=False, type=click.INT, help='Output png width',
              default=SwfExporter().default_width, show_default=True)
@click.option('-h', '--height', required=False, type=click.INT, help='Output png height',
              default=SwfExporter().default_height, show_default=True)
def swf2png(swf_file, png_file, width, height):
    if swf_file:
        se = SwfExporter(default_width=width, default_height=height)
        se(swf_file, to=png_file, width=width, height=height)
        shutdown_server()


@command.command(help='Convert swfs in record.xml to pngs')
@click.option('-r', '--record_file', required=True, type=click.Path(file_okay=True, dir_okay=False, exists=True))
@click.option('-s', '--swf_folder', required=True, type=click.Path(file_okay=False, dir_okay=True, exists=True))
@click.option('-p', '--png_folder', required=False, type=click.Path(file_okay=False, dir_okay=True, exists=True))
@click.option('--default_width', required=False, type=click.INT, help='default width to display swf',
              default=960, show_default=True)
@click.option('--default_height', required=False, type=click.INT, help='default height to display swf',
              default=540, show_default=True)
def record2pngs(record_file, swf_folder, png_folder, default_width, default_height):
    if record_file and swf_folder:
        rx = RecordXml()
        rx.read(record_file)
        rx.parse()
        swfs = rx.swfs
        # output
        output_folder = swf_folder if not png_folder else png_folder
        se = SwfExporter(default_width=default_width, default_height=default_height)
        with click.progressbar(swfs, length=len(swfs), label='Converting') as swfs:
            for swf in swfs:
                content = swf['content']
                ufilename = swf['ufilename']
                width = swf['width']
                height = swf['height']
                grf_filename = os.path.join(swf_folder, content)
                png_filename = os.path.join(output_folder, ufilename[:ufilename.rindex('.')] + '.png')
                se(grf_filename, to=png_filename, width=width, height=height)
        shutdown_server()


@command.command(help='Covert grf to mp4')
@click.option('-g', '--grf_file', required=True, type=click.Path(file_okay=True, dir_okay=False, exists=True),
              help='GRF file')
@click.option('-m', '--mp4_file', required=False, type=click.Path(file_okay=True, dir_okay=False),
              help='MP4 file')
def grf2mp4(grf_file, mp4_file):
    if grf_file:
        gt = GrfTransformer()
        gt(grf_file, output=mp4_file)


@command.command(help='Convert png to mp4')
@click.option('-p', '--png_file', required=True, type=click.Path(file_okay=True, dir_okay=False, exists=True),
              help='PNG file')
@click.option('-m', '--mp4_file', required=False, type=click.Path(file_okay=True, dir_okay=False),
              help='PNG file')
@click.option('-d', '--duration', required=False, type=click.STRING,
              help='Video duration (unit: second)', default='1', show_default=True)
def png2mp4(png_file, mp4_file, duration):
    if png_file:
        pt = PngTransformer()
        pt(png_file, mp4_file, duration)


@command.command(help='Convert pngs to mp4s')
@click.option('-r', '--record_file', required=True, type=click.Path(file_okay=True, dir_okay=False, exists=True))
@click.option('-p', '--png_folder', required=True, type=click.Path(file_okay=False, dir_okay=True, exists=True))
@click.option('-m', '--mp4_folder', required=False, type=click.Path(file_okay=False, dir_okay=True, exists=True))
def pngs2mp4s(record_file, png_folder, mp4_folder):
    if record_file and png_folder:
        rx = RecordXml()
        rx.read(record_file)
        rx.parse()
        swfs = rx.swfs
        output_folder = png_folder if not mp4_folder else png_folder
        # pt
        pt = PngTransformer()
        with click.progressbar(swfs, length=len(swfs), label='Converting...') as swfs:
            for swf in swfs:
                # png file comes from swf file
                # use unique filename
                content = swf['ufilename'].replace('.swf', '.png')
                # width = swf['width']
                # height = swf['height']
                starttimestamp = swf['starttimestamp']
                stoptimestamp = swf['stoptimestamp']
                # cal duration
                # use abs() to deal with the situation when starttimestamp="5801.734" stoptimestamp="5801.684"
                duration = '%.3f' % abs(float(stoptimestamp) - float(starttimestamp))
                png_filename = os.path.join(png_folder, content)
                mp4_filename = os.path.join(output_folder, content[:content.rindex('.')] + '.mp4')
                pt(png_filename, mp4_filename, duration_s=duration)


@command.command(help='Convert grfs in record.xml to mp4s')
@click.option('-r', '--record_file', required=True, type=click.Path(file_okay=True, dir_okay=False, exists=True))
@click.option('-g', '--grf_folder', required=True, type=click.Path(file_okay=False, dir_okay=True, exists=True))
@click.option('-m', '--mp4_folder', required=False, type=click.Path(file_okay=False, dir_okay=True, exists=True))
def record2mp4s(record_file, grf_folder, mp4_folder):
    if record_file and grf_folder:
        rx = RecordXml()
        rx.read(record_file)
        rx.parse()
        grfs = rx.grfs
        # output folder
        output_folder = grf_folder if not mp4_folder else mp4_folder
        # gt
        gt = GrfTransformer()
        with click.progressbar(grfs, length=len(grfs), label='Converting...') as grfs:
            for grf in grfs:
                filename = grf['multimedia']
                # starttimestamp = grf['starttimestamp']
                # stoptimestamp = grf['stoptimestamp']
                duration = grf['duration']
                # force size to 320x240, since some is 640x480
                # width = grf['width']
                # height = grf['height']
                grf_filename = os.path.join(grf_folder, filename)
                mp4_filename = os.path.join(output_folder, filename[:filename.rindex('.')] + '.mp4')
                # use duration since starttimestamp doesn't always start with 0.000.
                gt(grf_filename, output=mp4_filename,  # width=width, height=height,
                   starttimestamp='0', stoptimestamp=duration)


@command.command(help='Merge mp4 files to ONE mp4 file')
@click.option('-r', '--record_file', required=True, type=click.Path(file_okay=True, dir_okay=False, exists=True))
@click.option('-m', '--mp4_folder', required=True, type=click.Path(file_okay=False, dir_okay=True, exists=True))
@click.option('-o', '--output', required=True, type=click.Path(file_okay=True, dir_okay=False))
@click.option('--source', required=True, type=click.Choice(['grf', 'swf']),
              help='source file type that mp4 is converted from')
def mergemp4s(record_file, mp4_folder, output, source):
    if record_file and mp4_folder and output and source:
        mm = MP4Merger()
        if source == 'grf':
            mm.merge_using_record_xml_of_grf(record_file, mp4_folder, output)
        else:
            mm.merge_using_record_xml_of_swf(record_file, mp4_folder, output)


@command.command(help='Add annotation to mp4 file')
@click.option('-m', '--mp4_file', required=True, type=click.Path(file_okay=True, dir_okay=False, exists=True),
              help='MP4 file, converted and merged from swf files')
@click.option('-a', '--anno_file', required=True, type=click.Path(file_okay=True, dir_okay=False, exists=True),
              help='Annotation file, xml format')
@click.option('-o', '--output', required=False, type=click.Path(file_okay=True, dir_okay=False))
@click.option('--resize', is_flag=True, default=False, show_default=True, help='Whether to size')
@click.option('--resize_width', default=960, show_default=True, type=click.INT,
              help='resize width')
@click.option('--resize_height', default=540, show_default=True, type=click.INT,
              help='resize height')
def addannotation(mp4_file, anno_file, output, resize, resize_width, resize_height):
    if mp4_file and anno_file:
        if not output:
            output = mp4_file[:mp4_file.rindex('.')] + "_anno.mp4"
        me = MovieEditor(mp4_file, output, resize_width if resize else None, resize_height if resize else None)
        me.draw_anno_file(anno_file)


@command.command(help='Convert chat xml file to mp4 file')
@click.option('-c', '--chat_file', required=True, type=click.Path(file_okay=True, dir_okay=False, exists=True),
              help='chat file, xml format')
@click.option('-w', '--width', type=click.INT, default=320, show_default=True,
              help='output mp4 video width')
@click.option('-h', '--height', type=click.INT, default=300, show_default=True,
              help='output mp4 video height')
@click.option('-f', '--fps', type=click.INT, default=10, show_default=True,
              help='output mp4 video fps')
@click.option('-m', '--max_size', type=click.INT, default=10, show_default=True,
              help='maximum of visible chat messages count')
@click.option('-x', '--x_offset', type=click.INT, default=10, show_default=True,
              help='The distance between text and the left border')
@click.option('-y', '--y_offset', type=click.INT, default=5, show_default=True,
              help='The distance between text and the upper border')
@click.option('-o', '--output', required=False, type=click.Path(file_okay=True, dir_okay=False))
def chat2mp4(chat_file, width, height, fps, max_size, x_offset, y_offset, output):
    if chat_file:
        if not output:
            output = chat_file[:chat_file.rindex('.')] + '.mp4'
        ce = ChatEditor(width=width, height=height,
                        filename=output, fps=fps, maxsize=max_size,
                        x_offset=x_offset, y_offset=y_offset)
        ce.draw(chat_file)
        ce.close()


@command.command(help='3to1, merge 3 mp4 files to one mp4 file')
@click.option('-s', '--swf_mp4', required=True, type=click.Path(file_okay=True, dir_okay=False, exists=True),
              help='MP4 file, converted and merged from swf files')
@click.option('-g', '--grf_mp4', required=True, type=click.Path(file_okay=True, dir_okay=False, exists=True),
              help='MP4 file, converted and merged from grf files')
@click.option('-c', '--chat_mp4', required=True, type=click.Path(file_okay=True, dir_okay=False, exists=True),
              help='MP4 file, converted from chat xml file')
@click.option('-o', '--output', required=True, type=click.Path(file_okay=True, dir_okay=False),
              help='output mp4 file')
@click.option('-f', '--fps', type=click.INT, default=10, show_default=True,
              help='output mp4 video fps')
def final(swf_mp4, grf_mp4, chat_mp4, output, fps):
    if swf_mp4 and grf_mp4 and chat_mp4 and output:
        fm = FinalMerger(swf_mp4, grf_mp4, chat_mp4, output, fps=fps)
        fm.merge()
        fm.close()


if __name__ == '__main__':
    command()
