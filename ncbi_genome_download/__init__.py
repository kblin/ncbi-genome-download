"""Download genome files from the NCBI"""
from .core import (
    download,
    SUPPORTED_TAXONOMIC_GROUPS,
    EFormats,
    EAssemblyLevels,
    EDefaults
)

__version__ = '0.2.4'
__all__ = [
    'download',
    'SUPPORTED_TAXONOMIC_GROUPS',
    'EFormats',
    'EAssemblyLevels',
    'EDefaults'
]
