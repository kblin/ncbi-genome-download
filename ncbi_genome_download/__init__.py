__version__ = '0.1.3'
from ncbi_genome_download.core import (
    download,
    NCBI_URI,
    supported_domains,
)
__all__ = [download, NCBI_URI, supported_domains]
