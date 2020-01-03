import json
import os
from xml.etree.ElementTree import ParseError, Element
from xml.etree.ElementTree import parse, fromstring


class Base(object):
    def __str__(self):
        ds = dir(self)
        # filter
        ds = list(filter(lambda x: not x.startswith('__') and not x.endswith('__'), ds))
        # sort
        ds = sorted(ds)
        # print
        s = ', '.join(list(map(lambda x: '%s=%s' % (x, getattr(self, x)), ds)))
        return '%s(%s)' % (self.__class__.__name__, s)


class Conf(Base):
    annofile = ''
    audiocodec = ''
    avstarttime = ''
    chatfile = ''
    # continue = ''
    duration = ''
    endtime = ''
    hls = ''
    hlsaudioonly = ''
    id = ''
    js = ''
    jsanno = ''
    jschat = ''
    kbps = ''
    name = ''
    novideo = ''
    starttime = ''
    storage = ''
    ver = ''
    videoheight = ''
    videowidth = ''


class Document(Base):
    name = ''
    id = ''
    type = ''
    timestamp = ''


class Page(Base):
    id = ''
    title = ''
    content = ''
    height = ''
    width = ''
    starttimestamp = ''
    speedup = ''
    step = ''
    stoptimestamp = ''
    hls = ''
    # add unique id, auto increase from 0, since some swf files are used more than once.
    uid = ''

    # update uid
    def update_uid(self, uid):
        self.uid = uid
        return self


class Command(Base):
    type = ''
    frameIdx = ''
    timestamp = ''
    documentid = ''
    pageid = ''


class MultiRecord(Base):
    starttimestamp = ''
    stoptimestamp = ''
    duration = ''
    multimedia = ''
    filesize = ''
    havevideo = ''
    chat = ''
    jschat = ''


class Event(Base):
    type = ''
    timestamp = ''
    totaltimestamp = ''


class Content(Base):
    document = ''
    page = ''
    speedup = ''
    step = ''
    videotype = ''
    width = ''
    height = ''


class AnnoCommand(Base):
    id = ''
    type = ''
    timestamp = ''
    documentid = ''
    pageid = ''
    color = ''
    linesize = ''
    p = ''
    removed = ''
    tail = ''  # <![CDATA[xxxx]]> --> xxxx


class Chat(Base):
    timestamp = ''
    utctime = ''
    type = ''
    id = ''
    group = ''
    sender = ''
    groupid = ''
    senderid = ''
    senderId = ''
    content = ''


class AudioIndex(Base):
    timestamp = ''
    filepos = ''


class VideoKey(AudioIndex):
    isconfig = ''


class CustomEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (Document, Page, Command, MultiRecord, Event,
                          Content, AudioIndex, VideoKey)):
            return str(o)
        elif isinstance(o, Element):
            return o.text
        return super(CustomEncoder, self).default(o)


def init_obj_using_attrib_by_exec(cls, obj, exclusive_keys=[]):
    ins = cls()

    [exec('ins.%s = v' % k, dict(ins=ins, v=v)) for k, v in obj.attrib.items() if k not in exclusive_keys]

    return ins


class XmlReader(object):
    def __init__(self):
        self._xml = None
        self.data = []

    def read(self, filename):
        assert os.path.exists(filename)

        try:
            self._xml = parse(filename)
        except ParseError:
            import re
            s = open(filename, 'rb').read().decode(encoding='utf-8', errors='ignore')
            s = re.sub("[\x00-\x08\x0b-\x0c\x0e-\x1f]+", "", s)
            self._xml = fromstring(s.encode(u'utf-8'))

        return self._xml

    def parse(self):
        pass

    @staticmethod
    def json_print(obj, cls=json.JSONEncoder):
        print(json.dumps(obj, indent=2, ensure_ascii=False, cls=cls))


class AnnoXml(XmlReader):
    def __init__(self):
        super(AnnoXml, self).__init__()
        self._command = []

    def parse(self):
        if not self._xml:
            return
        # root
        root = self._xml.getroot()
        cs = []
        for child in root.getchildren():
            # update attrib to call init_obj_using_attrib_by_exec()
            child.attrib.update({'p': ','.join(map(lambda x: '(' + x.text + ')', child.getchildren())),
                                 'tail': list(filter(lambda y: y, map(lambda x: x.tail, child.getchildren())))[0]
                                 if list(filter(lambda y: y, map(lambda x: x.tail, child.getchildren()))) else ''})
            c = init_obj_using_attrib_by_exec(AnnoCommand, child)
            cs.append(c)

        self._command = cs

    @property
    def command(self):
        return self._command


