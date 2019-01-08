"""Core functionality of ncbi-genome-download."""
from __future__ import print_function

from appdirs import user_cache_dir
import argparse
import codecs
from datetime import datetime, timedelta
import errno
import hashlib
import logging
import os
import sys
from io import StringIO
from multiprocessing import Pool

import requests

from .config import (
    NgdConfig,
)
from .jobs import DownloadJob
from . import metadata
from .summary import SummaryReader

# Python < 2.7.9 hack: fix ssl support
if sys.version_info < (2, 7, 9):  # pragma: no cover
    from requests.packages.urllib3.contrib import pyopenssl
    pyopenssl.inject_into_urllib3()


# Get the user's cache dir in a system-independent manner
CACHE_DIR = user_cache_dir(appname="ncbi-genome-download", appauthor="kblin")


def argument_parser(version=None):
    """Create the argument parser for ncbi-genome-download."""
    parser = argparse.ArgumentParser()
    parser.add_argument('group',
                        default=NgdConfig.get_default('group'),
                        help='The NCBI taxonomic group to download (default: %(default)s). '
                        'A comma-separated list of taxonomic groups is also possible. For example: "bacteria,viral"'
                        'Choose from: {choices}'.format(choices=NgdConfig.get_choices('group')))
    parser.add_argument('-s', '--section', dest='section',
                        choices=NgdConfig.get_choices('section'),
                        default=NgdConfig.get_default('section'),
                        help='NCBI section to download (default: %(default)s)')
    parser.add_argument('-F', '--format', dest='file_format',
                        default=NgdConfig.get_default('file_format'),
                        help='Which format to download (default: %(default)s).'
                        'A comma-separated list of formats is also possible. For example: "fasta,assembly-report". '
                        'Choose from: {choices}'.format(choices=NgdConfig.get_choices('file_format')))
    parser.add_argument('-l', '--assembly-level', dest='assembly_level',
                        default=NgdConfig.get_default('assembly_level'),
                        help='Assembly level of genomes to download (default: %(default)s). '
                        'A comma-separated list of assembly levels is also possible. For example: "complete,chromosome". '
                        'Coose from: {choices}'.format(choices=NgdConfig.get_choices('assembly_level')))
    parser.add_argument('-g', '--genus', dest='genus',
                        default=NgdConfig.get_default('genus'),
                        help='Only download sequences of the provided genus. '
                        'A comma-seperated list of genera is also possible. For example: '
                        '"Streptomyces coelicolor,Escherichia coli". (default: %(default)s)')
    parser.add_argument('-T', '--species-taxid', dest='species_taxid',
                        default=NgdConfig.get_default('species_taxid'),
                        help='Only download sequences of the provided species NCBI taxonomy ID. '
                             'A comma-separated list of species taxids is also possible. For example: "52342,12325". '
                             '(default: %(default)s)')
    parser.add_argument('-t', '--taxid', dest='taxid',
                        default=NgdConfig.get_default('taxid'),
                        help='Only download sequences of the provided NCBI taxonomy ID. '
                             'A comma-separated list of taxids is also possible. For example: "9606,9685". '
                             '(default: %(default)s)')
    parser.add_argument('-A', '--assembly-accessions', dest='assembly_accessions',
                        default=NgdConfig.get_default('assembly_accessions'),
                        help='Only download sequences matching the provided NCBI assembly accession(s). '
                        'A comma-separated list of accessions is possible, as well as a path to a filename '
                        'containing one accession per line.')
    parser.add_argument('-R', '--refseq-category', dest='refseq_category',
                        choices=NgdConfig.get_choices('refseq_category'),
                        default=NgdConfig.get_default('refseq_category'),
                        help='Only download sequences of the provided refseq category (default: %(default)s)')
    parser.add_argument('-o', '--output-folder', dest='output',
                        default=NgdConfig.get_default('output'),
                        help='Create output hierarchy in specified folder (default: %(default)s)')
    parser.add_argument('-H', '--human-readable', dest='human_readable', action='store_true',
                        help='Create links in human-readable hierarchy (might fail on Windows)')
    parser.add_argument('-u', '--uri', dest='uri',
                        default=NgdConfig.get_default('uri'),
                        help='NCBI base URI to use (default: %(default)s)')
    parser.add_argument('-p', '--parallel', dest='parallel', type=int, metavar="N",
                        default=NgdConfig.get_default('parallel'),
                        help='Run %(metavar)s downloads in parallel (default: %(default)s)')
    parser.add_argument('-r', '--retries', dest='retries', type=int, metavar="N",
                        default=0,
                        help='Retry download %(metavar)s times when connection to NCBI fails ('
                             'default: %(default)s)')
    parser.add_argument('-m', '--metadata-table', type=str,
                        help='Save tab-delimited file with genome metadata')
    parser.add_argument('-n', '--dry-run', dest='dry_run', action='store_true',
                        help="Only check which files to download, don't download genome files.")
    parser.add_argument('-N', '--no-cache', dest='use_cache', action='store_false',
                        help="Don't cache the assembly summary file in %s." % CACHE_DIR)
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='increase output verbosity')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='print debugging information')
    parser.add_argument('-V', '--version', action='version', version=version,
                        help='print version information')
    parser.add_argument('-M', '--type-material', dest='type_material',
                        default=NgdConfig.get_default('type_material'),
                        help='Specifies the relation to type material for the assembly (default: %(default)s). '
                        '"any" will include assemblies with no relation to type material value defined, "all" will download only assemblies with a defined value. '
                        'A comma-separated list of relatons. For example: "reference,synonym".  '
                        'Choose from: {choices} .  '.format(choices=NgdConfig.get_choices('type_material')))

    return parser


