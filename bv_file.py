
# ##filename=bv_file.py, edited on 29 Oct 2020 Thu 05:11 PM
# filename=bv_file.py, edited on 12 Oct 2016 Wed 09:38 AM

__author__ = "Siew Kam Onn"
__email__ = "kosiew at gmail.com"
__version__ = "$Revision: 1.0 $"
__date__ = "$Date: 27/Jul/2017"
__copyright__ = "Copyright (c) 2017 Siew Kam Onn"
__license__ = "Python"

""" a collection of file related functions """
from bv_file64 import *
from pathlib import Path
# import bv_symlink
import bv_fire
import attr
import bv_subprocess
import os
import shutil
import re
import csv
import json

@attr.s
class FileLinesMarker (object):
    """FileLinesMarker marks all file lines with a string at the
    end


    Attributes:
        path_file (str): full path file
        marker_string (str): string to append to all lines within file
        marker_position (int, optional): position to append marker_string

    """

    path_file = attr.ib()
    marker_string = attr.ib()
    marker_position = attr.ib(default=None)

    def __attrs_post_init__(self):
        if self.marker_position:
            self.marker_position = int(self.marker_position)

        p, f = get_path_file_tuple(self.path_file)
        _f = f'{f}_tmp'
        self.temp_file = os.path.join(p, _f)
        self.marker_string = str(self.marker_string)

    def do(self):
        """

        """

        with open(self.temp_file, 'w') as out_file:
            with open(self.path_file, 'r') as in_file:
                for line in in_file:
                    _line = line.rstrip('\n')
                    _line = _line.rstrip('\r')
                    if self.marker_position:
                        _line = _line.ljust(self.marker_position)

                    out_file.write(_line + self.marker_string + '\n')

        rename_file(self.temp_file, self.path_file)

# allowed_types = (float, int)
# def x_smaller_than_y(self, attribute, value):
#     if value >= self._y:
#         raise ValueError("'x' has to be smaller than 'y'!")

@attr.s
class FileExtensionChanger:

    """ FileExtensionChanger changes extension from from_extension to to_extension
    """


    path_file = attr.ib()
    to_extension = attr.ib()

    def __attrs_post_init__(self):
        pass

    def get_new_path_file(self):
        p, f, e = get_path_file_extension_tuple(self.path_file)
        fe = f'{f}{self.to_extension}'
        new_path_file = os.path.join(p, fe)
        return new_path_file

    def do(self):
        """
        """
        new_path_file = self.get_new_path_file()
        rename_file(self.path_file, new_path_file)

        return new_path_file


# allowed_types = (float, int)
# def x_smaller_than_y(self, attribute, value):
#     if value >= self._y:
#         raise ValueError("'x' has to be smaller than 'y'!")

@attr.s
class FilesAddFix:
    """FilesAddSuffix gets all files in folder with pattern and adds a prefix or suffix

    """

    folder = attr.ib()
    pattern = attr.ib()
    fix = attr.ib() # the .fix to add
    prefix = attr.ib() # if True adds prefix, else adds as suffix

    def __attrs_post_init__(self):
        pass

    def get_new_path_file(self, path_file):
        """

        """
        p, f, e = get_path_file_extension_tuple(path_file)
        if self.prefix:
            f = f'{self.fix}{f}'
        else:
            f = f'{f}{self.fix}'

        fe = f'{f}{e}'
        result = os.path.join(p, fe)
        return result

    def add_fix(self, path_file):
        """

        """
        new_path_file = self.get_new_path_file(path_file)
        return rename_file(path_file, new_path_file)


    def do(self):
        ff = FolderFiles(self.folder, patterns=self.pattern,
                         single_level=True)
        for i, f in enumerate(ff.files):
            self.add_fix(f)
        return i+1

