import os


def get_abs_path(curren_file, filename):
    return os.path.abspath(os.path.join(os.path.dirname(curren_file), filename))


def get_abs_dir(filename):
    return os.path.dirname(filename)


def add_to_system_path(filename):
    os.environ['PATH'] = ':'.join([os.environ.get('PATH'), get_abs_dir(filename)])


def get_filename(filename):
    return os.path.basename(filename)