def download(**kwargs):
    """Download data from NCBI using parameters passed as kwargs.

    Parameters
    ----------
    kwargs
        dictionary of parameters to pass to NgdConfig

    Returns
    -------
    int
        success code

    """
    config = NgdConfig.from_kwargs(**kwargs)
    return config_download(config)


def args_download(args):
    """Download data from NCBI using parameters passed as argparse.Namespace object.

    Parameters
    ----------
    args: Namespace
        Arguments from argument_parser

    Returns
    -------
    int
        success code

    """
    config = NgdConfig.from_namespace(args)
    return config_download(config)


def config_download(config):
    """Run the actual download from NCBI with parameters in a config object.

    Parameters
    ----------
        config: NgdConfig
            A configuration object with the download settings

    Returns
    -------
    int
        success code

    """
    try:
        download_candidates = select_candidates(config)

        if len(download_candidates) < 1:
            logging.error("No downloads matched your filter. Please check your options.")
            return 1

        if config.dry_run:
            print("Considering the following {} assemblies for download:".format(len(download_candidates)))
            for entry, _ in download_candidates:
                print(entry['assembly_accession'], entry['organism_name'], sep="\t")

            return 0

        download_jobs = []
        for entry, group in download_candidates:
            download_jobs.extend(create_downloadjob(entry, group, config))

        if config.parallel == 1:
            for dl_job in download_jobs:
                worker(dl_job)
        else:  # pragma: no cover
            # Testing multiprocessing code is annoying
            pool = Pool(processes=config.parallel)
            jobs = pool.map_async(worker, download_jobs)
            try:
                # 0xFFFF is just "a really long time"
                jobs.get(0xFFFF)
            except KeyboardInterrupt:
                # TODO: Actually test this once I figure out how to do this in py.test
                logging.error("Interrupted by user")
                return 1

        if config.metadata_table:
            with codecs.open(config.metadata_table, mode='w', encoding='utf-8') as handle:
                table = metadata.get()
                table.write(handle)

    except requests.exceptions.ConnectionError as err:
        logging.error('Download from NCBI failed: %r', err)
        # Exit code 75 meas TEMPFAIL in C/C++, so let's stick with that for now.
        return 75
    return 0


def select_candidates(config):
    """Select candidates to download.

    Parameters
    ----------
    config: NgdConfig
        Runtime configuration object

    Returns
    -------
    list of (<candidate entry>, <taxonomic group>)

    """
    download_candidates = []

    for group in config.group:
        summary_file = get_summary(config.section, group, config.uri, config.use_cache)
        entries = parse_summary(summary_file)

        for entry in filter_entries(entries, config):
            download_candidates.append((entry, group))

    return download_candidates


