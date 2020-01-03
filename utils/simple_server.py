import os
import socket
import threading
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer

from utils.path import get_filename
from utils.template_updater import template_file, template_dir

PORT = 8000
IP = "127.0.0.1"

TEMPLATE_FILE = get_filename(template_file)

httpd = None


def server():
    Handler = SimpleHTTPRequestHandler
    global httpd
    httpd = TCPServer((IP, PORT), Handler)

    print("serving at port %d " % PORT)
    httpd.serve_forever()


def default_page(ip, port, template_file):
    return 'http://{0}:{1}/{2}'.format(ip, port, template_file)


index_page = default_page(IP, PORT, TEMPLATE_FILE)


def start_server():
    # chdir
    os.chdir(template_dir)
    if not is_open(IP, PORT):
        t = threading.Thread(target=server)
        t.start()


def is_open(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((ip, int(port)))
        s.shutdown(2)
        print('%d is open' % port)
        return True
    except:
        print('%d is down' % port)
        return False
