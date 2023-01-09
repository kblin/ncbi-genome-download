"""Configuration for the downloader."""
import codecs
from collections import OrderedDict
import os
from typing import List


SUPPORTED_TAXONOMIC_GROUPS = [
    'archaea',
    'bacteria',
    'fungi',
    'invertebrate',
    'metagenomes',
    'plant',
    'protozoa',
    'vertebrate_mammalian',
    'vertebrate_other',
    'viral'
]

GENBANK_EXCLUSIVE = [
        'metagenomes'
        ]


class NgdConfig(object):
    """Configuration object for ncbi-genome-download."""

    _FORMATS = OrderedDict([
        ('genbank', '_genomic.gbff.gz'),
        ('fasta', '_genomic.fna.gz'),
        ('rm', '_rm.out.gz'),
        ('features', '_feature_table.txt.gz'),
        ('gff', '_genomic.gff.gz'),
        ('protein-fasta', '_protein.faa.gz'),
        ('genpept', '_protein.gpff.gz'),
        ('wgs', '_wgsmaster.gbff.gz'),
        ('cds-fasta', '_cds_from_genomic.fna.gz'),
        ('rna-fna', '_rna.fna.gz'),
        ('rna-fasta', '_rna_from_genomic.fna.gz'),
        ('assembly-report', '_assembly_report.txt'),
        ('assembly-stats', '_assembly_stats.txt'),
        ('translated-cds', '_translated_cds.faa.gz'),
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
        ('na', 'na'),
    ])

    _RELATION_TO_TYPE_MATERIAL = OrderedDict([
        ('type', 'assembly from type material'),
        ('reference', 'assembly from reference material'),
        ('synonym', 'assembly from synonym type material'),
        ('proxytype', 'assembly from proxytype material'),
        ('neotype', 'assembly designated as neotype')
    ])

    _DEFAULTS = {
        'groups': ['all'] + SUPPORTED_TAXONOMIC_GROUPS,
        'section': ['refseq', 'genbank'],
        'file_formats': list(_FORMATS) + ['all'],
        'assembly_levels': ['all'] + list(_LEVELS),
        'refseq_categories': ['all'] + list(_REFSEQ_CATEGORIES),
        'genera': [],
        'strains': [],
        'flat_output': False,
        'fuzzy_accessions': False,
        'fuzzy_genus': False,
        'species_taxids': [],
        'taxids': [],
        'assembly_accessions': [],
        'output': os.getcwd(),
        'uri': 'https://ftp.ncbi.nih.gov/genomes',
        'parallel': 1,
        'human_readable': False,
        'progress_bar': False,
        'metadata_table': None,
        'dry_run': False,
        'use_cache': False,
        'type_materials': ['any', 'all'] + list(_RELATION_TO_TYPE_MATERIAL)
    }

    _LIST_TYPES = set([
        'assembly_accessions',
        'assembly_levels',
        'groups',
        'file_formats',
        'genera',
        'strains',
        'refseq_categories',
        'species_taxids',
        'taxids',
        'type_materials'
    ])

    __slots__ = (
        '_section',  # section needs to be set first, because group init uses it
        '_groups',
        '_file_formats',
        '_assembly_levels',
        '_refseq_categories',
        '_genera',
        '_strains',
        '_species_taxids',
        '_taxids',
        '_type_materials',
        '_assembly_accessions',
        'flat_output',
        'fuzzy_accessions',
        'fuzzy_genus',
        'output',
        'uri',
        'parallel',
        'human_readable',
        'progress_bar',
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

    @property
    def available_groups(self) -> List[str]:
        groups = SUPPORTED_TAXONOMIC_GROUPS[::]
        if self.section == "refseq":
            groups = list(filter(lambda x: x not in GENBANK_EXCLUSIVE, groups))

        return groups

    @property
    def groups(self):
        """Access the taxonomic groups."""
        return self._groups

    @groups.setter
    def groups(self, value):
        groups = _create_list(value)

        available_groups = set(self._DEFAULTS['groups'])
        for group in groups:
            if group not in available_groups:
                raise ValueError("Unsupported group: {}".format(group))
            if self.section == "refseq" and group in GENBANK_EXCLUSIVE:
                raise ValueError("Unsupported group in refseq: {}".format(group))

        if 'all' in groups:
            groups = self.available_groups

        self._groups = groups

    @property
    def file_formats(self):
        """Get the file format to downoad."""
        return self._file_formats

    @file_formats.setter
    def file_formats(self, value):
        formats = _create_list(value)

        available_formats = set(self._DEFAULTS['file_formats'])
        for file_format in formats:
            if file_format not in available_formats:
                raise ValueError("Unsupported file format: {}".format(file_format))
        if 'all' in formats:
            formats = list(self._FORMATS)

        self._file_formats = formats

    @property
    def assembly_levels(self):
        """Get the assembly level."""
        return self._assembly_levels

    @assembly_levels.setter
    def assembly_levels(self, value):
        levels = _create_list(value)
        available_levels = set(self._DEFAULTS['assembly_levels'])
        for level in levels:
            if level not in available_levels:
                raise ValueError("Unsupported assembly level: {}".format(level))
        if 'all' in levels:
            levels = list(self._LEVELS)
        self._assembly_levels = levels

    @property
    def type_materials(self):
        """Get the relation to type material. """
        return self._type_materials

    @type_materials.setter
    def type_materials(self, value):
        type_materials = _create_list(value)
        available_types = set(self._DEFAULTS['type_materials'])
        for type_material in type_materials:
            if type_material not in available_types:
                raise ValueError("Unsupported relation to type material: {}".format(type_material))
        if 'all' in type_materials:
            type_materials = list(self._RELATION_TO_TYPE_MATERIAL)
        elif 'any' in type_materials:
            type_materials = ['any']
        self._type_materials = type_materials

    @property
    def refseq_categories(self):
        """Get the refseq_categories."""
        return self._refseq_categories

    @refseq_categories.setter
    def refseq_categories(self, value):
        refseq_categories = _create_list(value)
        for category in refseq_categories:
            if category not in self._DEFAULTS['refseq_categories']:
                raise ValueError("Unsupported refseq_category: {}".format(category))
        if 'all' in refseq_categories:
            refseq_categories = list(self._REFSEQ_CATEGORIES)
        self._refseq_categories = refseq_categories

    @property
    def taxids(self):
        """Get the taxids."""
        return self._taxids

    @taxids.setter
    def taxids(self, value):
        self._taxids = _create_list(value, allow_filename=True)

    @property
    def species_taxids(self):
        """Get the species_taxids."""
        return self._species_taxids

    @species_taxids.setter
    def species_taxids(self, value):
        self._species_taxids = _create_list(value, allow_filename=True)

    @property
    def genera(self):
        """Get the genera."""
        return self._genera

    @genera.setter
    def genera(self, value):
        self._genera = _create_list(value, allow_filename=True)

    @property
    def strains(self):
        """Get the strains."""
        return self._strains

    @strains.setter
    def strains(self, value):
        self._strains = _create_list(value, allow_filename=True)

    @property
    def assembly_accessions(self):
        """Get the assembly_accessions."""
        return self._assembly_accessions

    @assembly_accessions.setter
    def assembly_accessions(self, value):
        self._assembly_accessions = _create_list(value, allow_filename=True)

    def is_compatible_assembly_accession(self, acc):
        """Check if a given NCBI assembly accession matches the configured assembly accessions."""
        # if no filter was configured, it's a match
        if not self.assembly_accessions:
            return True

        if not self.fuzzy_accessions:
            return acc in self.assembly_accessions
        else:
            for specified in self.assembly_accessions:
                if acc.startswith(specified):
                    return True
            return False

    def is_compatible_assembly_level(self, ncbi_assembly_level):
        """Check if a given ncbi assembly level string matches the configured assembly levels."""
        configured_ncbi_strings = [self._LEVELS[level] for level in self.assembly_levels]
        return ncbi_assembly_level in configured_ncbi_strings

    def is_compatible_refseq_category(self, category):
        """Check if a given refseq category matches the configured category."""
        configured_refseq_categories = [self.get_refseq_category_string(category)
                                        for category in self.refseq_categories]
        return category in configured_refseq_categories

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
    elif isinstance(value, str):
        if allow_filename and os.path.isfile(value):
            with codecs.open(value, 'r', encoding="utf-8") as handle:
                return handle.read().splitlines()
        return value.split(',')
    else:
        raise ValueError("Can't create list for input {}".format(value))
