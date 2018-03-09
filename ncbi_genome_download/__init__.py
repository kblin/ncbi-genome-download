"""Download genome files from the NCBI"""
from .config import (
    SUPPORTED_TAXONOMIC_GROUPS,
    EFormats,
    EAssemblyLevels,
    EDefaults,
)
from .core import (
    args_download,
    download,
    argument_parser,
)

__version__ = '0.2.6'
__all__ = [
    'download',
    'args_download',
    'SUPPORTED_TAXONOMIC_GROUPS',
    'EFormats',
    'EAssemblyLevels',
    'EDefaults',
    'argument_parser'
]
