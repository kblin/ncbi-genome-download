"""Core module tests."""

from argparse import Namespace
from collections import OrderedDict
import os
from os import path

import pytest
import requests_mock
from requests.exceptions import ConnectionError

from ncbi_genome_download import core
from ncbi_genome_download import NgdConfig, SUPPORTED_TAXONOMIC_GROUPS


def _get_file(fname):
    """Get a file from the test directory."""
    return path.join(path.dirname(__file__), fname)


@pytest.yield_fixture
def req():
    """Fake requests object."""
    with requests_mock.mock() as req:
        yield req


def test_download_defaults(monkeypatch, mocker):
    """Test download does the right thing."""
    entry = {
        'assembly_accession': 'FAKE0.1',
        'organism_name': 'Example species',
        'infraspecific_name': 'strain=ABC 1234',
        'ftp_path': 'https://fake/genomes/FAKE0.1'
    }
    worker_mock = mocker.MagicMock()
    select_candidates_mock = mocker.MagicMock(return_value=[(entry, 'bacteria')])
    create_downloadjob_mock = mocker.MagicMock(return_value=[core.DownloadJob(None, None, None, None)])
    monkeypatch.setattr(core, 'select_candidates', select_candidates_mock)
    monkeypatch.setattr(core, 'create_downloadjob', create_downloadjob_mock)
    monkeypatch.setattr(core, 'worker', worker_mock)
    assert core.download() == 0
    assert select_candidates_mock.call_args_list[0][0][0].group == SUPPORTED_TAXONOMIC_GROUPS
    assert create_downloadjob_mock.call_args_list[0][0][0] == entry


def test_args_download_defaults(monkeypatch, mocker):
    """Test args_download does the correct thing."""
    entry = {
        'assembly_accession': 'FAKE0.1',
        'organism_name': 'Example species',
        'infraspecific_name': 'strain=ABC 1234',
        'ftp_path': 'https://fake/genomes/FAKE0.1'
    }
    worker_mock = mocker.MagicMock()
    select_candidates_mock = mocker.MagicMock(return_value=[(entry, 'bacteria')])
    create_downloadjob_mock = mocker.MagicMock(return_value=[core.DownloadJob(None, None, None, None)])
    monkeypatch.setattr(core, 'select_candidates', select_candidates_mock)
    monkeypatch.setattr(core, 'create_downloadjob', create_downloadjob_mock)
    monkeypatch.setattr(core, 'worker', worker_mock)
    assert core.args_download(Namespace()) == 0
    assert select_candidates_mock.call_args_list[0][0][0].group == SUPPORTED_TAXONOMIC_GROUPS
    assert create_downloadjob_mock.call_args_list[0][0][0] == entry


def test_download_defaults_nomatch(monkeypatch, mocker):
    """Test download bails with a 1 return code if no entries match."""
    select_candidates_mock = mocker.MagicMock(return_value=[])
    monkeypatch.setattr(core, 'select_candidates', select_candidates_mock)
    assert core.download() == 1


def test_download_dry_run(monkeypatch, mocker):
    """Test _download is not called for a dry run."""
    entry = {
        'assembly_accession': 'FAKE0.1',
        'organism_name': 'Example species',
        'infraspecific_name': 'strain=ABC 1234',
        'ftp_path': 'https://fake/genomes/FAKE0.1'
    }
    worker_mock = mocker.MagicMock()
    select_candidates_mock = mocker.MagicMock(return_value=[(entry, 'bacteria')])
    create_downloadjob_mock = mocker.MagicMock(return_value=[core.DownloadJob(None, None, None, None)])
    monkeypatch.setattr(core, 'select_candidates', select_candidates_mock)
    monkeypatch.setattr(core, 'create_downloadjob', create_downloadjob_mock)
    monkeypatch.setattr(core, 'worker', worker_mock)
    assert core.download(dry_run=True) == 0
    assert select_candidates_mock.call_count == 1
    assert create_downloadjob_mock.call_count == 0
    assert worker_mock.call_count == 0


def test_download_one(monkeypatch, mocker):
    download_mock = mocker.MagicMock()
    monkeypatch.setattr(core, 'download', download_mock)
    kwargs = {'group': 'bacteria', 'output': '/tmp/fake'}
    core.download(**kwargs)
    download_mock.assert_called_with(**kwargs)


def test_download_connection_err(monkeypatch, mocker):
    select_candidates_mock = mocker.MagicMock(side_effect=ConnectionError)
    monkeypatch.setattr(core, 'select_candidates', select_candidates_mock)
    assert core.download() == 75


def test_download(monkeypatch, mocker, req):
    summary_contents = open(_get_file('partial_summary.txt'), 'r').read()
    req.get('https://ftp.ncbi.nih.gov/genomes/refseq/bacteria/assembly_summary.txt',
            text=summary_contents)
    mocker.spy(core, 'get_summary')
    mocker.spy(core, 'parse_summary')
    mocker.patch('ncbi_genome_download.core.create_downloadjob')
    core.download(group='bacteria', output='/tmp/fake')
    assert core.get_summary.call_count == 1
    assert core.parse_summary.call_count == 1
    assert core.create_downloadjob.call_count == 4