def filter_entries(entries, config):
    """Narrrow down which entries to download."""
    def in_genus_list(species, genus_list):
        for genus in genus_list:
            if species.startswith(genus.capitalize()):
                return True
        return False

    new_entries = []
    for entry in entries:
        if config.type_material and config.type_material != ['any']:
            requested_types = map(lambda x: config._RELATION_TO_TYPE_MATERIAL[x], config.type_material)
            if not entry['relation_to_type_material'] or entry['relation_to_type_material'] not in requested_types:
                 logging.debug("Skipping assembly with no reference to type material or reference to type material does not match requested")
                 continue 
            else:
                print(entry['relation_to_type_material'])
        if config.genus and not in_genus_list(entry['organism_name'], config.genus):
            logging.debug('Organism name %r does not start with any in %r, skipping',
                          entry['organism_name'], config.genus)
            continue
        if config.species_taxid and entry['species_taxid'] not in config.species_taxid:
            logging.debug('Species TaxID %r does not match with any in %r, skipping',
                          entry['species_taxid'], config.species_taxid)
            continue
        if config.taxid and entry['taxid'] not in config.taxid:
            logging.debug('Organism TaxID %r does not match with any in %r, skipping',
                          entry['taxid'], config.taxid)
            continue
        if not config.is_compatible_assembly_accession(entry['assembly_accession']):
            logging.debug('Skipping entry with incompatible assembly accession %r', entry['assembly_accession'])
            continue
        if not config.is_compatible_assembly_level(entry['assembly_level']):
            logging.debug('Skipping entry with assembly level %r', entry['assembly_level'])
            continue
        if config.refseq_category != 'all' \
                and entry['refseq_category'] != config.get_refseq_category_string(config.refseq_category):
            logging.debug('Skipping entry with refseq_category %r, not %r', entry['refseq_category'],
                          config.refseq_category)
            continue
        new_entries.append(entry)

    return new_entries


def worker(job):
    """Run a single download job."""
    ret = False
    try:
        if job.full_url is not None:
            req = requests.get(job.full_url, stream=True)
            ret = save_and_check(req, job.local_file, job.expected_checksum)
            if not ret:
                return ret
        ret = create_symlink(job.local_file, job.symlink_path)
    except KeyboardInterrupt:  # pragma: no cover
        # TODO: Actually test this once I figure out how to do this in py.test
        logging.debug("Ignoring keyboard interrupt.")

    return ret


def get_summary(section, domain, uri, use_cache):
    """Get the assembly_summary.txt file from NCBI and return a StringIO object for it."""
    logging.debug('Checking for a cached summary file')

    cachefile = "{section}_{domain}_assembly_summary.txt".format(section=section, domain=domain)
    full_cachefile = os.path.join(CACHE_DIR, cachefile)
    if use_cache and os.path.exists(full_cachefile) and \
       datetime.utcnow() - datetime.fromtimestamp(os.path.getmtime(full_cachefile)) < timedelta(days=1):
        logging.info('Using cached summary.')
        with codecs.open(full_cachefile, 'r', encoding='utf-8') as fh:
            return StringIO(fh.read())

    logging.debug('Downloading summary for %r/%r uri: %r', section, domain, uri)
    url = '{uri}/{section}/{domain}/assembly_summary.txt'.format(
        section=section, domain=domain, uri=uri)
    req = requests.get(url)

    if use_cache:
        try:
            os.makedirs(CACHE_DIR)
        except OSError as err:
            # Errno 17 is "file exists", ignore that, otherwise re-raise
            if err.errno != 17:
                raise

        with codecs.open(full_cachefile, 'w', encoding='utf-8') as fh:
            fh.write(req.text)

    return StringIO(req.text)


def parse_summary(summary_file):
    """Parse the summary file from TSV format to a csv DictReader-like object."""
    return SummaryReader(summary_file)


