'''Parse NCBI RefSeq/GenBank summary files'''

import logging


# pylint: disable=too-few-public-methods
class SummaryReader(object):
    '''An Iterator-like class for assembly summary files'''
    def __init__(self, infile):
        self._file = infile
        self._lineno = 0
        line = ''
        while 'assembly_accession' not in line:
            line = self._file.readline().rstrip('\n')
            self._lineno += 1

        if line.startswith('# '):
            line = line[2:]

        self._fields = line.split('\t')

    def __iter__(self):
        return self

    def __next__(self):
        entry = {}
        parts = []
        while len(parts) != len(self._fields):
            line = self._file.readline().rstrip('\n')
            self._lineno += 1
            if line == '':
                raise StopIteration
            parts = line.split('\t')
            if len(parts) != len(self._fields):
                logging.error('Invalid line length in summary file line %s. Expected %s, got %s. Skipping entry.',
                              self._lineno, len(self._fields), len(parts))
        for i, val in enumerate(parts):
            entry[self._fields[i]] = val
        return entry

    next = __next__
# pylint: enable=too-few-public-methods