def test_download_metadata(monkeypatch, mocker, req, tmpdir):
    """Test creating the metadata file works."""
    metadata_file = tmpdir.join('metadata.tsv')
    summary_contents = open(_get_file('partial_summary.txt'), 'r').read()
    req.get('https://ftp.ncbi.nih.gov/genomes/refseq/bacteria/assembly_summary.txt',
            text=summary_contents)
    mocker.spy(core, 'get_summary')
    mocker.spy(core, 'parse_summary')
    mocker.patch('ncbi_genome_download.core.create_downloadjob', return_value=[core.DownloadJob(None, None, None, None)])
    core.download(group='bacteria', output='/tmp/fake', metadata_table=str(metadata_file))
    assert core.get_summary.call_count == 1
    assert core.parse_summary.call_count == 1
    assert core.create_downloadjob.call_count == 4
    assert metadata_file.check()


def test_download_complete(monkeypatch, mocker, req):
    summary_contents = open(_get_file('assembly_status.txt'), 'r').read()
    req.get('https://ftp.ncbi.nih.gov/genomes/refseq/bacteria/assembly_summary.txt',
            text=summary_contents)
    mocker.spy(core, 'get_summary')
    mocker.spy(core, 'parse_summary')
    mocker.patch('ncbi_genome_download.core.create_downloadjob')
    core.download(group='bacteria', output='/tmp/fake', assembly_level='complete')
    assert core.get_summary.call_count == 1
    assert core.parse_summary.call_count == 1
    assert core.create_downloadjob.call_count == 1
    # Many nested tuples in call_args_list, no kidding.
    assert core.create_downloadjob.call_args_list[0][0][0]['assembly_level'] == 'Complete Genome'


def test_download_chromosome(monkeypatch, mocker, req):
    summary_contents = open(_get_file('assembly_status.txt'), 'r').read()
    req.get('https://ftp.ncbi.nih.gov/genomes/refseq/bacteria/assembly_summary.txt',
            text=summary_contents)
    mocker.spy(core, 'get_summary')
    mocker.spy(core, 'parse_summary')
    mocker.patch('ncbi_genome_download.core.create_downloadjob')
    core.download(group='bacteria', output='/tmp/fake', assembly_level='chromosome')
    assert core.get_summary.call_count == 1
    assert core.parse_summary.call_count == 1
    assert core.create_downloadjob.call_count == 1
    # Many nested tuples in call_args_list, no kidding.
    assert core.create_downloadjob.call_args_list[0][0][0]['assembly_level'] == 'Chromosome'


def test_download_scaffold(monkeypatch, mocker, req):
    summary_contents = open(_get_file('assembly_status.txt'), 'r').read()
    req.get('https://ftp.ncbi.nih.gov/genomes/refseq/bacteria/assembly_summary.txt',
            text=summary_contents)
    mocker.spy(core, 'get_summary')
    mocker.spy(core, 'parse_summary')
    mocker.patch('ncbi_genome_download.core.create_downloadjob')
    core.download(group='bacteria', output='/tmp/fake', assembly_level='scaffold')
    assert core.get_summary.call_count == 1
    assert core.parse_summary.call_count == 1
    assert core.create_downloadjob.call_count == 1
    # Many nested tuples in call_args_list, no kidding.
    assert core.create_downloadjob.call_args_list[0][0][0]['assembly_level'] == 'Scaffold'


def test_download_contig(monkeypatch, mocker, req):
    summary_contents = open(_get_file('assembly_status.txt'), 'r').read()
    req.get('https://ftp.ncbi.nih.gov/genomes/refseq/bacteria/assembly_summary.txt',
            text=summary_contents)
    mocker.spy(core, 'get_summary')
    mocker.spy(core, 'parse_summary')
    mocker.patch('ncbi_genome_download.core.create_downloadjob')
    core.download(group='bacteria', output='/tmp/fake', assembly_level='contig')
    assert core.get_summary.call_count == 1
    assert core.parse_summary.call_count == 1
    assert core.create_downloadjob.call_count == 1
    # Many nested tuples in call_args_list, no kidding.
    assert core.create_downloadjob.call_args_list[0][0][0]['assembly_level'] == 'Contig'


def test_download_genus(monkeypatch, mocker, req):
    summary_contents = open(_get_file('partial_summary.txt'), 'r').read()
    req.get('https://ftp.ncbi.nih.gov/genomes/refseq/bacteria/assembly_summary.txt',
            text=summary_contents)
    mocker.spy(core, 'get_summary')
    mocker.spy(core, 'parse_summary')
    mocker.patch('ncbi_genome_download.core.create_downloadjob')
    core.download(group='bacteria', output='/tmp/fake', genus='Azorhizobium')
    assert core.get_summary.call_count == 1
    assert core.parse_summary.call_count == 1
    assert core.create_downloadjob.call_count == 1
    # Many nested tuples in call_args_list, no kidding.
    assert core.create_downloadjob.call_args_list[0][0][0][
               'organism_name'] == 'Azorhizobium caulinodans ORS 571'


