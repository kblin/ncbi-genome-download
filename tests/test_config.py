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


def test_groups():
    """Test NgdConfig.groups getters/setters."""
    config = NgdConfig()

    assert config.groups == SUPPORTED_TAXONOMIC_GROUPS

    config.groups = ['bacteria', 'fungi']
    assert config.groups == ['bacteria', 'fungi']

    config.groups = "all"
    assert config.groups == SUPPORTED_TAXONOMIC_GROUPS

    with pytest.raises(ValueError):
        config.groups = "garbage"

    # No metagenomes in refseq
    with pytest.raises(ValueError):
        config.section = "refseq"
        config.groups = "metagenomes"

    # genbank has metagenomes
    config.section = "genbank"
    config.groups = "metagenomes"


def test_file_formats():
    """Test NgdConfig.file_formats getters/setters."""
    config = NgdConfig()

    assert config.file_formats == ['genbank']

    config.file_formats = ['genbank', 'fasta']
    assert config.file_formats == ['genbank', 'fasta']

    config.file_formats = "all"
    assert config.file_formats == list(NgdConfig._FORMATS)

    with pytest.raises(ValueError):
        config.file_formats = "garbage"


def test_assembly_levels():
    """Test NgdConfig.assembly_levels getters/setters."""
    config = NgdConfig()

    with pytest.raises(ValueError):
        config.assembly_levels = 'garbage'


def test_is_compatible_assembly_level():
    """Test NgdConfig.is_compatible_assembly_level."""
    config = NgdConfig()
    ncbi_string = "Complete Genome"

    assert config.is_compatible_assembly_level(ncbi_string)

    config.assembly_levels = "complete"
    assert config.is_compatible_assembly_level(ncbi_string)

    config.assembly_levels = "chromosome,complete"
    assert config.is_compatible_assembly_level(ncbi_string)

    config.assembly_levels = "chromosome"
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


def test_refseq_categories():
    """Test NgdConfig.refseq_categories getters/setters."""
    config = NgdConfig()

    with pytest.raises(ValueError):
        config.refseq_categories = 'garbage'


def test_type_materials():
    """Test NgdConfig.type_materials setters."""
    config = NgdConfig()

    with pytest.raises(ValueError):
        config.type_materials = "invalid"


def test_get_choices():
    """Test NgdConfig.get_choices works."""
    assert NgdConfig.get_choices('refseq_categories') == ['all', 'reference', 'representative', 'na']

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
