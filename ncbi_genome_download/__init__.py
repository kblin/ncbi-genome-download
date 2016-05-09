__version__ = '0.1.5'
from ncbi_genome_download.core import (
    download,
    NCBI_URI,
    supported_domains,
    format_name_map
)
__all__ = [download, NCBI_URI, supported_domains, format_name_map]