def test_download_genus_lowercase(monkeypatch, mocker, req):
    summary_contents = open(_get_file('partial_summary.txt'), 'r').read()
    req.get('https://ftp.ncbi.nih.gov/genomes/refseq/bacteria/assembly_summary.txt',
            text=summary_contents)
    mocker.spy(core, 'get_summary')
    mocker.spy(core, 'parse_summary')
    mocker.patch('ncbi_genome_download.core.create_downloadjob')
    core.download(group='bacteria', output='/tmp/fake', genus='azorhizobium')
    assert core.get_summary.call_count == 1
    assert core.parse_summary.call_count == 1
    assert core.create_downloadjob.call_count == 1
    # Many nested tuples in call_args_list, no kidding.
    assert core.create_downloadjob.call_args_list[0][0][0][
               'organism_name'] == 'Azorhizobium caulinodans ORS 571'


def test_download_genus_fuzzy(monkeypatch, mocker, req):
    summary_contents = open(_get_file('partial_summary.txt'), 'r').read()
    req.get('https://ftp.ncbi.nih.gov/genomes/refseq/bacteria/assembly_summary.txt',
            text=summary_contents)
    mocker.spy(core, 'get_summary')
    mocker.spy(core, 'parse_summary')
    mocker.patch('ncbi_genome_download.core.create_downloadjob')
    core.download(group='bacteria', output='/tmp/fake', genus='ors', fuzzy_genus=True)
    assert core.get_summary.call_count == 1
    assert core.parse_summary.call_count == 1
    assert core.create_downloadjob.call_count == 1
    # Many nested tuples in call_args_list, no kidding.
    assert core.create_downloadjob.call_args_list[0][0][0][
               'organism_name'] == 'Azorhizobium caulinodans ORS 571'


def test_download_taxid(monkeypatch, mocker, req):
    summary_contents = open(_get_file('partial_summary.txt'), 'r').read()
    req.get('https://ftp.ncbi.nih.gov/genomes/refseq/bacteria/assembly_summary.txt',
            text=summary_contents)
    mocker.spy(core, 'get_summary')
    mocker.spy(core, 'parse_summary')
    mocker.patch('ncbi_genome_download.core.create_downloadjob')
    core.download(group='bacteria', output='/tmp/fake', taxid='438753')
    assert core.get_summary.call_count == 1
    assert core.parse_summary.call_count == 1
    assert core.create_downloadjob.call_count == 1
    # Many nested tuples in call_args_list, no kidding.
    assert core.create_downloadjob.call_args_list[0][0][0][
               'organism_name'] == 'Azorhizobium caulinodans ORS 571'


def test_download_species_taxid(monkeypatch, mocker, req):
    summary_contents = open(_get_file('partial_summary.txt'), 'r').read()
    req.get('https://ftp.ncbi.nih.gov/genomes/refseq/bacteria/assembly_summary.txt',
            text=summary_contents)
    mocker.spy(core, 'get_summary')
    mocker.spy(core, 'parse_summary')
    mocker.patch('ncbi_genome_download.core.create_downloadjob')
    core.download(group='bacteria', output='/tmp/fake', species_taxid='7')
    assert core.get_summary.call_count == 1
    assert core.parse_summary.call_count == 1
    assert core.create_downloadjob.call_count == 1
    # Many nested tuples in call_args_list, no kidding.
    assert core.create_downloadjob.call_args_list[0][0][0][
               'organism_name'] == 'Azorhizobium caulinodans ORS 571'


def test_download_refseq_category(monkeypatch, mocker, req):
    summary_contents = open(_get_file('assembly_status.txt'), 'r').read()
    req.get('https://ftp.ncbi.nih.gov/genomes/refseq/bacteria/assembly_summary.txt',
            text=summary_contents)
    mocker.spy(core, 'get_summary')
    mocker.spy(core, 'parse_summary')
    mocker.patch('ncbi_genome_download.core.create_downloadjob')
    core.download(group='bacteria', output='/tmp/fake', refseq_category='reference')
    assert core.get_summary.call_count == 1
    assert core.parse_summary.call_count == 1
    assert core.create_downloadjob.call_count == 1
    # Many nested tuples in call_args_list, no kidding.
    assert core.create_downloadjob.call_args_list[0][0][0][
               'organism_name'] == 'Streptomyces coelicolor A3(2)'


def test_download_type_material(monkeypatch, mocker, req):
    summary_contents = open(_get_file('type_material.txt'), 'r').read()
    req.get('https://ftp.ncbi.nih.gov/genomes/refseq/bacteria/assembly_summary.txt',
            text=summary_contents)
    print(summary_contents)
    mocker.spy(core, 'get_summary')
    mocker.spy(core, 'parse_summary')
    mocker.patch('ncbi_genome_download.core.create_downloadjob')
    core.download(group='bacteria', output='/tmp/fake', type_material=["all"])
    assert core.get_summary.call_count == 1
    assert core.parse_summary.call_count == 1
    assert core.create_downloadjob.call_count == 1
    # Many nested tuples in call_args_list, no kidding.
    assert core.create_downloadjob.call_args_list[0][0][0][
               'organism_name'] == 'Myxococcus fulvus'


