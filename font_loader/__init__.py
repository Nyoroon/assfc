from collections import defaultdict
import os
from fnmatch import fnmatch
import logging
import sys
import pickle
from font_loader.font_info import FontInfo
from font_loader.ttf_parser import TTFFont
from font_loader.ttc_parser import TTCFont
from misc import get_app_data_folder, enumerate_files_in_directory, get_windows_system_fonts_folder, read_linux_font_dirs


is_supported_font = lambda x: os.path.splitext(x)[1].lower() in {'.ttf', '.otf', '.ttc'}

class FontLoader(object):
    def __init__(self, font_dirs = None, load_system_fonts = True):
        font_files = set()

        if load_system_fonts:
            font_files.update(self.enumerate_system_fonts())

        if font_dirs:
            for dir in font_dirs:
                font_files.update(self.enumerate_font_files(dir))

        self.__load_fonts(font_files)

    def get_fonts_for_list(self, font_list):
        found = {}
        not_found = {}

        search_dict = defaultdict(list)
        for font in self.fonts:
            for name in font.names:
                search_dict[name.lower()].append(font)

        for font_info in font_list.keys():
            logging.debug('Processing font %s...' % font_info)
            candidates = search_dict[font_info.fontname.lower()]
            best_candidate = None

            logging.debug('Found %i candidates' % len(candidates))

            if not candidates:
                not_found[font_info] = font_list[font_info]
                continue

            for candidate in candidates:
                if candidate.bold == font_info.bold and candidate.italic == font_info.italic:
                    best_candidate = candidate
                    logging.debug("Found exact match")
                    break

            if not best_candidate:
                logging.debug('Failed to find exact match. Looking for regular version...')
                for candidate in candidates:
                    if candidate.bold == False and candidate.italic == False:
                        best_candidate = candidate
                        logging.debug('Found regular one')
                        break

            if not best_candidate:
                not_found[font_info] = font_list[font_info]
                continue

            if best_candidate in found.values():
                logging.debug("Font %s already exists" % best_candidate.names[0])
                continue

            for already_added in found.values():
                if already_added.md5 == best_candidate.md5:
                    logging.info("Duplicate font found. Skipping.")
                    continue

            found[font_info] = best_candidate
            logging.debug('Found font %s at %s' % (font_info, best_candidate.path))
        return found, not_found


    def __load_fonts(self, fonts_paths):
        cache_file = FontLoader.get_font_cache_file_path()
        removed = []
        self.fonts = []
        try:
            #let's try to load our cache
            with open(cache_file, 'rb') as file:
                cached_fonts = pickle.load(file)
                #updating the cache - finding all removed/added files
            cached_paths = frozenset(map(lambda x: x.path, cached_fonts))
            removed = cached_paths.difference(fonts_paths)
            added = fonts_paths.difference(cached_paths)
            self.fonts = list(filter(lambda x: x.path not in removed, cached_fonts))
        except:
            print(sys.exc_info())
            #we don't care what happened - just reindex everything
            added = fonts_paths

        for font_path in added:
            if fnmatch(font_path, '*.ttc'):
                self.fonts.extend(TTCFont(font_path).get_infos())
            else:
                self.fonts.append(TTFFont(font_path).get_info())

        if added or removed:
            # updating the cache
            with open(cache_file, 'wb') as file:
                pickle.dump(self.fonts, file, -1)


    @staticmethod
    def enumerate_font_files(directory):
        files =  enumerate_files_in_directory(directory)
        return [x for x in files if is_supported_font(x)]


    @staticmethod
    def enumerate_linux_system_fonts():
        paths = []
        for f in read_linux_font_dirs():
            paths.extend(FontLoader.enumerate_font_files(f))
        return paths


    @staticmethod
    def enumerate_windows_system_fonts():
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Fonts\\") as key:
            paths = []
            info = winreg.QueryInfoKey(key)
            fonts_root = get_windows_system_fonts_folder()
            for index in range(info[1]):
                value = winreg.EnumValue(key, index)
                path = value[1] if os.path.isabs(value[1]) else os.path.join(fonts_root, value[1])
                if is_supported_font(path):
                    paths.append(path)
        return paths


    @staticmethod
    def enumerate_system_fonts():
        if sys.platform == 'win32':
            return FontLoader.enumerate_windows_system_fonts()
        else:
            return FontLoader.enumerate_linux_system_fonts()


    @staticmethod
    def discard_cache():
        cache = FontLoader.get_font_cache_file_path()
        if os.path.exists(cache):
            os.remove(cache)


    @staticmethod
    def get_font_cache_file_path():
        return os.path.join(get_app_data_folder(), "font_cache.bin")

