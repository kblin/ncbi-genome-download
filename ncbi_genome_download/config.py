"""Configuration for the downloader"""

from enum import Enum, unique
import os

SUPPORTED_TAXONOMIC_GROUPS = ['archaea', 'bacteria', 'fungi', 'invertebrate', 'plant', 'protozoa',
                              'vertebrate_mammalian', 'vertebrate_other', 'viral']


@unique
class EMap(Enum):
    """
    Enumeration of (`key`, `content`) pairs. The name `content` is used, because `value` is
     already an attribute of the Enum instances.
     We use an enumeration to ensure the immutability of the elements.
    """

    def __init__(self, key, content):
        """

        Parameters
        ----------
        key : str
        content : object
        """
        self.key = key
        self.content = content

    @classmethod
    def keys(cls):
        """
        Simulate dict.keys() on this enumeration map

        Returns
        -------
        list
            containing all the keys of this map enumeration
        """
        if not hasattr(cls, '_keys'):
            keys = []
            for _, member in cls.__members__.items():
                keys.append(member.key)
            cls._keys = keys
        return cls._keys

    @classmethod
    def items(cls):
        """
        Simulate dict.items() on this enumeration map

        Returns
        -------
        list of tuple
        """
        if not hasattr(cls, '_items'):
            items = []
            for _, member in cls.__members__.items():
                items.append((member.key, member.content))
            cls._items = items
        return cls._items

    @classmethod
    def get_content(cls, key):
        """
        Shortcut to get the content value for the enumeration map item with the given `key`.

        Parameters
        ----------
        key : str

        Returns
        -------
        type(content)

        """
        if not hasattr(cls, '_as_dict'):
            as_dict = {}
            for emap in list(cls):
                as_dict.update({emap.key: emap.content})
            cls._as_dict = as_dict
        return cls._as_dict[key]


class EFormats(EMap):
    # only needed in Python 2
    __order__ = 'GENBANK FASTA FEATURES GFF PROTFASTA GENREPT WGS CDSFASTA RNAFASTA ASSEMBLYREPORT ASSEMBLYSTATS'
    GENBANK = ('genbank', '_genomic.gbff.gz')
    FASTA = ('fasta', '_genomic.fna.gz')
    FEATURES = ('features', '_feature_table.txt.gz')
    GFF = ('gff', '_genomic.gff.gz')
    PROTFASTA = ('protein-fasta', '_protein.faa.gz')
    GENREPT = ('genpept', '_protein.gpff.gz')
    WGS = ('wgs', '_wgsmaster.gbff.gz')
    CDSFASTA = ('cds-fasta', '_cds_from_genomic.fna.gz')
    RNAFASTA = ('rna-fasta', '_rna_from_genomic.fna.gz')
    ASSEMBLYREPORT = ('assembly-report', '_assembly_report.txt')
    ASSEMBLYSTATS = ('assembly-stats', '_assembly_stats.txt')


class EAssemblyLevels(EMap):
    __order__ = 'COMPLETE CHROMOSOME SCAFFOLD CONTIG'  # only needed in Python 2
    COMPLETE = ('complete', 'Complete Genome')
    CHROMOSOME = ('chromosome', 'Chromosome')
    SCAFFOLD = ('scaffold', 'Scaffold')
    CONTIG = ('contig', 'Contig')


class ERefseqCategories(EMap):
    __order__ = 'REFERENCE REPRESENTATIVE'
    REFERENCE = ('reference', 'reference genome')
    REPRESENTATIVE = ('representative', 'representative genome')


class EDefaults(Enum):
    TAXONOMIC_GROUPS = ['all'] + SUPPORTED_TAXONOMIC_GROUPS
    SECTIONS = ['refseq', 'genbank']
    FORMATS = list(EFormats.keys()) + ['all']
    ASSEMBLY_LEVELS = ['all'] + list(EAssemblyLevels.keys())
    REFSEQ_CATEGORIES = ['all'] + list(ERefseqCategories.keys())
    GENUS = None
    SPECIES_TAXID = None
    TAXID = None
    OUTPUT = os.getcwd()
    URI = 'https://ftp.ncbi.nih.gov/genomes'
    NB_PROCESSES = 1
    TABLE = None

    @property
    def default(self):
        return self.value[0] if isinstance(self.value, list) else self.value

    @property
    def choices(self):
        return self.value if isinstance(self.value, list) else None