def test_download_type_material_no_match(monkeypatch, mocker, req):
    summary_contents = open(_get_file('type_material.txt'), 'r').read()
    req.get('https://ftp.ncbi.nih.gov/genomes/refseq/bacteria/assembly_summary.txt',
            text=summary_contents)
    print(summary_contents)
    mocker.spy(core, 'get_summary')
    mocker.spy(core, 'parse_summary')
    mocker.patch('ncbi_genome_download.core.create_downloadjob')
    core.download(group='bacteria', output='/tmp/fake', type_material=["neotype"])
    assert core.get_summary.call_count == 1
    assert core.parse_summary.call_count == 1
    assert core.create_downloadjob.call_count == 0


def test_get_summary(monkeypatch, req, tmpdir):
    """Test getting the assembly summary file."""
    cache_dir = tmpdir.mkdir('cache')
    monkeypatch.setattr(core, 'CACHE_DIR', str(cache_dir))
    cache_file = cache_dir.join('refseq_bacteria_assembly_summary.txt')
    req.get('https://ftp.ncbi.nih.gov/genomes/refseq/bacteria/assembly_summary.txt', text='test')

    ret = core.get_summary('refseq', 'bacteria', NgdConfig.get_default('uri'), False)
    assert ret.read() == 'test'
    assert not cache_file.check()

    ret = core.get_summary('refseq', 'bacteria', NgdConfig.get_default('uri'), True)
    assert ret.read() == 'test'
    assert cache_file.check()

    req.get('https://ftp.ncbi.nih.gov/genomes/refseq/bacteria/assembly_summary.txt', text='never read')
    ret = core.get_summary('refseq', 'bacteria', NgdConfig.get_default('uri'), True)
    assert ret.read() == 'test'


def test_get_summary_error_handling(monkeypatch, mocker, req, tmpdir):
    """Test get_summary error handling."""
    cache_dir = tmpdir.join('cache')
    monkeypatch.setattr(core, 'CACHE_DIR', str(cache_dir))
    req.get('https://ftp.ncbi.nih.gov/genomes/refseq/bacteria/assembly_summary.txt', text='test')

    fake_makedirs = mocker.MagicMock(side_effect=OSError(13, "Permission denied"))
    monkeypatch.setattr(os, 'makedirs', fake_makedirs)
    with pytest.raises(OSError):
        core.get_summary('refseq', 'bacteria', NgdConfig.get_default('uri'), True)


def test_parse_summary():
    with open(_get_file('partial_summary.txt'), 'r') as fh:
        reader = core.parse_summary(fh)
        first = next(reader)
        assert 'ftp_path' in first
        assert 'assembly_accession' in first

        fh.seek(2)
        reader = core.parse_summary(fh)
        first = next(reader)
        assert 'assembly_accession' in first


def test_filter_entries():
    """Test filter_entries."""
    config = NgdConfig()
    with open(_get_file('assembly_status.txt'), 'r') as fh:
        entries = list(core.parse_summary(fh))

    assert core.filter_entries(entries, config) == entries

    expected = entries[-1:]
    config.assembly_accessions = "GCF_000203835.1"

    assert core.filter_entries(entries, config) == expected


def prepare_create_downloadjob(req, tmpdir, format_map=NgdConfig._FORMATS, human_readable=False,
                               create_local_file=False):
    # Set up test env
    entry = {
        'assembly_accession': 'FAKE0.1',
        'organism_name': 'Example species',
        'infraspecific_name': 'strain=ABC 1234',
        'ftp_path': 'https://fake/genomes/FAKE0.1'
    }

    config = NgdConfig()

    outdir = tmpdir.mkdir('output')
    download_jobs = []
    config.output = str(outdir)
    config.human_readable = human_readable

    checksum_file_content = ''
    for key, val in format_map.items():
        seqfile = tmpdir.join('fake{}'.format(val))
        seqfile.write(key)

        checksum = core.md5sum(str(seqfile))
        filename = path.basename(str(seqfile))
        full_url = 'https://fake/genomes/FAKE0.1/{}'.format(filename)
        local_file = outdir.join('refseq', 'bacteria', 'FAKE0.1', filename)
        if create_local_file:
            local_file.write(seqfile.read(), ensure=True)

        symlink_path = None
        if human_readable:
            symlink_path = str(
                outdir.join('human_readable', 'refseq', 'bacteria', 'Example', 'species',
                            'ABC_1234', filename))

        download_jobs.append(core.DownloadJob(full_url, str(local_file), checksum, symlink_path))
        checksum_file_content += '{}\t./{}\n'.format(checksum, filename)
        req.get(full_url, text=seqfile.read())

    req.get('https://fake/genomes/FAKE0.1/md5checksums.txt', text=checksum_file_content)

    return entry, config, download_jobs