class ChatXml(XmlReader):
    def __init__(self):
        super(ChatXml, self).__init__()
        self._chat = []

    def parse(self):
        if not self._xml:
            return
        # inconsistent cases
        try:
            root = self._xml.getroot()
        except:
            root = self._xml.getchildren()

        cs = []
        for child in root:
            child.attrib.update(child.getchildren()[0].attrib)
            child.attrib.update({'content': child.getchildren()[0].getchildren()[0].text})
            c = init_obj_using_attrib_by_exec(Chat, child)
            cs.append(c)

        self._chat = cs

    @property
    def chat(self):
        return self._chat

    @property
    def duration(self):
        if not self._chat:
            return None
        return float(self.chat[-1].timestamp)


class RecordXml(XmlReader):
    def __init__(self):
        super(RecordXml, self).__init__()

        self.attributes = {}

        self.conf = Conf()

        self.animationsetting = None

        self.document = None

        self.document_action = None

        self.multirecord = None

    def parse(self):
        if not self._xml:
            return
        root = self._xml.getroot()
        self.attributes = root.attrib

        self.conf = init_obj_using_attrib_by_exec(Conf, root, exclusive_keys=['continue'])

        # animationsetting, document, document action, multirecord
        modules = root.getchildren()
        for module in modules:
            name = module.attrib.get('name')
            exec('self.%s = module' % name.replace(' ', '_'))

        self._parse_animationsetting()
        self._parse_document()
        self._parse_document_action()
        self._parse_multirecord()

    def _parse_animationsetting(self):
        pass

    def _parse_document(self):

        if not self.document:
            return

        documents = self.document.getchildren()

        ret = []
        for document in documents:

            d = init_obj_using_attrib_by_exec(Document, document)

            pages = document.getchildren()

            ps = []
            for page in pages:
                p = init_obj_using_attrib_by_exec(Page, page)
                ps.append(p)

            ret.append(dict(document=d, page=ps))
        self.document = ret

    def _parse_document_action(self):

        if not self.document_action:
            return

        commands = self.document_action.getchildren()

        cs = []
        for command in commands:
            c = init_obj_using_attrib_by_exec(Command, command)

            cs.append(c)

        self.document_action = dict(command=cs)

    def _parse_multirecord(self):

        if not self.multirecord:
            return

        multirecords = self.multirecord.getchildren()

        result = []

        for multirecord in multirecords:

            m = init_obj_using_attrib_by_exec(MultiRecord, multirecord)

            es = []
            ads = []
            vks = []

            for child in multirecord.getchildren():
                tag = child.tag

                if tag == 'events':
                    # events
                    events = child.getchildren()
                    for event in events:
                        e = init_obj_using_attrib_by_exec(Event, event)

                        contents = event.getchildren()

                        cs = []
                        for content in contents:
                            c = init_obj_using_attrib_by_exec(Content, content)

                            cs.append(c)

                        es.append(dict(event=e, content=cs))

                elif tag == 'audioindexs':
                    # audioindex
                    audioindexs = child.getchildren()
                    for audioindex in audioindexs:
                        a = init_obj_using_attrib_by_exec(AudioIndex, audioindex)

                        ads.append(a)

                elif tag == 'videokeys':
                    # videokey
                    videokeys = child.getchildren()
                    for videokey in videokeys:
                        vk = init_obj_using_attrib_by_exec(VideoKey, videokey)

                        vks.append(vk)

                else:
                    print(tag)
                    pass
            result.append(dict(multirecord=m, events=es, audioindex=ads, videokey=vks))
        self.multirecord = result

    @property
    def grfs(self):
        if not self.multirecord:
            return []

        return list(map(lambda x: dict(
            multimedia=x.get('multirecord').multimedia,
            starttimestamp=x.get('multirecord').starttimestamp,
            stoptimestamp=x.get('multirecord').stoptimestamp,
            duration=x.get('multirecord').duration,
            width=self.videowidth,
            height=self.videoheight,
        ), self.multirecord))

    @property
    def videowidth(self):
        return self.conf.videowidth

    @property
    def videoheight(self):
        return self.conf.videoheight

    @property
    def pages(self):
        if not self.document:
            return []
        pages = list(map(lambda x: x['page'], self.document))
        pages = [i for item in pages for i in item]
        # init uid
        pages = [item.update_uid(idx) for idx, item in enumerate(pages)]
        return pages

    @property
    def swfs(self):
        if not self.document:
            return []
        return list(map(lambda x: dict(
            content=x.content,
            width=x.width,
            height=x.height,
            starttimestamp=x.starttimestamp,
            stoptimestamp=x.stoptimestamp,
            pageid=x.id,
            uid=x.uid,
            # unique filename
            ufilename='{uid}-{content}'.format(uid=x.uid, content=x.content)
        ), self.pages))
