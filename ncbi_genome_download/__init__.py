'''Download genome files from the NCBI'''
from ncbi_genome_download.core import (
    download,
    NCBI_URI,
    supported_domains,
    format_name_map,
    assembly_level_map,
)
__version__ = '0.1.7'
__all__ = [
    'download',
    'NCBI_URI',
    'supported_domains',
    'format_name_map',
    'assembly_level_map'
]