def test_create_downloadjob_genbank(req, tmpdir):
    entry, config, joblist = prepare_create_downloadjob(req, tmpdir)
    jobs = core.create_downloadjob(entry, 'bacteria', config)
    expected = [j for j in joblist if j.local_file.endswith('_genomic.gbff.gz')]
    assert jobs == expected


def test_create_downloadjob_all(req, tmpdir):
    entry, config, expected = prepare_create_downloadjob(req, tmpdir)
    config.file_format = "all"
    jobs = core.create_downloadjob(entry, 'bacteria', config)
    assert jobs == expected


def test_create_downloadjob_missing(req, tmpdir):
    name_map_copy = OrderedDict(NgdConfig._FORMATS)
    del name_map_copy['genbank']
    entry, config, _ = prepare_create_downloadjob(req, tmpdir, name_map_copy)
    jobs = core.create_downloadjob(entry, 'bacteria', config)
    assert jobs == []


def test_create_downloadjob_human_readable(req, tmpdir):
    entry, config, joblist = prepare_create_downloadjob(req, tmpdir, human_readable=True)
    jobs = core.create_downloadjob(entry, 'bacteria', config)
    expected = [j for j in joblist if j.local_file.endswith('_genomic.gbff.gz')]
    assert jobs == expected


def test_create_downloadjob_symlink_only(req, tmpdir):
    entry, config, joblist = prepare_create_downloadjob(req, tmpdir, human_readable=True,
                                                        create_local_file=True)
    jobs = core.create_downloadjob(entry, 'bacteria', config)
    expected = [core.DownloadJob(None, j.local_file, None, j.symlink_path)
                for j in joblist if j.local_file.endswith('_genomic.gbff.gz')]
    assert jobs == expected


def test_create_dir(tmpdir):
    entry = {'assembly_accession': 'FAKE0.1'}
    output = tmpdir.mkdir('output')
    ret = core.create_dir(entry, 'refseq', 'bacteria', str(output), flat_output=False)

    expected = output.join('refseq', 'bacteria', 'FAKE0.1')
    assert expected.check()
    assert ret == str(expected)


def test_create_dir_exists(tmpdir):
    entry = {'assembly_accession': 'FAKE0.1'}
    output = tmpdir.mkdir('output')
    expected = output.mkdir('refseq').mkdir('bacteria').mkdir('FAKE0.1')
    ret = core.create_dir(entry, 'refseq', 'bacteria', str(output), flat_output=False)
    assert ret == str(expected)


def test_create_dir_isfile(tmpdir):
    entry = {'assembly_accession': 'FAKE0.1'}
    output = tmpdir.mkdir('output')
    output.join('refseq', 'bacteria', 'FAKE0.1').write('foo', ensure=True)
    with pytest.raises(OSError):
        core.create_dir(entry, 'refseq', 'bacteria', str(output), flat_output=False)


def test_create_dir_flat(tmpdir):
    entry = {'assembly_accession': 'FAKE0.1'}
    output = tmpdir.mkdir('output')
    ret = core.create_dir(entry, 'refseq', 'bacteria', str(output), flat_output=True)

    assert ret == str(output)


def test_create_readable_dir(tmpdir):
    entry = {'organism_name': 'Example species', 'infraspecific_name': 'strain=ABC 1234'}
    output = tmpdir.mkdir('output')
    ret = core.create_readable_dir(entry, 'refseq', 'bacteria', str(output))

    expected = output.join('human_readable', 'refseq', 'bacteria', 'Example', 'species',
                           'ABC_1234')
    assert expected.check()
    assert ret == str(expected)


def test_create_readable_dir_exists(tmpdir):
    entry = {'organism_name': 'Example species', 'infraspecific_name': 'strain=ABC 1234'}
    output = tmpdir.mkdir('output')
    expected = output.mkdir('human_readable').mkdir('refseq').mkdir('bacteria').mkdir(
        'Example').mkdir('species').mkdir('ABC_1234')
    ret = core.create_readable_dir(entry, 'refseq', 'bacteria', str(output))
    assert ret == str(expected)


def test_create_readable_dir_isfile(tmpdir):
    entry = {'organism_name': 'Example species', 'infraspecific_name': 'strain=ABC 1234'}
    output = tmpdir.mkdir('output')
    output.join('human_readable', 'refseq', 'bacteria', 'Example', 'species', 'ABC_1234').write(
        'foo', ensure=True)
    with pytest.raises(OSError):
        core.create_readable_dir(entry, 'refseq', 'bacteria', str(output))


