import os, re
from glob import glob
from munge.io.guess import GuessReader
from munge.util.err_utils import warn, info

class MultiGuessReader(object):
    '''A read-only reader which iterates over an entire PTB-structured corpus (one whose directory
hierarchy is corpus -> section+ -> document+). This reader allows neither index-based retrieval or
modification of derivations, nor corpus output.'''
    def __init__(self, topdir, reader=GuessReader):
        self.topdir = topdir
        _, tail = os.path.split(self.topdir)
        if re.match(r'\d\d', tail):
            self.sections = [self.topdir]
        else:
            self.sections = glob(os.path.join(self.topdir, '*'))
        self.reader = reader

    def __iter__(self):
        for section_path in filter(lambda dir_name: os.path.isdir(dir_name), self.sections):
            docs = glob(os.path.join(section_path, '*'))
            for doc_path in docs:
                info("Processing %s...", doc_path)
                reader = self.reader(doc_path)
                for deriv_bundle in reader:
                    yield deriv_bundle

    def no_getitem_setitem(self, *args):
        raise NotImplementedError("get and setitem unavailable with PTBCorpusReader.")
    __getitem__ = __setitem__ = no_getitem_setitem

    def __str__(self):
        raise NotImplementedError("Cannot directly generate treebank with PTBCorpusReader.")

class DirFileGuessReader(object):
    '''Reader allowing the uniform treatment of directories and files.'''
    def __init__(self, path):
        self.path = path

    def __iter__(self):
        path = self.path

        if not os.path.exists(path):
            warn("%s does not exist, so skipping.", path)

        if os.path.isdir(path):
            reader = MultiGuessReader(path)
        elif os.path.isfile(path):
            reader = GuessReader(path)
        else:
            warn("%s is neither a file nor a directory, so skipping.", path)

        for deriv_bundle in reader:
            yield deriv_bundle
