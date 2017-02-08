'''Download genome files from the NCBI'''
from ncbi_genome_download.core import (
    download,
    NCBI_URI,
    SUPPORTED_DOMAINS,
    FORMAT_NAME_MAP,
    ASSEMBLY_LEVEL_MAP,
)
__version__ = '0.2.3'
__all__ = [
    'download',
    'NCBI_URI',
    'SUPPORTED_DOMAINS',
    'FORMAT_NAME_MAP',
    'ASSEMBLY_LEVEL_MAP'
]
