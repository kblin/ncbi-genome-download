import codecs
from os import path

from ncbi_genome_download.summary import SummaryReader


def open_testfile(fname):
    return codecs.open(path.join(path.dirname(__file__), fname), 'r', 'utf-8')


def test_bacteria_ascii():
    ascii_file = open_testfile('partial_summary.txt')
    reader = SummaryReader(ascii_file)
    first = next(reader)
    assert 'assembly_accession' in first
    assert 'ftp_path' in first


def test_bacteria_unicode():
    utf8_file = open_testfile('noascii_summary.txt')
    reader = SummaryReader(utf8_file)
    first = next(reader)
    assert 'assembly_accession' in first
    assert 'ftp_path' in first


# stupid viral summary file has an extra comment
def test_virus():
    utf8_file = open_testfile('viral_summary.txt')
    reader = SummaryReader(utf8_file)
    first = next(reader)
    assert 'assembly_accession' in first
    assert 'ftp_path' in first
