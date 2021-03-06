from collections import namedtuple
import logging
import struct
from font_loader.ttf_parser import TTFFont

TTCHeader = namedtuple('TTCHeader', ['tag','version','num_fonts'])

class TTCFont(object):

    def __init__(self, path):
        self.__info = []
        self.parse(path)

    def parse(self, path):
        with open(path,'rb') as file:
            data = struct.unpack('>4sIL', file.read(12))
            ttc_header = TTCHeader(data[0].decode('ascii'),data[1],data[2])
            if ttc_header.tag != 'ttcf':
                return

            ttf_offsets = []
            for i in range(ttc_header.num_fonts):
                ttf_offsets.append(struct.unpack('>I',file.read(4))[0])

        for offset in ttf_offsets:
            ttf_font = TTFFont(path, offset)
            self.__info.append(ttf_font.get_info())

    def get_infos(self):
        return self.__info

