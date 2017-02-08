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
                logging.error('Invalid line length in summary file line %s. Expected %s, got %s. Attempting to fix.',
                              self._lineno, len(self._fields), len(parts))
                submitter_idx = self._fields.index('submitter')
                ftp_path_idx = self._fields.index('ftp_path')
                # if there is a submitter, and the ftp_path is shifted by one
                try:
                    if parts[submitter_idx] != '' and parts[ftp_path_idx + 1].startswith('ftp://'):
                        logging.error("Extra tab after submitter detected in line %s, fixing entry", self._lineno)
                        # remove the extra field
                        parts.pop(submitter_idx + 1)
                        continue
                except IndexError:
                    # nope, that didn't work.
                    pass
                logging.error("Failed to fix line %s, skipping.", self._lineno)
        for i, val in enumerate(parts):
            entry[self._fields[i]] = val
        return entry

    next = __next__
# pylint: enable=too-few-public-methods
