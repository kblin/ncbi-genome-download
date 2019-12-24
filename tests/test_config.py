"""Test the config module."""

from argparse import Namespace
import pytest

from ncbi_genome_download.config import NgdConfig, SUPPORTED_TAXONOMIC_GROUPS, _create_list


def test_init():
    """Test NgdConfig initialises with the correct default values."""
    config = NgdConfig()

    for key in NgdConfig._DEFAULTS:
        expected = NgdConfig._DEFAULTS[key]
        if key in NgdConfig._LIST_TYPES:
            if expected:
                if expected[0] == 'all':
                    expected = expected[1:]
                else:
                    expected = expected[:1]
            if 'all' in expected:
                expected = expected[::].remove('all')
        elif isinstance(expected, list):
            expected = expected[0]

        assert getattr(config, key) == expected


def test_from_kwargs():
    """Test NgdConfig initialises correctly from kwargs."""
    config = NgdConfig.from_kwargs(parallel=2)
    assert config.parallel == 2

    with pytest.raises(ValueError):
        NgdConfig.from_kwargs(garbage="wow")


def test_from_namespace():
    """Test NgdConfig initialises correctly from a Namespace object."""
    args = Namespace(parallel=2)
    config = NgdConfig.from_namespace(args)
    assert config.parallel == 2


def test_section():
    """Test NgdConfig.section getters/setters."""
    config = NgdConfig()

    with pytest.raises(ValueError):
        config.section = 'garbage'


def test_group():
    """Test NgdConfig.group getters/setters."""
    config = NgdConfig()

    assert config.group == SUPPORTED_TAXONOMIC_GROUPS

    config.group = ['bacteria', 'fungi']
    assert config.group == ['bacteria', 'fungi']

    config.group = "all"
    assert config.group == SUPPORTED_TAXONOMIC_GROUPS

    with pytest.raises(ValueError):
        config.group = "garbage"


def test_file_format():
    """Test NgdConfig.file_format getters/setters."""
    config = NgdConfig()

    assert config.file_format == ['genbank']

    config.file_format = ['genbank', 'fasta']
    assert config.file_format == ['genbank', 'fasta']

    config.file_format = "all"
    assert config.file_format == list(NgdConfig._FORMATS)

    with pytest.raises(ValueError):
        config.file_format = "garbage"


def test_assembly_level():
    """Test NgdConfig.assembly_level getters/setters."""
    config = NgdConfig()

    with pytest.raises(ValueError):
        config.assembly_level = 'garbage'


def test_is_compatible_assembly_level():
    """Test NgdConfig.is_compatible_assembly_level."""
    config = NgdConfig()
    ncbi_string = "Complete Genome"

    assert config.is_compatible_assembly_level(ncbi_string)

    config.assembly_level = "complete"
    assert config.is_compatible_assembly_level(ncbi_string)

    config.assembly_level = "chromosome,complete"
    assert config.is_compatible_assembly_level(ncbi_string)

    config.assembly_level = "chromosome"
    assert not config.is_compatible_assembly_level(ncbi_string)


def test_assembly_accessions():
    """Test NgdConfig.assembly_accessions getters/setters."""
    config = NgdConfig()

    assert config.assembly_accessions == []

    config.assembly_accessions = "GCF_000203835.1"
    assert config.assembly_accessions == ['GCF_000203835.1']

    config.assembly_accessions = "GCF_000203835.1,GCF_000444875.1"
    assert config.assembly_accessions == ['GCF_000203835.1', 'GCF_000444875.1']


def test_is_compatible_assembly_accession():
    """Test NgdConfig.is_compatible_assembly_accession."""
    config = NgdConfig()

    assert config.is_compatible_assembly_accession("GCF_000444875.1")

    config.assembly_accessions = "GCF_000203835.1,GCF_000444875.1"
    assert config.is_compatible_assembly_accession("GCF_000444875.1")

    config.assembly_accessions = "GCF_000203835.1"
    assert not config.is_compatible_assembly_accession("GCF_000444875.1")

    config.fuzzy_accessions = True

    config.assembly_accessions = "GCF_000203835"
    assert config.is_compatible_assembly_accession("GCF_000203835.1")

    config.assembly_accessions = "GCF_000203835.1"
    assert not config.is_compatible_assembly_accession("GCF_000444875.1")


def test_refseq_category():
    """Test NgdConfig.refseq_category getters/setters."""
    config = NgdConfig()

    with pytest.raises(ValueError):
        config.refseq_category = 'garbage'


def test_type_material():
    """Test NgdConfig.type_material setters."""
    config = NgdConfig()

    with pytest.raises(ValueError):
        config.type_material = "invalid"


def test_get_choices():
    """Test NgdConfig.get_choices works."""
    assert NgdConfig.get_choices('refseq_category') == ['all', 'reference', 'representative']

    with pytest.raises(KeyError):
        NgdConfig.get_choices('garbage')

    with pytest.raises(ValueError):
        NgdConfig.get_choices('uri')


def test_create_list(tmpdir):
    """Test creating lists from different inputs works as expected."""
    expected = ["foo", "bar", "baz"]

    ret = _create_list(["foo", "bar", "baz"])
    assert ret == expected

    ret = _create_list("foo,bar,baz")
    assert ret == expected

    listfile = tmpdir.join('listfile.txt')
    listfile.write("foo\nbar\nbaz")
    ret = _create_list(str(listfile), allow_filename=True)
    assert ret == expected

    with pytest.raises(ValueError):
        _create_list(123)
