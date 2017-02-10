import sys
sys.path.append("../")

import os
import re
import tempfile

from time import sleep
from client import runner
from utils.config_import import DistillerConfig


class ModuleFinder:
    def __init__(self, config):
        self.d_path = config.drio_path
        self.t_path = config.target_path
        self.t_args = config.target_args
        self.w_time = config.w_time
        self.m_time = config.m_time

        self.s_name = None
        self.s_data = None  # Original seed data
        self.temp = None

        self.mod_table = set()

    def prepare_data(self, seed):
        self.s_name = os.path.basename(seed)
        with open(seed, 'rb') as f:
            self.s_data = f.read()

        ext = os.path.splitext(self.s_name)[1]

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as self.temp:
            self.temp.write(self.s_data)

    @staticmethod
    def get_list_of_files(directory_path, ext=None):
        files_list = set()
        for root, subFolders, files in os.walk(directory_path):
            for each_file in files:
                if ext is None:
                    files_list.add(os.path.join(root, each_file))
                else:
                    if each_file.endswith(".{0}".format(ext)):
                        files_list.add(os.path.join(root, each_file))
        return list(files_list)

    def clean(self):
        while True:
            try:
                if os.path.isfile(self.temp.name):
                    os.remove(self.temp.name)
            except WindowsError:
                print "[ +E+ ] - Error deleting file."
                sleep(1)
            else:
                break

    def parse(self, data):
        module_names = set()

        md = re.search(r'Module Table:.*?\n(.*?)BB Table', data, re.DOTALL)
        td = re.search(r'module id, start, size:\n(.*)', data, re.DOTALL)

        if md and td:
            module_data = md.group(1)
            for m in module_data.splitlines():
                m_entry = m.split(",")
                m_name = m_entry[2].strip()
                module_names.add(m_name)

        return module_names

    def go(self, seed_dir, extension):
        print "[ +D+ ] - Getting list of all loaded modules..."

        files = self.get_list_of_files(seed_dir, extension)

        for each_file in files:
            self.prepare_data(each_file)

            logfile = runner.run(self.d_path, self.t_path, self.t_args, self.temp.name, self.w_time, self.m_time)

            if logfile is not None:
                module_names = self.parse(logfile)
                if module_names:
                    self.mod_table.update(module_names)
                    print "[ +D+ ] - Number of modules for current file: %d" % len(self.mod_table)
            else:
                print "[ +E+ ] - Error retrieving log file. Restarting."

            self.clean()

        print self.mod_table


def main(config_file, seed_dir, extension):
    cfg = DistillerConfig(config_file, 'client')

    evaluator = ModuleFinder(cfg)
    evaluator.go(seed_dir, extension)


def usage():
    print "Usage:", sys.argv[0], "<config.yml> <seed_folder> <extension>"


if __name__ == "__main__":
    if len(sys.argv) != 4:
        usage()
    else:
        main(sys.argv[1], sys.argv[2], sys.argv[3])
