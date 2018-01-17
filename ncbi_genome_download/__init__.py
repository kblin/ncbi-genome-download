"""Download genome files from the NCBI"""
from .core import (
    args_download,
    download,
    SUPPORTED_TAXONOMIC_GROUPS,
    EFormats,
    EAssemblyLevels,
    EDefaults,
    argument_parser
)

__version__ = '0.2.5'
__all__ = [
    'download',
    'args_download',
    'SUPPORTED_TAXONOMIC_GROUPS',
    'EFormats',
    'EAssemblyLevels',
    'EDefaults',
    'argument_parser'
]
