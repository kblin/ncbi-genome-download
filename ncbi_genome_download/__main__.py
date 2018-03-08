"""Command line handling for ncbi-genome-download."""
import logging
from ncbi_genome_download import args_download
from ncbi_genome_download import argument_parser
from ncbi_genome_download import __version__


def main():
    """Build and parse command line."""
    parser = argument_parser(version=__version__)
    args = parser.parse_args()

    if args.debug:
        log_level = logging.DEBUG
    elif args.verbose:
        log_level = logging.INFO
    else:
        log_level = logging.WARNING

    logging.basicConfig(format='%(levelname)s: %(message)s', level=log_level)

    max_retries = args.retries
    attempts = 0
    ret = args_download(args)
    while ret == 75 and attempts < max_retries:
        attempts += 1
        logging.error(
            'Downloading from NCBI failed due to a connection error, retrying. Retries so far: %s',
            attempts)
        ret = args_download(args)

    return ret


if __name__ == '__main__':
    main()
