"""Configuration for the downloader."""

import codecs
from collections import OrderedDict
import os
import sys

SUPPORTED_TAXONOMIC_GROUPS = ['archaea', 'bacteria', 'fungi', 'invertebrate', 'plant', 'protozoa',
                              'vertebrate_mammalian', 'vertebrate_other', 'viral']


# TODO: Remove this once we drop py2 support
if sys.version_info[0] == 2:  # pragma: no cover
    string_type = basestring
else:
    string_type = str


class NgdConfig(object):
    """Configuration object for ncbi-genome-download."""

    _FORMATS = OrderedDict([
        ('genbank', '_genomic.gbff.gz'),
        ('fasta', '_genomic.fna.gz'),
        ('features', '_feature_table.txt.gz'),
        ('gff', '_genomic.gff.gz'),
        ('protein-fasta', '_protein.faa.gz'),
        ('genpept', '_protein.gpff.gz'),
        ('wgs', '_wgsmaster.gbff.gz'),
        ('cds-fasta', '_cds_from_genomic.fna.gz'),
        ('rna-fasta', '_rna_from_genomic.fna.gz'),
        ('assembly-report', '_assembly_report.txt'),
        ('assembly-stats', '_assembly_stats.txt'),
    ])

    _LEVELS = OrderedDict([
        ('complete', 'Complete Genome'),
        ('chromosome', 'Chromosome'),
        ('scaffold', 'Scaffold'),
        ('contig', 'Contig'),
    ])

    _REFSEQ_CATEGORIES = OrderedDict([
        ('reference', 'reference genome'),
        ('representative', 'representative genome'),
    ])

    _DEFAULTS = {
        'group': ['all'] + SUPPORTED_TAXONOMIC_GROUPS,
        'section': ['refseq', 'genbank'],
        'file_format': list(_FORMATS) + ['all'],
        'assembly_level': ['all'] + list(_LEVELS),
        'refseq_category': ['all'] + list(_REFSEQ_CATEGORIES),
        'genus': [],
        'species_taxid': [],
        'taxid': [],
        'output': os.getcwd(),
        'uri': 'https://ftp.ncbi.nih.gov/genomes',
        'parallel': 1,
        'human_readable': False,
        'metadata_table': None,
        'dry_run': False,
        'use_cache': False,
    }

    _LIST_TYPES = set([
        'group',
        'file_format',
        'genus',
        'species_taxid',
        'taxid',
    ])

    __slots__ = (
        '_group',
        '_section',
        '_file_format',
        '_assembly_level',
        '_refseq_category',
        '_genus',
        '_species_taxid',
        '_taxid',
        'output',
        'uri',
        'parallel',
        'human_readable',
        'metadata_table',
        'dry_run',
        'use_cache',
    )

    def __init__(self):
        """Set up a config object with all default values."""
        for slot in self.__slots__:
            if slot.startswith('_'):
                slot = slot[1:]
            setattr(self, slot, self.get_default(slot))

    @property
    def section(self):
        """Access the section."""
        return self._section

    @section.setter
    def section(self, value):
        if value not in self._DEFAULTS['section']:
            raise ValueError("Unsupported section {}".format(value))
        self._section = value

    # TODO: Rename this to 'groups' once we do the next API bump
    @property
    def group(self):
        """Access the taxonomic groups."""
        return self._group

    @group.setter
    def group(self, value):
        groups = _create_list(value)

        available_groups = set(self._DEFAULTS['group'])
        for group in groups:
            if group not in available_groups:
                raise ValueError("Unsupported group: {}".format(group))

        if 'all' in groups:
            groups = SUPPORTED_TAXONOMIC_GROUPS

        self._group = groups

    # TODO: Rename this to 'file_formats' once we do the next API bump
    @property
    def file_format(self):
        """Get the file format to downoad."""
        return self._file_format

    @file_format.setter
    def file_format(self, value):
        formats = _create_list(value)

        available_formats = set(self._DEFAULTS['file_format'])
        for file_format in formats:
            if file_format not in available_formats:
                raise ValueError("Unsupported file format: {}".format(file_format))
        if 'all' in formats:
            formats = list(self._FORMATS)

        self._file_format = formats

    @property
    def assembly_level(self):
        """Get the assembly level."""
        return self._assembly_level

    @assembly_level.setter
    def assembly_level(self, value):
        if value not in self._DEFAULTS['assembly_level']:
            raise ValueError("Unsupported assembly level: {}".format(value))
        self._assembly_level = value

    @property
    def refseq_category(self):
        """Get the refseq_category."""
        return self._refseq_category

    @refseq_category.setter
    def refseq_category(self, value):
        if value not in self._DEFAULTS['refseq_category']:
            raise ValueError("Unsupported refseq_category: {}".format(value))
        self._refseq_category = value

    # TODO: Rename to 'taxids' once we do the next API bump
    @property
    def taxid(self):
        """Get the taxid."""
        return self._taxid

    @taxid.setter
    def taxid(self, value):
        self._taxid = _create_list(value, allow_filename=True)

    # TODO: Rename to 'species_taxids' once we do the next API bump
    @property
    def species_taxid(self):
        """Get the species_taxids."""
        return self._species_taxid

    @species_taxid.setter
    def species_taxid(self, value):
        self._species_taxid = _create_list(value, allow_filename=True)

    # TODO: Rename to 'genera' once we do the next API bump
    @property
    def genus(self):
        """Get the genera."""
        return self._genus

    @genus.setter
    def genus(self, value):
        self._genus = _create_list(value, allow_filename=True)

    @classmethod
    def from_kwargs(cls, **kwargs):
        """Initialise configuration from kwargs."""
        config = cls()
        for slot in cls.__slots__:

            if slot.startswith('_'):
                slot = slot[1:]
            setattr(config, slot, kwargs.pop(slot, cls.get_default(slot)))

        if kwargs:
            raise ValueError("Unrecognized option(s): {}".format(kwargs.keys()))
        return config

    @classmethod
    def from_namespace(cls, namespace):
        """Initialise from argparser Namespace object."""
        config = cls()
        for slot in cls.__slots__:
            if slot.startswith('_'):
                slot = slot[1:]
            if not hasattr(namespace, slot):
                continue
            setattr(config, slot, getattr(namespace, slot))

        return config

    @classmethod
    def get_default(cls, category):
        """Get the default value of a given category."""
        value = cls._DEFAULTS[category]
        if not value or not isinstance(value, list):
            return value
        return value[0]

    @classmethod
    def get_choices(cls, category):
        """Get all available options for a category."""
        value = cls._DEFAULTS[category]
        if not isinstance(value, list):
            raise ValueError("{} does not offer choices".format(category))
        return value

    @classmethod
    def get_fileending(cls, file_format):
        """Get the fileending for a given file format."""
        return cls._FORMATS[file_format]

    @classmethod
    def get_assembly_level_string(cls, assembly_level):
        """Get the NCBI string for an assembly level."""
        return cls._LEVELS[assembly_level]

    @classmethod
    def get_refseq_category_string(cls, category):
        """Get the NCBI string for a refseq category."""
        return cls._REFSEQ_CATEGORIES[category]


def _create_list(value, allow_filename=False):
    """Create a list from the input value.

    If the input is a list already, return it.
    If the input is a comma-separated string, split it.

    """
    if isinstance(value, list):
        return value
    elif isinstance(value, string_type):
        if allow_filename and os.path.isfile(value):
            with codecs.open(value, 'r', encoding="utf-8") as handle:
                return handle.read().splitlines()
        return value.split(',')
    else:
        raise ValueError("Can't create list for input {}".format(value))
