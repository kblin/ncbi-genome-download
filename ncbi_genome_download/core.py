from __future__ import print_function
import requests

NCBI_URI = 'http://ftp.ncbi.nih.gov/genomes'
supported_domains = ['archaea', 'bacteria', 'fungi', 'invertebrate', 'plant',
                     'protozoa', 'unknown', 'vertebrate_mammalian',
                     'vertebrate_other', 'viral']


def download(args):
    '''Download a specified NCBI domain'''

    if args.domain == 'all':
        print('Downloading all NCBI domains')
    else:
        print('Downloading NCBI domain {!r}'.format(args.domain))


def get_summary(section, domain, uri=NCBI_URI):
    url = '{uri}/{section}/{domain}/assembly_summary.txt'.format(
        section=section, domain=domain, uri=uri)
    r = requests.get(url)
    return r.text
