import argparse
import logging
import os

import ncbi_genome_download


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('domain',
                        choices=['all'] + ncbi_genome_download.supported_domains,
                        help='The NCBI "domain" to download')
    parser.add_argument('-s', '--section',
                        dest='section', default='refseq', choices=['refseq', 'genbank'],
                        help='NCBI section to download')
    parser.add_argument('-F', '--format',
                        dest='file_format', default='genbank',
                        choices=['all'] + list(ncbi_genome_download.format_name_map.keys()),
                        help='Which format to download (default: genbank)')
    parser.add_argument('-l', '--assembly-level',
                        dest='assembly_level', default='all',
                        choices=['all'] + list(ncbi_genome_download.assembly_level_map.keys()),
                        help='Assembly level of genomes to download (default: all)')
    parser.add_argument('-g', '--genus',
                        dest='genus', default='',
                        help='Only download sequences of the provided genus. (default: unset, download all)')
    parser.add_argument('-o', '--output-folder',
                        dest='output', default=os.getcwd(),
                        help='Create output hierarchy in specified folder (default: current directory)')
    parser.add_argument('-u', '--uri',
                        dest='uri', default=ncbi_genome_download.NCBI_URI,
                        help='NCBI base URI to use')
    parser.add_argument('-v', '--verbose',
                        action='store_true', default=False,
                        help='increase output verbosity')
    parser.add_argument('-d', '--debug',
                        action='store_true', default=False,
                        help='print debugging information')
    parser.add_argument('-V', '--version',
                        action='version', version=ncbi_genome_download.__version__,
                        help='print version information')

    args = parser.parse_args()

    if args.debug:
        log_level = logging.DEBUG
    elif args.verbose:
        log_level = logging.INFO
    else:
        log_level = logging.WARNING

    logging.basicConfig(format='%(levelname)s: %(message)s', level=log_level)

    ncbi_genome_download.download(args)


if __name__ == '__main__':
    main()
