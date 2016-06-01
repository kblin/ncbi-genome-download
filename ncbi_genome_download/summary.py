'''Parse NCBI RefSeq/GenBank summary files'''


# pylint: disable=too-few-public-methods
class SummaryReader(object):
    '''An Iterator-like class for assembly summary files'''
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
        '''Return the next entry'''
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
# pylint: enable=too-few-public-methods
