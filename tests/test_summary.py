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


def test_weird_organism_name():
    ascii_file = open_testfile('weird_organism_name_summary.txt')
    reader = SummaryReader(ascii_file)
    first = next(reader)
    assert 'assembly_accession' in first
    assert 'ftp_path' in first


# stupid viral summary file has an extra comment
def test_virus():
    utf8_file = open_testfile('viral_summary.txt')
    reader = SummaryReader(utf8_file)
    entries = list(reader)
    first = entries[0]
    assert 'assembly_accession' in first
    assert 'ftp_path' in first
    assert len(entries) == 6
    for entry in entries:
        assert 'assembly_accession' in entry

    # entry should now be the last

# new bacterial file also has a different header format
def test_new_format():
    utf8_file = open_testfile('new_format_summary.txt')
    reader = SummaryReader(utf8_file)
    entries = list(reader)
    first = entries[0]
    assert 'assembly_accession' in first