def test_create_readable_dir_virus(tmpdir):
    output = tmpdir.mkdir('output')
    entry = {'organism_name': 'OnlyOneString-1', 'infraspecific_name': 'strain=ABC 1234'}
    ret = core.create_readable_dir(entry, 'refseq', 'viral', str(output))

    expected = output.join('human_readable', 'refseq', 'viral', 'OnlyOneString-1', 'ABC_1234')
    assert expected.check()
    assert ret == str(expected)

    entry = {'organism_name': 'Two strings', 'infraspecific_name': 'strain=ABC 1234'}
    ret = core.create_readable_dir(entry, 'refseq', 'viral', str(output))

    expected = output.join('human_readable', 'refseq', 'viral', 'Two_strings', 'ABC_1234')
    assert expected.check()
    assert ret == str(expected)

    entry = {'organism_name': 'This is four strings', 'infraspecific_name': 'strain=ABC 1234'}
    ret = core.create_readable_dir(entry, 'refseq', 'viral', str(output))

    expected = output.join('human_readable', 'refseq', 'viral', 'This_is_four_strings', 'ABC_1234')
    assert expected.check()
    assert ret == str(expected)

    entry = {'organism_name': 'This is four strings', 'infraspecific_name': '',
             'isolate': '', 'assembly_accession': 'ABC12345'}
    ret = core.create_readable_dir(entry, 'refseq', 'viral', str(output))

    expected = output.join('human_readable', 'refseq', 'viral', 'This_is_four_strings', 'ABC12345')
    assert expected.check()
    assert ret == str(expected)


def test_grab_checksums_file(req):
    req.get('https://ftp.ncbi.nih.gov/genomes/all/FAKE0.1/md5checksums.txt', text='test')
    entry = {'ftp_path': 'ftp://ftp.ncbi.nih.gov/genomes/all/FAKE0.1'}
    ret = core.grab_checksums_file(entry)
    assert ret == 'test'


def test_parse_checksums():
    checksums_string = """\
d3c2634cedd0efe05cbf8a5f5384d921  ./GCF_000009605.1_ASM960v1_feature_table.txt.gz
42c1bb1447aea2512a17aeb3645b55e9  ./GCF_000009605.1_ASM960v1_genomic.fna.gz
8a685d49d826c4f0ad05152e906f3250  ./GCF_000009605.1_ASM960v1_genomic.gbff.gz
e2d9e1cfa085cb462a73d3d2d2c22be5  ./GCF_000009605.1_ASM960v1_genomic.gff.gz
d8ce7c80d457e012f9d368a4673dea65  ./GCF_000009605.1_ASM960v1_protein.faa.gz
This_is_totally_an_invalid_line!
620a09de4286f66113317456c0dc8f66  ./GCF_000009605.1_ASM960v1_protein.gpff.gz
"""
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


def test_has_file_changed_no_file(tmpdir):
    checksums = [
        {'checksum': 'fake', 'file': 'skipped'},
        {'checksum': 'fake', 'file': 'fake_genomic.gbff.gz'},
    ]
    assert core.has_file_changed(str(tmpdir), checksums)


def test_has_file_changed(tmpdir):
    checksums = [
        {'checksum': 'fake', 'file': 'skipped'},
        {'checksum': 'fake', 'file': 'fake_genomic.gbff.gz'},
    ]
    fake_file = tmpdir.join(checksums[-1]['file'])
    fake_file.write('foo')
    assert fake_file.check()
    assert core.has_file_changed(str(tmpdir), checksums)


def test_has_file_changed_unchanged(tmpdir):
    fake_file = tmpdir.join('fake_genomic.gbff.gz')
    fake_file.write('foo')
    assert fake_file.check()
    checksum = core.md5sum(str(fake_file))

    checksums = [
        {'checksum': 'fake', 'file': 'skipped'},
        {'checksum': checksum, 'file': fake_file.basename},
    ]

    assert core.has_file_changed(str(tmpdir), checksums) is False


def test_need_to_create_symlink_no_symlink(tmpdir):
    checksums = [
        {'checksum': 'fake', 'file': 'skipped'},
        {'checksum': 'fake', 'file': 'fake_genomic.gbff.gz'},
    ]
    assert core.need_to_create_symlink(str(tmpdir), checksums, 'genbank', None) is False


def test_need_to_create_symlink_correct_link(tmpdir):
    fake_file = tmpdir.join('fake_genomic.gbff.gz')
    fake_file.write('foo')
    assert fake_file.check()
    checksum = core.md5sum(str(fake_file))
    human_readable_dir = tmpdir.mkdir('human_readable')
    fake_link = human_readable_dir.join('fake_genomic.gbff.gz')
    fake_link.mksymlinkto(str(fake_file))

    checksums = [
        {'checksum': 'fake', 'file': 'skipped'},
        {'checksum': checksum, 'file': fake_file.basename},
    ]

    assert core.need_to_create_symlink(str(tmpdir), checksums, 'genbank',
                                       str(human_readable_dir)) is False


def test_need_to_create_symlink(tmpdir):
    fake_file = tmpdir.join('fake_genomic.gbff.gz')
    fake_file.write('foo')
    assert fake_file.check()
    checksum = core.md5sum(str(fake_file))
    human_readable_dir = tmpdir.mkdir('human_readable')

    checksums = [
        {'checksum': 'fake', 'file': 'skipped'},
        {'checksum': checksum, 'file': fake_file.basename},
    ]

    assert core.need_to_create_symlink(str(tmpdir), checksums, 'genbank', str(human_readable_dir))


def test_md5sum():
    expected = '74d72df33d621f5eb6300dc9a2e06573'
    filename = _get_file('partial_summary.txt')
    ret = core.md5sum(filename)
    assert ret == expected