def create_downloadjob(entry, domain, config):
    """Create download jobs for all file formats from a summary file entry."""
    logging.info('Checking record %r', entry['assembly_accession'])
    full_output_dir = create_dir(entry, config.section, domain, config.output)

    symlink_path = None
    if config.human_readable:
        symlink_path = create_readable_dir(entry, config.section, domain, config.output)

    checksums = grab_checksums_file(entry)

    # TODO: Only write this when the checksums file changed
    with open(os.path.join(full_output_dir, 'MD5SUMS'), 'w') as handle:
        handle.write(checksums)

    parsed_checksums = parse_checksums(checksums)

    download_jobs = []
    for fmt in config.file_format:
        try:
            if has_file_changed(full_output_dir, parsed_checksums, fmt):
                download_jobs.append(
                    download_file_job(entry, full_output_dir, parsed_checksums, fmt, symlink_path))
            elif need_to_create_symlink(full_output_dir, parsed_checksums, fmt, symlink_path):
                download_jobs.append(
                    create_symlink_job(full_output_dir, parsed_checksums, fmt, symlink_path))
        except ValueError as err:
            logging.error(err)

    return download_jobs


def create_dir(entry, section, domain, output):
    """Create the output directory for the entry if needed."""
    full_output_dir = os.path.join(output, section, domain, entry['assembly_accession'])
    try:
        os.makedirs(full_output_dir)
    except OSError as err:
        if err.errno == errno.EEXIST and os.path.isdir(full_output_dir):
            pass
        else:
            raise

    return full_output_dir


def create_readable_dir(entry, section, domain, output):
    """Create the a human-readable directory to link the entry to if needed."""
    if domain != 'viral':
        full_output_dir = os.path.join(output, 'human_readable', section, domain,
                                       get_genus_label(entry),
                                       get_species_label(entry),
                                       get_strain_label(entry))
    else:
        full_output_dir = os.path.join(output, 'human_readable', section, domain,
                                       entry['organism_name'].replace(' ', '_'),
                                       get_strain_label(entry, viral=True))

    try:
        os.makedirs(full_output_dir)
    except OSError as err:
        if err.errno == errno.EEXIST and os.path.isdir(full_output_dir):
            pass
        else:
            raise

    return full_output_dir


def grab_checksums_file(entry):
    """Grab the checksum file for a given entry."""
    http_url = convert_ftp_url(entry['ftp_path'])
    full_url = '{}/md5checksums.txt'.format(http_url)
    req = requests.get(full_url)
    return req.text


def convert_ftp_url(url):
    """Convert FTP to HTTPS URLs."""
    return url.replace('ftp://', 'https://', 1)


def parse_checksums(checksums_string):
    """Parse a file containing checksums and filenames."""
    checksums_list = []
    for line in checksums_string.split('\n'):
        try:
            # skip empty lines
            if line == '':
                continue

            checksum, filename = line.split()
            # strip leading ./
            if filename.startswith('./'):
                filename = filename[2:]
            checksums_list.append({'checksum': checksum, 'file': filename})
        except ValueError:
            logging.debug('Skipping over unexpected checksum line %r', line)
            continue

    return checksums_list


def has_file_changed(directory, checksums, filetype='genbank'):
    """Check if the checksum of a given file has changed."""
    pattern = NgdConfig.get_fileending(filetype)
    filename, expected_checksum = get_name_and_checksum(checksums, pattern)
    full_filename = os.path.join(directory, filename)
    # if file doesn't exist, it has changed
    if not os.path.isfile(full_filename):
        return True

    actual_checksum = md5sum(full_filename)
    return expected_checksum != actual_checksum


def need_to_create_symlink(directory, checksums, filetype, symlink_path):
    """Check if we need to create a symlink for an existing file."""
    # If we don't have a symlink path, we don't need to create a symlink
    if symlink_path is None:
        return False

    pattern = NgdConfig.get_fileending(filetype)
    filename, _ = get_name_and_checksum(checksums, pattern)
    full_filename = os.path.join(directory, filename)
    symlink_name = os.path.join(symlink_path, filename)

    if os.path.islink(symlink_name):
        existing_link = os.readlink(symlink_name)
        if full_filename == existing_link:
            return False

    return True