@attr.s
class FilesExtensionChanger:
    """FilesExtensionChanger changes all files within folder with pattern to to_extension

    """

    folder = attr.ib()
    pattern = attr.ib()
    to_extension = attr.ib()

    def __attrs_post_init__(self):
        pass

    def do(self):
        ff = FolderFiles(self.folder, patterns=self.pattern,
                         single_level=True)
        for i, f in enumerate(ff.files):
            fec = FileExtensionChanger(f, self.to_extension)
            fec.do()
        return i+1

@attr.s
class DateFileCopier (object):
    """
        a DateFileCopier copies files of dates to another folder

        if to_folder_date_format is None
            will not create a date folder in to_folders
    """
    dates = attr.ib()
    from_folders = attr.ib()
    extensions = attr.ib()
    to_folders = attr.ib()
    to_folder_date_format = attr.ib(default=None)

    def init(self):
        a.assert_is_not_none(self.from_folders, 'from_folders is required')
        a.assert_is_not_none(self.to_folders, 'to_folders is required')
        if not self.extensions:
            self.extensions = ['']
        if not self.dates:
            self.dates = [u.now()]
        self.dates = list(map(bv_date.parse_date, self.dates))
        strip = lambda a : a.strip()

        self.from_folders = list(map(strip, self.from_folders))
        self.to_folders = list(map(strip, self.to_folders))
        self.extensions = list(map(strip, self.extensions))

    def get_from_files(self):
        """
            returns a generator of files in from_folders with
            extension
        """
        for from_folder in self.from_folders:
            for extension in self.extensions:
                glob_pattern = r'{0}\*.{1}'.format(from_folder, extension)
                files = glob.iglob(glob_pattern)
                for file in files:
                    yield file

    def ensure_folder_exists(self, folder):
        """
        """
        if not exists(folder):
            mkdir(folder)

    def copy(self, file, to_folders, date):
        """
        """
        i = 0
        for to_folder in to_folders:
            _to_folder = to_folder
            if self.to_folder_date_format:
                date_folder_name = date.strftime(self.to_folder_date_format)
                _to_folder = os.path.join(to_folder, date_folder_name)
            self.ensure_folder_exists(_to_folder)

            copy(file, _to_folder)
            p, f = get_path_file_tuple(file)
            i += 1

        return i

    def do(self):
        """
        """
        self.init()
        i = 0
        copied_files = []
        failed_files = []
        for file in self.get_from_files():
            for date in self.dates:
                try:
                    ok = False
                    file_last_modified_time = get_file_last_modified_time(
                        file)
                    if file_last_modified_time.date() == date.date():
                        self.copy(file, self.to_folders, date)
                        p, f = get_path_file_tuple(file)
                        copied_files.append(f)
                        i += 1
                except Exception as e:
                    failed_files.append(file)

        self.copied_files = sorted(copied_files)
        self.failed_files = sorted(failed_files)
        return i

def is_link(path_file):
    """ Returns True if path_file is a symbolic link
    """
    return Path(path_file).is_symlink()

def get_subdirectories(root, subdirectory_name):
    for root, dirs, subdirs in os.walk(root):
        for d in dirs:
            if d == subdirectory_name:
                yield root, d

def delete_subdirectories(root, subdirectory_name):
    '''
        useful for deleting node_modules in source directory to
        reduce files synchronized
    '''
    for root, dirs, subdirs in os.walk(root):
        for d in dirs:
            if d == subdirectory_name:
                _d = os.path.join(root, d)
                shutil.rmtree(_d)
                print(f'deleted {_d}')

def symlink_subdirectories(root, subdirectory_name,
                           move_to_root):
    '''
        useful for moving directories to a non-synced location
        and creating a symlink in its place

        eg for node_modules

        move_to_root is a dictionary to modify the path_folder eg
        {'Source': 'Source-nosync'}

        to move from Source... to Source-nosync...
    '''
    for root, subdirectory in get_subdirectories(root, subdirectory_name):
        from_folder = os.path.join(root, subdirectory)
        for k, v in move_to_root.items():
            to_folder = from_folder.replace(k, v, 1)
            move_folder(from_folder, to_folder)
            os.symlink(to_folder, from_folder,
                       target_is_directory=True)
            print(f'created symlink {from_folder} for {to_folder}')



