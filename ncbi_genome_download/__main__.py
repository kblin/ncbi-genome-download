"""Command line handling for ncbi-genome-download"""
import argparse
import logging

import ncbi_genome_download as ngd
from ncbi_genome_download import EDefaults as dflt


def main():
    """Build and parse command line"""
    parser = argparse.ArgumentParser()
    parser.add_argument('domain',
                        choices=dflt.DOMAIN.choices,
                        default=dflt.DOMAIN.default,
                        help='The NCBI "domain" to download (default: %(default)s)')
    parser.add_argument('-s', '--section', dest='section',
                        default=dflt.SECTION.default,
                        choices=dflt.SECTION.choices,
                        help='NCBI section to download (default: %(default)s)')
    parser.add_argument('-F', '--format', dest='file_format',
                        default=dflt.FORMAT.default,
                        choices=dflt.FORMAT.choices,
                        help='Which format to download (default: %(default)s)')
    parser.add_argument('-l', '--assembly-level', dest='assembly_level',
                        default=dflt.ASSEMBLY_LEVEL.default,
                        choices=dflt.ASSEMBLY_LEVEL.choices,
                        help='Assembly level of genomes to download (default: %(default)s)')
    parser.add_argument('-g', '--genus', dest='genus',
                        default=dflt.GENUS.default,
                        help='Only download sequences of the provided genus. (default: %(default)s)')
    parser.add_argument('-T', '--species-taxid', dest='species_taxid',
                        default=dflt.SPECIES_TAXID.default,
                        help='Only download sequences of the provided species NCBI taxonomy ID. '
                             '(default: %(default)s)')
    parser.add_argument('-t', '--taxid',
                        dest='taxid',
                        default=dflt.TAXID.default,
                        help='Only download sequences of the provided NCBI taxonomy ID. ('
                             'default: %(default)s)')
    parser.add_argument('-o', '--output-folder',
                        dest='output', default=dflt.OUTPUT.default,
                        help='Create output hierarchy in specified folder (default: %(default)s)')
    parser.add_argument('-H', '--human-readable',
                        dest='human_readable', action='store_true',
                        help='Create links in human-readable hierarchy (might fail on Windows)')
    parser.add_argument('-u', '--uri',
                        dest='uri', default=dflt.URI.default,
                        help='NCBI base URI to use (default: %(default)s)')
    parser.add_argument('-p', '--parallel', dest='parallel', type=int, metavar="N",
                        default=dflt.PROCESSES.default,
                        help='Run %(metavar)s downloads in parallel (default: %(default)s)')
    parser.add_argument('-r', '--retries', dest='retries', type=int, metavar="N",
                        default=dflt.RETRIES.default,
                        help='Retry download %(metavar)s times when connection to NCBI fails ('
                             'default: %(default)s)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='increase output verbosity')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='print debugging information')
    parser.add_argument('-V', '--version', action='version', version=ngd.__version__,
                        help='print version information')

    args = parser.parse_args()

    if args.debug:
        log_level = logging.DEBUG
    elif args.verbose:
        log_level = logging.INFO
    else:
        log_level = logging.WARNING

    logging.basicConfig(format='%(levelname)s: %(message)s', level=log_level)

    retries = 0
    ret = ngd.download(vars(args))
    while ret == 75 and retries < args.retries:
        retries += 1
        logging.error(
            'Downloading from NCBI failed due to a connection error, retrying. Retries so far: %s',
            retries)
        ret = ngd.download(args)

    return ret


if __name__ == '__main__':
    main()