def get_name_and_checksum(checksums, end):
    """Extract a full filename and checksum from the checksums list for a file ending in given end."""
    for entry in checksums:
        if not entry['file'].endswith(end):
            # wrong file
            continue
        # workaround for ..cds_from_genomic.fna.gz and ..rna_from_genomic.fna.gz also
        # ending in _genomic.fna.gz, causing bogus matches for the plain fasta
        if '_from_' not in end and '_from_' in entry['file']:
            # still the wrong file
            continue
        filename = entry['file']
        expected_checksum = entry['checksum']
        return filename, expected_checksum
    raise ValueError('No entry for file ending in {!r}'.format(end))


def md5sum(filename):
    """Calculate the md5sum of a file and return the hexdigest."""
    hash_md5 = hashlib.md5()
    with open(filename, 'rb') as handle:
        for chunk in iter(lambda: handle.read(4096), b''):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


# pylint and I disagree on code style here. Shut up, pylint.
# pylint: disable=too-many-arguments
def download_file_job(entry, directory, checksums, filetype='genbank', symlink_path=None):
    """Generate a DownloadJob that actually triggers a file download."""
    pattern = NgdConfig.get_fileending(filetype)
    filename, expected_checksum = get_name_and_checksum(checksums, pattern)
    base_url = convert_ftp_url(entry['ftp_path'])
    full_url = '{}/{}'.format(base_url, filename)
    local_file = os.path.join(directory, filename)
    full_symlink = None
    if symlink_path is not None:
        full_symlink = os.path.join(symlink_path, filename)

    # Keep metadata around
    mtable = metadata.get()
    mtable.add(entry, local_file)

    return DownloadJob(full_url, local_file, expected_checksum, full_symlink)
# pylint: enable=too-many-arguments,too-many-locals


def create_symlink_job(directory, checksums, filetype, symlink_path):
    """Create a symlink-creating DownloadJob for an already downloaded file."""
    pattern = NgdConfig.get_fileending(filetype)
    filename, _ = get_name_and_checksum(checksums, pattern)
    local_file = os.path.join(directory, filename)
    full_symlink = os.path.join(symlink_path, filename)
    return DownloadJob(None, local_file, None, full_symlink)


def save_and_check(response, local_file, expected_checksum):
    """Save the content of an http response and verify the checksum matches."""
    with open(local_file, 'wb') as handle:
        for chunk in response.iter_content(4096):
            handle.write(chunk)

    actual_checksum = md5sum(local_file)
    if actual_checksum != expected_checksum:
        logging.error('Checksum mismatch for %r. Expected %r, got %r',
                      local_file, expected_checksum, actual_checksum)
        return False

    return True


def create_symlink(local_file, symlink_path):
    """Create a symlink if symlink path is given."""
    if symlink_path is not None:
        if os.path.exists(symlink_path) or os.path.lexists(symlink_path):
            os.unlink(symlink_path)

        os.symlink(os.path.abspath(local_file), symlink_path)

    return True


def get_genus_label(entry):
    """Get the genus name of an assembly summary entry."""
    return entry['organism_name'].split(' ')[0]


def get_species_label(entry):
    """Get the species name of an assembly summary entry."""
    return entry['organism_name'].split(' ')[1]


def get_strain_label(entry, viral=False):
    """Try to extract a strain from an assemly summary entry.

    First this checks 'infraspecific_name', then 'isolate', then
    it tries to get it from 'organism_name'. If all fails, it
    falls back to just returning the assembly accesion number.
    """
    def get_strain(entry):
        strain = entry['infraspecific_name']
        if strain != '':
            strain = strain.split('=')[-1]
            return strain

        strain = entry['isolate']
        if strain != '':
            return strain

        if len(entry['organism_name'].split(' ')) > 2 and not viral:
            strain = ' '.join(entry['organism_name'].split(' ')[2:])
            return strain

        return entry['assembly_accession']

    def cleanup(strain):
        strain = strain.strip()
        strain = strain.replace(' ', '_')
        strain = strain.replace(';', '_')
        strain = strain.replace('/', '_')
        strain = strain.replace('\\', '_')
        return strain

    return cleanup(get_strain(entry))
