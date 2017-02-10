"""Download genome files from the NCBI"""
from ncbi_genome_download.core import (
    download,
    SUPPORTED_TAXONOMIC_GROUPS,
    EFormats,
    EAssemblyLevels,
    EDefaults
)

__version__ = '0.2.3'
__all__ = [
    'download',
    'SUPPORTED_TAXONOMIC_GROUPS',
    'EFormats',
    'EAssemblyLevels',
    'EDefaults'
]
