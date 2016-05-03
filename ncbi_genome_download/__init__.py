__version__ = '0.1.0'
supported_domains = ['archaea', 'bacteria', 'fungi', 'invertebrate', 'plant',
                     'protozoa', 'unknown', 'vertebrate_mammalian',
                     'vertebrate_other', 'viral']
from ncbi_genome_download.core import download
__all__ = [download]