def test_download_file_genbank(req, tmpdir):
    entry = {'ftp_path': 'ftp://fake/path'}
    fake_file = tmpdir.join('fake_genomic.gbff.gz')
    fake_file.write('foo')
    assert fake_file.check()
    checksum = core.md5sum(str(fake_file))
    checksums = [{'checksum': checksum, 'file': fake_file.basename}]
    dl_dir = tmpdir.mkdir('download')
    req.get('https://fake/path/fake_genomic.gbff.gz', text=fake_file.read())

    assert core.worker(core.download_file_job(entry, str(dl_dir), checksums))


def test_download_file_genbank_mismatch(req, tmpdir):
    entry = {'ftp_path': 'ftp://fake/path'}
    fake_file = tmpdir.join('fake_genomic.gbff.gz')
    fake_file.write('foo')
    assert fake_file.check()
    checksums = [{'checksum': 'fake', 'file': fake_file.basename}]
    dl_dir = tmpdir.mkdir('download')
    req.get('https://fake/path/fake_genomic.gbff.gz', text=fake_file.read())

    assert core.worker(core.download_file_job(entry, str(dl_dir), checksums)) is False


def test_download_file_fasta(req, tmpdir):
    entry = {'ftp_path': 'ftp://fake/path'}
    bogus_file = tmpdir.join('fake_cds_from_genomic.fna.gz')
    bogus_file.write("we don't want this one")
    bogus_checksum = core.md5sum(str(bogus_file))
    fake_file = tmpdir.join('fake_genomic.fna.gz')
    fake_file.write('foo')
    assert fake_file.check()
    checksum = core.md5sum(str(fake_file))
    checksums = [
        {'checksum': bogus_checksum, 'file': bogus_file.basename},
        {'checksum': checksum, 'file': fake_file.basename},
    ]
    dl_dir = tmpdir.mkdir('download')
    req.get('https://fake/path/fake_genomic.fna.gz', text=fake_file.read())

    assert core.worker(core.download_file_job(entry, str(dl_dir), checksums, 'fasta'))


def test_download_file_cds_fasta(req, tmpdir):
    entry = {'ftp_path': 'ftp://fake/path'}
    fake_file = tmpdir.join('fake_cds_from_genomic.fna.gz')
    fake_file.write('foo')
    assert fake_file.check()
    checksum = core.md5sum(str(fake_file))
    checksums = [
        {'checksum': checksum, 'file': fake_file.basename},
    ]
    dl_dir = tmpdir.mkdir('download')
    req.get('https://fake/path/fake_cds_from_genomic.fna.gz', text=fake_file.read())

    assert core.worker(core.download_file_job(entry, str(dl_dir), checksums, 'cds-fasta'))


def test_download_file_rna_fasta(req, tmpdir):
    entry = {'ftp_path': 'ftp://fake/path'}
    fake_file = tmpdir.join('fake_rna_from_genomic.fna.gz')
    fake_file.write('foo')
    assert fake_file.check()
    checksum = core.md5sum(str(fake_file))
    checksums = [
        {'checksum': checksum, 'file': fake_file.basename},
    ]
    dl_dir = tmpdir.mkdir('download')
    req.get('https://fake/path/fake_rna_from_genomic.fna.gz', text=fake_file.read())

    assert core.worker(core.download_file_job(entry, str(dl_dir), checksums, 'rna-fasta'))


def test_download_file_rna_fna(req, tmpdir):
    entry = {'ftp_path': 'ftp://fake/path'}
    fake_file = tmpdir.join('fake_rna.fna.gz')
    fake_file.write('foo')
    assert fake_file.check()
    checksum = core.md5sum(str(fake_file))
    checksums = [{'checksum': checksum, 'file': fake_file.basename}]
    dl_dir = tmpdir.mkdir('download')
    req.get('https://fake/path/fake_rna.fna.gz', text=fake_file.read())

    assert core.worker(core.download_file_job(entry, str(dl_dir), checksums, 'rna-fna'))


def test_download_file_rm_out(req, tmpdir):
    entry = {'ftp_path': 'ftp://fake/path'}
    fake_file = tmpdir.join('fake_rm.out.gz')
    fake_file.write('foo')
    assert fake_file.check()
    checksum = core.md5sum(str(fake_file))
    checksums = [{'checksum': checksum, 'file': fake_file.basename}]
    dl_dir = tmpdir.mkdir('download')
    req.get('https://fake/path/fake_rm.out.gz', text=fake_file.read())

    assert core.worker(core.download_file_job(entry, str(dl_dir), checksums, 'rm'))


def test_download_file_symlink_path(req, tmpdir):
    entry = {'ftp_path': 'ftp://fake/path'}
    fake_file = tmpdir.join('fake_genomic.gbff.gz')
    fake_file.write('foo')
    assert fake_file.check()
    checksum = core.md5sum(str(fake_file))
    checksums = [{'checksum': checksum, 'file': fake_file.basename}]
    dl_dir = tmpdir.mkdir('download')
    symlink_dir = tmpdir.mkdir('symlink')
    req.get('https://fake/path/fake_genomic.gbff.gz', text=fake_file.read())

    assert core.worker(
        core.download_file_job(entry, str(dl_dir), checksums, symlink_path=str(symlink_dir)))
    symlink = symlink_dir.join('fake_genomic.gbff.gz')
    assert symlink.check()


