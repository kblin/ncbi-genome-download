import pytest
import requests_mock
from argparse import Namespace
from os import path

from ncbi_genome_download import core


def _get_file(fname):
    '''Get a file from the test directory'''
    return path.join(path.dirname(__file__), fname)


@pytest.yield_fixture
def req():
    with requests_mock.mock() as req:
        yield req


def test_download_one(monkeypatch, mocker):
    _download_mock = mocker.MagicMock()
    monkeypatch.setattr(core, '_download', _download_mock)
    fake_args = Namespace(section='refseq', domain='bacteria', uri=core.NCBI_URI,
                          output='/tmp/fake')
    core.download(fake_args)
    _download_mock.assert_called_with('refseq', 'bacteria', core.NCBI_URI, '/tmp/fake')


def test_download_all(monkeypatch, mocker):
    _download_mock = mocker.MagicMock()
    monkeypatch.setattr(core, '_download', _download_mock)
    fake_args = Namespace(section='refseq', domain='all', uri=core.NCBI_URI, output='/tmp/fake')
    core.download(fake_args)
    assert _download_mock.call_count == len(core.supported_domains)


def test__download(monkeypatch, mocker, req):
    summary_contents = open(_get_file('partial_summary.txt'), 'r').read()
    req.get('http://ftp.ncbi.nih.gov/genomes/refseq/bacteria/assembly_summary.txt',
            text=summary_contents)
    mocker.spy(core, 'get_summary')
    mocker.spy(core, 'parse_summary')
    mocker.patch('ncbi_genome_download.core.download_entry')
    core._download('refseq', 'bacteria', core.NCBI_URI, '/tmp/fake')
    assert core.get_summary.call_count == 1
    assert core.parse_summary.call_count == 1
    assert core.download_entry.call_count == 4


def test_get_summary(req):
    req.get('http://ftp.ncbi.nih.gov/genomes/refseq/bacteria/assembly_summary.txt', text='test')
    ret = core.get_summary('refseq', 'bacteria', core.NCBI_URI)
    assert ret.read() == 'test'


def test_parse_summary():
    with open(_get_file('partial_summary.txt'), 'r') as fh:
        reader = core.parse_summary(fh)
        first = reader.next()
        assert first.has_key('ftp_path')
        assert first.has_key('assembly_accession')

        fh.seek(2)
        reader = core.parse_summary(fh)
        first = reader.next()
        assert first.has_key('assembly_accession')
