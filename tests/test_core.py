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


def test_download_entry():
    pass


def test_create_dir(tmpdir):
    entry = {'assembly_accession': 'FAKE0.1' }
    output = tmpdir.mkdir('output')
    ret = core.create_dir(entry, 'refseq', 'bacteria', str(output))

    expected = output.join('refseq', 'bacteria', 'FAKE0.1')
    assert expected.check()
    assert ret == str(expected)


def test_create_dir_exists(tmpdir):
    entry = {'assembly_accession': 'FAKE0.1' }
    output = tmpdir.mkdir('output')
    output.mkdir('refseq').mkdir('bacteria').mkdir('FAKE0.1')
    core.create_dir(entry, 'refseq', 'bacteria', str(output))


def test_create_dir_isfile(tmpdir):
    entry = {'assembly_accession': 'FAKE0.1' }
    output = tmpdir.mkdir('output')
    output.join('refseq', 'bacteria', 'FAKE0.1').write('foo', ensure=True)
    with pytest.raises(OSError):
        core.create_dir(entry, 'refseq', 'bacteria', str(output))


def test_grab_checksums_file(req):
    req.get('http://ftp.ncbi.nih.gov/genomes/all/FAKE0.1/md5checksums.txt', text='test')
    entry = {'ftp_url': 'ftp://ftp.ncbi.nih.gov/genomes/all/FAKE0.1' }
    ret = core.grab_checksums_file(entry)
    assert ret == 'test'


def test_parse_checksums():
    checksums_string = '''\
d3c2634cedd0efe05cbf8a5f5384d921  ./GCF_000009605.1_ASM960v1_feature_table.txt.gz
42c1bb1447aea2512a17aeb3645b55e9  ./GCF_000009605.1_ASM960v1_genomic.fna.gz
8a685d49d826c4f0ad05152e906f3250  ./GCF_000009605.1_ASM960v1_genomic.gbff.gz
e2d9e1cfa085cb462a73d3d2d2c22be5  ./GCF_000009605.1_ASM960v1_genomic.gff.gz
d8ce7c80d457e012f9d368a4673dea65  ./GCF_000009605.1_ASM960v1_protein.faa.gz
620a09de4286f66113317456c0dc8f66  ./GCF_000009605.1_ASM960v1_protein.gpff.gz
'''
    expected = [
        {'checksum': 'd3c2634cedd0efe05cbf8a5f5384d921', 'file': 'GCF_000009605.1_ASM960v1_feature_table.txt.gz'},
        {'checksum': '42c1bb1447aea2512a17aeb3645b55e9', 'file': 'GCF_000009605.1_ASM960v1_genomic.fna.gz'},
        {'checksum': '8a685d49d826c4f0ad05152e906f3250', 'file': 'GCF_000009605.1_ASM960v1_genomic.gbff.gz'},
        {'checksum': 'e2d9e1cfa085cb462a73d3d2d2c22be5', 'file': 'GCF_000009605.1_ASM960v1_genomic.gff.gz'},
        {'checksum': 'd8ce7c80d457e012f9d368a4673dea65', 'file': 'GCF_000009605.1_ASM960v1_protein.faa.gz'},
        {'checksum': '620a09de4286f66113317456c0dc8f66', 'file': 'GCF_000009605.1_ASM960v1_protein.gpff.gz'},
    ]

    ret = core.parse_checksums(checksums_string)
    assert ret == expected


def test_has_gbk_file_changed_no_file(tmpdir):
    checksums = [
        {'checksum': 'fake', 'file': 'skipped'},
        {'checksum': 'fake', 'file': 'fake_genomic.gbff.gz'},
    ]
    assert core.has_gbk_file_changed(str(tmpdir), checksums)


def test_has_gbk_file_changed(tmpdir):
    checksums = [
        {'checksum': 'fake', 'file': 'skipped'},
        {'checksum': 'fake', 'file': 'fake_genomic.gbff.gz'},
    ]
    fake_file = tmpdir.join(checksums[-1]['file'])
    fake_file.write('foo')
    assert fake_file.check()
    assert core.has_gbk_file_changed(str(tmpdir), checksums)


def test_has_gbk_file_changed_unchanged(tmpdir):
    fake_file = tmpdir.join('fake_genomic.gbff.gz')
    fake_file.write('foo')
    assert fake_file.check()
    checksum = core.md5sum(str(fake_file))

    checksums = [
        {'checksum': 'fake', 'file': 'skipped'},
        {'checksum': checksum, 'file': fake_file.basename},
    ]

    assert core.has_gbk_file_changed(str(tmpdir), checksums) == False


def test_md5sum():
    expected = '74d72df33d621f5eb6300dc9a2e06573'
    filename = _get_file('partial_summary.txt')
    ret = core.md5sum(filename)
    assert ret == expected


def test_download_gbk_file(req, tmpdir):
    entry = {'ftp_url': 'ftp://fake/path'}
    fake_file = tmpdir.join('fake_genomic.gbff.gz')
    fake_file.write('foo')
    assert fake_file.check()
    checksum = core.md5sum(str(fake_file))
    checksums = [{'checksum': checksum, 'file': fake_file.basename}]
    dl_dir = tmpdir.mkdir('download')
    req.get('http://fake/path/fake_genomic.gbff.gz', text=fake_file.read())


    assert core.download_gbk_file(entry, str(dl_dir), checksums)


def test_download_gbk_file_mismatch(req, tmpdir):
    entry = {'ftp_url': 'ftp://fake/path'}
    fake_file = tmpdir.join('fake_genomic.gbff.gz')
    fake_file.write('foo')
    assert fake_file.check()
    checksums = [{'checksum': 'fake', 'file': fake_file.basename}]
    dl_dir = tmpdir.mkdir('download')
    req.get('http://fake/path/fake_genomic.gbff.gz', text=fake_file.read())


    assert core.download_gbk_file(entry, str(dl_dir), checksums) == False