def test_create_symlink_job(tmpdir):
    dl_dir = tmpdir.mkdir('download')
    fake_file = dl_dir.join('fake_genomic.gbff.gz')
    fake_file.write('foo')
    assert fake_file.check()
    checksum = core.md5sum(str(fake_file))
    checksums = [{'checksum': checksum, 'file': fake_file.basename}]
    symlink_dir = tmpdir.mkdir('symlink')

    assert core.worker(
        core.create_symlink_job(str(dl_dir), checksums, 'genbank', str(symlink_dir)))
    symlink = symlink_dir.join('fake_genomic.gbff.gz')
    assert symlink.check()


def test_create_symlink_job_remove_symlink(tmpdir):
    dl_dir = tmpdir.mkdir('download')
    fake_file = dl_dir.join('fake_genomic.gbff.gz')
    fake_file.write('foo')
    assert fake_file.check()
    checksum = core.md5sum(str(fake_file))
    checksums = [{'checksum': checksum, 'file': fake_file.basename}]
    symlink_dir = tmpdir.mkdir('symlink')
    wrong_file = symlink_dir.join('fake_genomic.gbff.gz')
    wrong_file.write('bar')
    assert wrong_file.check()

    assert core.worker(
        core.create_symlink_job(str(dl_dir), checksums, 'genbank', str(symlink_dir)))
    symlink = symlink_dir.join('fake_genomic.gbff.gz')
    assert symlink.check()
    assert str(symlink.realpath()) == str(fake_file)


def test_download_file_symlink_path_existed(req, tmpdir):
    entry = {'ftp_path': 'ftp://fake/path'}
    fake_file = tmpdir.join('fake_genomic.gbff.gz')
    fake_file.write('foo')
    assert fake_file.check()
    checksum = core.md5sum(str(fake_file))
    checksums = [{'checksum': checksum, 'file': fake_file.basename}]
    dl_dir = tmpdir.mkdir('download')
    symlink_dir = tmpdir.mkdir('symlink')
    symlink = symlink_dir.join('fake_genomic.gbff.gz')
    os.symlink("/foo/bar", str(symlink))
    req.get('https://fake/path/fake_genomic.gbff.gz', text=fake_file.read())

    assert core.worker(
        core.download_file_job(entry, str(dl_dir), checksums, symlink_path=str(symlink_dir)))
    assert symlink.check()


def test_get_genus_label():
    fake_entry = {'organism_name': 'Example species ABC 1234'}
    assert core.get_genus_label(fake_entry) == 'Example'


def test_get_species_label():
    fake_entry = {'organism_name': 'Example species ABC 1234'}
    assert core.get_species_label(fake_entry) == 'species'

    fake_entry = {'organism_name': 'archaeon', 'infraspecific_name': '',
                  'isolate': 'ARS1334'}
    assert core.get_species_label(fake_entry) == 'sp.'


def test_get_strain_label():
    fake_entry = {'infraspecific_name': 'strain=ABC 1234'}
    assert core.get_strain_label(fake_entry) == 'ABC_1234'

    fake_entry = {'infraspecific_name': '', 'isolate': 'ABC 1234'}
    assert core.get_strain_label(fake_entry) == 'ABC_1234'

    fake_entry = {'infraspecific_name': '', 'isolate': '',
                  'organism_name': 'Example species ABC 1234'}
    assert core.get_strain_label(fake_entry) == 'ABC_1234'

    fake_entry = {'infraspecific_name': '', 'isolate': '',
                  'organism_name': 'Example strain', 'assembly_accession': 'ABC12345'}
    assert core.get_strain_label(fake_entry) == 'ABC12345'

    fake_entry = {'infraspecific_name': '', 'isolate': '',
                  'organism_name': 'Example strain with stupid name',
                  'assembly_accession': 'ABC12345'}
    assert core.get_strain_label(fake_entry, viral=True) == 'ABC12345'

    fake_entry = {'infraspecific_name': 'strain=ABC 1234; FOO'}
    assert core.get_strain_label(fake_entry) == 'ABC_1234__FOO'

    fake_entry = {'infraspecific_name': 'strain=ABC 1234 '}
    assert core.get_strain_label(fake_entry) == 'ABC_1234'

    fake_entry = {'infraspecific_name': 'strain= ABC 1234'}
    assert core.get_strain_label(fake_entry) == 'ABC_1234'

    fake_entry = {'infraspecific_name': 'strain=ABC/1234'}
    assert core.get_strain_label(fake_entry) == 'ABC_1234'

    fake_entry = {'infraspecific_name': 'strain=ABC//1234'}
    assert core.get_strain_label(fake_entry) == 'ABC__1234'

    fake_entry = {'infraspecific_name': 'strain=ABC\\1234'}
    assert core.get_strain_label(fake_entry) == 'ABC_1234'
