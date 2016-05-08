'''Parse NCBI RefSeq/GenBank summary files'''
import logging


class SummaryReader(object):
    def __init__(self, infile):
        self._file = infile
        line = ''
        while 'assembly_accession' not in line:
            line = self._file.readline().rstrip('\n')

        if line.startswith('# '):
            line = line[2:]

        self._fields = line.split('\t')

    def __iter__(self):
        return self

    def next(self):
        return self.__next__()

    def __next__(self):
        entry = {}
        line = self._file.readline().rstrip('\n')
        if line == '':
            raise StopIteration
        parts = line.split('\t')
        for i, val in enumerate(parts):
            entry[self._fields[i]] = val
        return entry