def delete_old_directories(directories, pattern = None,
    old_threshold_days = 100, test = True):
    """ Returns list of directories deleted,
           and list of directories that could not be deleted
    """
    if not u.is_iterable(directories):
        return delete_old_directories((directories,), pattern,
            old_threshold_days, test)

    l = []
    f = []
    for directory in directories:
        for d in get_dir_items(directory, yield_directories = True):
            if get_days_since_last_modified(d) > old_threshold_days:
                try:
                    if not test and not is_link(d):
                        os.rmdir(d)
                    l.append(d)
                    message = 'deleted {0}'.format(d)
                    print(message)
                except OSError as e:
                    f.append('{0} - {1}'.format(d, e))

    return l, f

def touch(pathfile):
    command = ['touch', pathfile]
    return bv_subprocess.run(command)

def expanduser(f):
    return os.path.expanduser(f)


def get_p_glob_files(p, pattern):
    '''
        a dummy function to be mocked for testing
    '''
    return p.glob(pattern)

def get_re_match(re, a_string):
    return re.match(a_string)

def get_duplicate_files(folder):
    '''
        get duplicate files in folder
        duplicate files have a numeric suffix like
        automatewoo (1).zip
    '''
    p = Path(expanduser(folder))
    files = get_p_glob_files(p, '*(*)*')
    RE = re.compile('(?P<pre>.+)(\(\d+\))(?P<post>\..+)')

    duplicate_parts = []
    for i, f in enumerate(files):
        m = get_re_match(RE, f.name)
        if m:
            pre = m.group('pre').strip()
            post = m.group('post')
            t = (pre, post)
            if t not in duplicate_parts:
                result = []
                def append_result(files, test_m=True):
                    for _file in files:
                        m = RE.match(_file.name)
                        if m or not test_m:
                            result.append(_file)

                _files = get_p_glob_files(p, f'{pre}*{post}')
                append_result(_files)
                _files = get_p_glob_files(p, f'{pre}{post}')
                append_result(_files, test_m=False)

                if len(result) > 1:
                    duplicate_parts.append(t)
                    yield result

def get_files_sorted_by_mtime(files):
    return sorted(files, key=os.path.getmtime)

def delete_duplicate_sync_files(folder, mark_for_delete=True):
    '''
        After Google Drive Sync or after download, duplicate sync files have a (\d+)
        suffix
        eg
        automatewoo (1).zip
        this script deletes older datestamp files and removes the
        numeric suffix

        if mark_for_delete then
          instead of deleting, rename file to prefix with 'delete ...'
    '''

    delete_count = 0
    for duplicate_files in get_duplicate_files(folder):
        _duplicate_files = get_files_sorted_by_mtime(duplicate_files)
        filename_to_keep = duplicate_files[-1]
        new_name = str(filename_to_keep)

        deleted_files = []
        for _file in _duplicate_files[0:-1]:
            file_name = str(_file)
            if mark_for_delete:
                delete_file_name = get_new_path_file_with_prefix(
                    file_name, 'delete ', True)
                rename_file(file_name, delete_file_name)
                deleted_files.append(delete_file_name)
            else:
                if delete_file(file_name):
                    delete_count += 1
                deleted_files.append(file_name)

        if deleted_files:
            deleted_files_string = '\n'.join(deleted_files)
            if mark_for_delete:
                message = f'marked for delete:\n{deleted_files_string}'
            else:
                message = f'deleted:\n{deleted_files_string}'
            print(message)

        old_name = str(_duplicate_files[-1])
        if new_name != old_name:
            rename_file(old_name, new_name)
        # _duplicate_files[-1].rename(Path(filename_to_keep.parent, new_name))




