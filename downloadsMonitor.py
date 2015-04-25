import sys
import os.path
import re
import signal
import urllib2

log_file = open("/var/log/downloadsMonitor.log", "a")
processedFileStr = "/volume1/Downloads/processed.txt"
errorFileStr = "/volume1/Downloads/error.txt"
# log_file = open("/Users/tobeswsu/Desktop/downloadsMonitor.log", "a")
# processedFileStr = "/Users/tobeswsu/Desktop/processed.txt"
# errorFileStr = "/Users/tobeswsu/Desktop/error.txt"


def log(text):
    log_file.write(text + "\n")
    log_file.flush()


'''pid = str(os.getpid())
pid_file='/var/run/downloadsMonitor.pid'

if os.path.isfile(pid_file):
    log("%s already exists, exiting" % (pid_file))
    sys.exit()
else:
    file(pid_file, 'w').write(pid)'''

log("Starting")


def signal_handler(signal, frame):
    # os.unlink(pid_file)
    log("Exiting")
    sys.exit(0)


signal.signal(signal.SIGTERM, signal_handler)

allowed_exts = ["mp4", "avi", "mov", "mkv", "m4v"]

# tvDir = "/Users/tobeswsu/Desktop/TV Shows/"
# kidTvDir = "/Users/tobeswsu/Desktop/Kid Shows/"
tvDir = "/volume1/TV Shows/"
kidTvDir = "/volume1/Kid Shows/"


class DownloadMonitor():
    def __init__(self):
        self.processed_files = set()
        if os.path.isfile(processedFileStr):
            tmp = open(processedFileStr, "r")
            self.processed_files.update(tmp.read().splitlines())
            tmp.close()
        else:
            self.processed_files = set()
        self.processing_file = open(processedFileStr, "a")

        self.error_files = set()
        if os.path.isfile(errorFileStr):
            tmp = open(errorFileStr, "r")
            self.error_files.update(tmp.read().splitlines())
            tmp.close()
        else:
            self.error_files = set()
        self.error_file = open(errorFileStr, "a")
        self.addedTVShow = False
        self.addedKidShow = False

    def scanDirectory(self, directory):
        log("Scanning %s" % (directory))
        for root, dirs, filenames in os.walk(directory):
            for filename in filenames:
                self.process_file(directory, filename)
            for folder in dirs:
                log("folder path = %s" % os.path.join(directory, folder))
                self.scanDirectory(os.path.join(directory, folder))

    def process_file(self, path, filename):

        if filename in self.processed_files:
            return True

        self.processed_files.add(filename)
        self.processing_file.write(filename + "\n")

        if not self.is_allowed_path(filename):
            return False

        parentDir = os.path.basename(path)
        names = [filename, parentDir]
        temp = ""
        for name in names:
            temp = re.findall('(.*)\.[S|s]?(\d+)[x|e|E](\d+)(.*)', name)
            if len(temp) <= 0:
                temp = re.findall('(.*) [S|s]?(\d+)[x|e|E](\d+)(.*)', name)
            if len(temp) <= 0:
                temp = re.findall('(.*)\.(\d{4}?).(\d{2}\.\d{2}?)(.*)', name)
            if len(temp) <= 0:
                temp = re.findall('(.*)(Season?).(Episode?)(.*)', name)
            if len(temp) <= 0:
                temp = re.findall('(.*)(\d+?)x(\d+?).(.*)', name)
            if len(temp) > 0:
                if name != filename:
                    new_name = name + os.path.splitext(filename)[1]
                    log("changing filename {0} to {1}".format(filename, new_name))
                    oldPath = os.path.join(path, filename)
                    newPath = os.path.join(path, new_name)
                    try:
                        os.link(oldPath, newPath)
                        filename = new_name
                        self.processed_files.add(filename)
                        self.processing_file.write(filename + "\n")
                    except EnvironmentError as e:
                        log("Unable to link. error={0}\n src={1}\n dest={2}".format(e,oldPath,newPath))
                        self.error_files.add(filename)
                        self.error_file.write(filename + "\n")
                break
        if len(temp) <= 0:
            log("Error parsing filename %s" % filename)
            self.error_files.add(filename)
            self.error_file.write(filename + "\n")
            return False
        log("temp = %s" % temp)

        if len(temp[0]) < 4:
            log("Partial error parsing filename %s" % filename)
            log("Parsed tuple: %s" % temp[0])
        show = temp[0][0]
        show = show.replace(".", "-")
        show = show.replace(" ", "-")
        show = show.replace("_", "-")
        show = show.lower()
        if show == 'american-dad' and len(temp[0]) > 3:
            src = os.path.join(path, filename)
            season = int(temp[0][1])
            season += 1
            season = "{0:0>2}".format(season)
            filename = filename.replace(temp[0][1], season, 1)
            dest = os.path.join(path, filename)
            try:
                os.link(src, dest)
                self.processed_files.add(filename)
                self.processing_file.write(filename + "\n")
            except EnvironmentError as e:
                log(e)
                log("Unable to fix season for {0}".format(filename))
                self.error_files.add(filename)
                self.error_file.write(filename + "\n")
        dest_path = ""
        for name in os.listdir(tvDir):
            if name.lower() == show:
                dest_path = os.path.join(tvDir, name)
                self.addedTVShow = True
                break
        if dest_path == "":
            for name in os.listdir(kidTvDir):
                if name.lower() == show:
                    dest_path = os.path.join(kidTvDir, name)
                    self.addedKidShow = True
                    break

        if dest_path == "":
            log("Missing destination directory for show: %s" % show)
            self.error_files.add(filename)
            self.error_file.write(filename + "\n")
            return False
        log("Moving to directory %s" % dest_path)
        src = os.path.join(path, filename)
        try:
            dest_full_path = os.path.join(dest_path, filename)
            os.link(src, dest_full_path)
        except EnvironmentError as e:
            log("Unable to link. error={0}\n src={1}\n dest={2}".format(e,src,dest_full_path))
            self.error_files.add(filename)
            self.error_file.write(filename + "\n")

        return True


    def is_allowed_path(self, filename):
        filestr = filename.lower()
        ext = os.path.splitext(filename)[1][1:].lower()
        if ext not in allowed_exts:
            return False
        if filestr.find('sample') >= 0:
            return False
        return True


watcher = DownloadMonitor()
watcher.scanDirectory("/volume1/Downloads/")
'''if watcher.addedTVShow:
    urllib2.urlopen("http://192.168.2.99:32400/library/sections/2/refresh")
if watcher.addedKidShow:
    urllib2.urlopen("http://192.168.2.99:32400/library/sections/3/refresh")
'''
# watcher.scanDirectory("/Users/tobeswsu/Desktop/")
