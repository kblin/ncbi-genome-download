"""Download genome files from the NCBI"""
from .config import (
    SUPPORTED_TAXONOMIC_GROUPS,
    NgdConfig
)
from .core import (
    args_download,
    download,
    argument_parser,
)

__version__ = '0.3.3'
__all__ = [
    'download',
    'args_download',
    'SUPPORTED_TAXONOMIC_GROUPS',
    'NgdConfig',
    'argument_parser'
]