# Function to convert a CSV to JSON
# Takes the file paths as arguments
def make_json(csvFilePath, jsonFilePath):

    # create a dictionary
    paths = []
    # Open a csv reader called DictReader
    with open(csvFilePath, encoding='utf-8') as csvf:
        csvReader = csv.DictReader(csvf)
        # Convert each row into a dictionary
        # and add it to data
        for row in csvReader:
            row['arg'] = row['url']
            row['variables'] = {'url': row['url']}
            paths.append(row)

    data = {'items': paths}
    # Open a json writer, and use the json.dumps()
    # function to dump data
    with open(jsonFilePath, 'w', encoding='utf-8') as jsonf:
        jsonf.write(json.dumps(data, indent=4))


@bv_time.print_timing
def main():
    import bv_error

    try:
        bv_fire.Fire(Runner)
    except Exception as e:
        bv_error.go_error(e, invoked_by_fire=True)

aspect.wrap_module(__name__)

@attr.s
class Runner (bv_fire._Runner):
    """
        This is a collection of file related tasks

        Usage:
        dof to delete old files
        wfif to wrap file in folders
        astal to append string to all lines in file
        cfe to change files extension in folder with pattern to to_extension
        af to change files in folder with pattern by adding ..fix
    """

    def delete_duplicate_sync_files(self, folder):
        delete_duplicate_sync_files(folder)

    def af(self, folder, pattern, fix, prefix):
        """

        """
        faf = FilesAddFix(folder, pattern, fix, prefix)
        number_of_files_changed = faf.do()

        message = f'changed {number_of_files_changed} files'
        self.robot.say(message)

    def csv_to_json(self, csv_file, json_file):
        make_json(csv_file, json_file)

    def cfe(self, folder, pattern, to_extension):
        fec = FilesExtensionChanger(folder, pattern, to_extension)
        number_of_files_changed = fec.do()

        message = f'changed {number_of_files_changed} files'
        self.robot.say(message)


    def astal(self, path_file, string_to_append, position=None):
        """

        Args:
            string_to_append (str):
            position=None (int): append at which position of line
              if None, will append to end of line

        Returns:

        """

        flm = FileLinesMarker(path_file, string_to_append, position)
        flm.do()


    def symlink_subdirectories(self, root, subdirectory_name,
            move_to_root={'/Users/kosiew/Google Drive/Source': '/Users/kosiew/Source-nosync'}):
        symlink_subdirectories(root, subdirectory_name,
                               move_to_root)


    def delete_subdirectories(self, root, subdirectory_name):
        '''
            delete subdirectories in root if subdirectory ==
            subdirectory_name

            eg
            delete_subdirectories "/Users/kosiew/Google
            Drive/Source/js/Training material/ReactDev"
            node_modules
        '''
        delete_subdirectories(root, subdirectory_name)

    def dof(self, folder, file_pattern, old_threshold_days,
            simulate=False):
        """
        delete old files

        Args:
            folder(str): the folder to delete files from
            file_pattern(str): file_pattern to delete
            old_threshold_days(int):
            simulate(boolean)

        """
        delete_old_files(folder, file_pattern, old_threshold_days, simulate)

    def wfif(self, folder, excluded_extension=['.ffs_db']):
        """
            in folder, find files and then move them to folders of
            same name

        Args:
            folder (str): the folder to look for files

        Returns:
            list of folders created

        """
        new_folders = []
        for fp in u.all_files_in(folder, single_level=True,
                follow_link=True):
            p, f, e = get_path_file_extension_tuple(fp)
            if e and e not in excluded_extension:
                _dir = os.path.join(p, f)
                mkdir(_dir)
                move_to_folder(fp, _dir)
                new_folders.append(_dir)
        result = new_folders

        return result

if __name__=="__main__":
    main()


