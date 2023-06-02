"""Core functionality of ncbi-genome-download."""
from appdirs import user_cache_dir
import argparse
import codecs
from datetime import datetime, timedelta
import errno
import hashlib
import logging
import os
from pathlib import Path
import sys
import time
from io import StringIO
from multiprocessing import Pool
from tqdm import tqdm

import requests

from .config import (
    NgdConfig,
)
from .jobs import DownloadJob
from . import metadata
from .summary import SummaryReader


# Get the user's cache dir in a system-independent manner
CACHE_DIR = user_cache_dir(appname="ncbi-genome-download", appauthor="kblin")


class DeprecatedAction(argparse.Action):
    def __init__(self, option_strings, *args, new_name=None, **kwargs):
        if new_name is None:
            raise ValueError("new_name must be set to name of new argument")
        super(DeprecatedAction, self).__init__(option_strings, *args, **kwargs)
        self.new_name = new_name

    def __call__(self, parser, namespace, values, option_string=None):
        print('Deprecated: option', option_string, 'is deprecated, please use', self.new_name, 'instead',
              file=sys.stderr)
        setattr(namespace, self.dest, values)


def argument_parser(version=None):
    """Create the argument parser for ncbi-genome-download."""
    parser = argparse.ArgumentParser()
    parser.add_argument('groups',
                        default=NgdConfig.get_default('groups'),
                        help='The NCBI taxonomic groups to download (default: %(default)s). '
                        'A comma-separated list of taxonomic groups is also possible. For example: "bacteria,viral"'
                        'Choose from: {choices}'.format(choices=NgdConfig.get_choices('groups')))
    parser.add_argument('-s', '--section', dest='section',
                        choices=NgdConfig.get_choices('section'),
                        default=NgdConfig.get_default('section'),
                        help='NCBI section to download (default: %(default)s)')
    parser.add_argument('-F', '--formats', dest='file_formats',
                        default=NgdConfig.get_default('file_formats'),
                        help='Which formats to download (default: %(default)s).'
                        'A comma-separated list of formats is also possible. For example: "fasta,assembly-report". '
                        'Choose from: {choices}'.format(choices=NgdConfig.get_choices('file_formats')))
    parser.add_argument('-l', '--assembly-levels', dest='assembly_levels',
                        default=NgdConfig.get_default('assembly_levels'),
                        help='Assembly levels of genomes to download (default: %(default)s). '
                        'A comma-separated list of assembly levels is also possible. '
                        'For example: "complete,chromosome". '
                        'Choose from: {choices}'.format(choices=NgdConfig.get_choices('assembly_levels')))
    parser.add_argument('-g', '--genera', dest='genera',
                        default=NgdConfig.get_default('genera'),
                        help='Only download sequences of the provided genera. '
                        'A comma-seperated list of genera is also possible. For example: '
                        '"Streptomyces coelicolor,Escherichia coli". (default: %(default)s)')
    parser.add_argument('--genus', dest='genera', action=DeprecatedAction, new_name="--genera",
                        help='Deprecated alias of --genera')
    parser.add_argument('--fuzzy-genus', dest='fuzzy_genus', action="store_true",
                        default=NgdConfig.get_default('fuzzy_genus'),
                        help="Use a fuzzy search on the organism name instead of an exact match.")
    parser.add_argument('-S', '--strains', dest='strains',
                        default=NgdConfig.get_default('strains'),
                        help='Only download sequences of the given strain(s). '
                        'A comma-separated list of strain names is possible, as well as a path to a filename '
                        'containing one name per line.')
    parser.add_argument('-T', '--species-taxids', dest='species_taxids',
                        default=NgdConfig.get_default('species_taxids'),
                        help='Only download sequences of the provided species NCBI taxonomy IDs. '
                             'A comma-separated list of species taxids is also possible. For example: "52342,12325". '
                             '(default: %(default)s)')
    parser.add_argument('-t', '--taxids', dest='taxids',
                        default=NgdConfig.get_default('taxids'),
                        help='Only download sequences of the provided NCBI taxonomy IDs. '
                             'A comma-separated list of taxids is also possible. For example: "9606,9685". '
                             '(default: %(default)s)')
    parser.add_argument('-A', '--assembly-accessions', dest='assembly_accessions',
                        default=NgdConfig.get_default('assembly_accessions'),
                        help='Only download sequences matching the provided NCBI assembly accession(s). '
                        'A comma-separated list of accessions is possible, as well as a path to a filename '
                        'containing one accession per line.')
    parser.add_argument('--fuzzy-accessions', dest='fuzzy_accessions', action="store_true",
                        default=NgdConfig.get_default('fuzzy_accessions'),
                        help="Use a fuzzy search on the entry accession instead of an exact match.")
    parser.add_argument('-R', '--refseq-categories', dest='refseq_categories',
                        default=NgdConfig.get_default('refseq_categories'),
                        help='Only download sequences of the provided refseq categories [refrerence, representative, na]. '
                             'A comma-separated list of categories is also possible. (default: download all categories)')
    parser.add_argument('--refseq-category', dest='refseq_categories',
                        action=DeprecatedAction, new_name="--refseq-categories",
                        help="Deprecated alias for --refseq-categories")
    parser.add_argument('-o', '--output-folder', dest='output',
                        default=NgdConfig.get_default('output'),
                        help='Create output hierarchy in specified folder (default: %(default)s)')
    parser.add_argument('--flat-output', dest="flat_output", action="store_true",
                        default=NgdConfig.get_default('flat_output'),
                        help='Dump all files right into the output folder without creating any subfolders.')
    parser.add_argument('-H', '--human-readable', dest='human_readable', action='store_true',
                        help='Create links in human-readable hierarchy (might fail on Windows)')
    parser.add_argument('-P', '--progress-bar', dest='progress_bar', action='store_true',
                        default=NgdConfig.get_default('progress_bar'),
                        help='Create a progress bar for indicating the download progress')
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
    parser.add_argument('-M', '--type-materials', dest='type_materials',
                        default=NgdConfig.get_default('type_materials'),
                        help='Specifies the relation to type material for the assembly (default: %(default)s). '
                        '"any" will include assemblies with no relation to type material value defined, "all" will '
                        'download only assemblies with a defined value. '
                        'A comma-separated list of relatons. For example: "reference,synonym".  '
                        'Choose from: {choices} .  '.format(choices=NgdConfig.get_choices('type_materials')))

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
    logger = logging.getLogger("ncbi-genome-download")
    try:
        download_candidates = select_candidates(config)

        if len(download_candidates) < 1:
            logger.error("No downloads matched your filter. Please check your options.")
            return 1

        if config.dry_run:
            print("Considering the following {} assemblies for download:".format(len(download_candidates)))
            for entry, _ in download_candidates:
                print(entry['assembly_accession'], entry['organism_name'], get_strain(entry), sep="\t")

            return 0

        download_jobs = []

        mtable = metadata.get()
        if config.parallel == 1:
            if config.progress_bar:
                download_candidates = tqdm(download_candidates, desc="Checking assemblies", unit="entries")
            for entry, group in download_candidates:
                curr_jobs = create_downloadjob(entry, group, config)
                fill_metadata(curr_jobs, entry, mtable)
                download_jobs.extend(curr_jobs)
            if config.progress_bar:
                _download_jobs = tqdm(download_jobs, desc="Downloading assemblies", unit="files")
            else:
                _download_jobs = download_jobs

            for dl_job in _download_jobs:
                worker(dl_job)
        else:  # pragma: no cover
            # Testing multiprocessing code is annoying
            with Pool(processes=config.parallel) as pool:
                dl_jobs = [pool.apply_async(downloadjob_creator_caller, ((entry, group, config),))
                           for entry, group in download_candidates]

                if config.progress_bar:
                    _dl_jobs = tqdm(dl_jobs, desc="Checking assemblies", unit="entries")
                else:
                    _dl_jobs = dl_jobs

                dl_jobs = [_.get(0xFFFF) for _ in _dl_jobs]

                for index, created_dl_job in enumerate(dl_jobs):
                    download_jobs.extend(created_dl_job)
                    # index is conserved from download_candidates with the use of imap
                    fill_metadata(created_dl_job, download_candidates[index][0], mtable)

                jobs = [pool.apply_async(worker, (_,))
                        for _ in download_jobs]
                try:

                    if config.progress_bar:
                        _jobs = tqdm(jobs, desc="Downloading assemblies", unit="files")
                    else:
                        _jobs = jobs
                    # add a wrapper for progress bar
                    # 0xFFFF is just "a really long time"
                    [_.get(0xFFFF) for _ in _jobs]
                except KeyboardInterrupt:
                    # TODO: Actually test this once I figure out how to do this in py.test
                    logger.error("Interrupted by user")
                    return 1

        if config.metadata_table:
            with codecs.open(config.metadata_table, mode='w', encoding='utf-8') as handle:
                table = metadata.get()
                table.write(handle)

    except requests.exceptions.ConnectionError as err:
        logger.error('Download from NCBI failed: %r', err)
        # Exit code 75 meas TEMPFAIL in C/C++, so let's stick with that for now.
        return 75
    return 0


def fill_metadata(jobs, entry, mtable):
    """Fill the metadata table with the info on the downloaded files.

    Parameters
    ----------
    jobs: List[DownloadJob]
        List of all different file format download jobs for an entry
    entry:
        An assembly entry describing the current download jobs
    mtable:
        Metadata table object to write into

    Returns
    -------
    None
    """
    for job in jobs:
        if job.full_url is not None:  # if it is None, it's a symlink making, so nothing to write
            mtable.add(entry, job.local_file)


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

    for group in config.groups:
        summary_file = get_summary(config.section, group, config.uri, config.use_cache)
        entries = parse_summary(summary_file)

        for entry in filter_entries(entries, config):
            download_candidates.append((entry, group))

    return download_candidates


def filter_entries(entries, config):
    """Narrrow down which entries to download."""
    logger = logging.getLogger("ncbi-genome-download")

    def in_genus_list(species, genus_list):
        for genus in genus_list:
            if config.fuzzy_genus:
                if species.lower().find(genus.lower()) > -1:
                    return True
            elif species.startswith(genus):
                return True
            # Be nice and also find capitalised species names if the user didn't
            elif species.startswith(genus.capitalize()):
                return True
        return False

    new_entries = []
    for entry in entries:
        if config.type_materials and config.type_materials != ['any']:
            requested_types = map(lambda x: config._RELATION_TO_TYPE_MATERIAL[x], config.type_materials)
            if not entry['relation_to_type_material'] or entry['relation_to_type_material'] not in requested_types:
                logger.debug("Skipping assembly with no reference to type material or reference to type material does "
                             "not match requested")
                continue
        if config.genera and not in_genus_list(entry['organism_name'], config.genera):
            logger.debug('Organism name %r does not start with any in %r, skipping',
                         entry['organism_name'], config.genera)
            continue
        if config.strains and get_strain(entry) not in config.strains:
            logger.debug('Strain name %r does not match with any in %r, skipping',
                         get_strain(entry), config.strains)
            continue
        if config.species_taxids and entry['species_taxid'] not in config.species_taxids:
            logger.debug('Species TaxID %r does not match with any in %r, skipping',
                         entry['species_taxid'], config.species_taxids)
            continue
        if config.taxids and entry['taxid'] not in config.taxids:
            logger.debug('Organism TaxID %r does not match with any in %r, skipping',
                         entry['taxid'], config.taxids)
            continue
        if not config.is_compatible_assembly_accession(entry['assembly_accession']):
            logger.debug('Skipping entry with incompatible assembly accession %r', entry['assembly_accession'])
            continue
        if not config.is_compatible_assembly_level(entry['assembly_level']):
            logger.debug('Skipping entry with assembly level %r', entry['assembly_level'])
            continue
        if not config.is_compatible_refseq_category(entry['refseq_category']):
            logger.debug('Skipping entry with refseq_category %r, not %r', entry['refseq_category'],
                         config.refseq_categories)
            continue
        if entry['ftp_path'] == "na":
            logger.warning("Skipping entry, as it has no ftp directory listed: %r", entry['assembly_accession'])
            continue

        new_entries.append(entry)

    return new_entries


def worker(job):
    """Run a single download job."""
    logger = logging.getLogger("ncbi-genome-download")
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
        logger.debug("Ignoring keyboard interrupt.")

    return ret


def get_summary(section, domain, uri, use_cache):
    """Get the assembly_summary.txt file from NCBI and return a StringIO object for it."""
    logger = logging.getLogger("ncbi-genome-download")
    logger.debug('Checking for a cached summary file')

    cachefile = "{section}_{domain}_assembly_summary.txt".format(section=section, domain=domain)
    full_cachefile = os.path.join(CACHE_DIR, cachefile)
    if use_cache and os.path.exists(full_cachefile) and \
       datetime.utcnow() - datetime.fromtimestamp(os.path.getmtime(full_cachefile)) < timedelta(days=1):
        logger.info('Using cached summary.')
        with codecs.open(full_cachefile, 'r', encoding='utf-8') as fh:
            return StringIO(fh.read())

    logger.debug('Downloading summary for %r/%r uri: %r', section, domain, uri)
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


def downloadjob_creator_caller(args):  # pragma: no cover  # No point testing this without testing multiprocessing d/ls
    """Call the download job function from a worker pool runner."""
    return create_downloadjob(*args)


def create_downloadjob(entry, domain, config):
    """Create download jobs for all file formats from a summary file entry."""
    logger = logging.getLogger("ncbi-genome-download")
    logger.info('Checking record %r', entry['assembly_accession'])
    full_output_dir = create_dir(entry, config.section, domain, config.output, config.flat_output)

    symlink_path = None
    if config.human_readable:
        symlink_path = create_readable_dir(entry, config.section, domain, config.output)

    if not config.flat_output:
        checksum_path = Path(full_output_dir) / 'MD5SUMS'

        # if the MD5SUM file is missing or too old, redownload
        if not checksum_path.exists() or checksum_path.stat().st_mtime + (24 * 60 * 60) < time.time():
            checksums = grab_checksums_file(entry)
            with checksum_path.open('w', encoding="utf-8") as handle:
                handle.write(checksums)
        else:
            with checksum_path.open('r', encoding="utf-8") as handle:
                checksums = handle.read()
    else:
        checksums = grab_checksums_file(entry)
    parsed_checksums = parse_checksums(checksums)

    download_jobs = []
    for fmt in config.file_formats:
        try:
            if has_file_changed(full_output_dir, parsed_checksums, fmt):
                download_jobs.append(
                    download_file_job(entry, full_output_dir, parsed_checksums, fmt, symlink_path))
            elif need_to_create_symlink(full_output_dir, parsed_checksums, fmt, symlink_path):
                download_jobs.append(
                    create_symlink_job(full_output_dir, parsed_checksums, fmt, symlink_path))
        except ValueError as err:
            logger.error(err)

    return download_jobs


def create_dir(entry, section, domain, output, flat_output):
    """Create the output directory for the entry if needed."""
    if not flat_output:
        full_output_dir = os.path.join(output, section, domain, entry['assembly_accession'])
    else:
        full_output_dir = os.path.join(output)
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
    logger = logging.getLogger("ncbi-genome-download")
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
            logger.debug('Skipping over unexpected checksum line %r', line)
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
    cds_fasta = NgdConfig.get_fileending('cds-fasta')
    rna_fasta = NgdConfig.get_fileending('rna-fasta')
    for entry in checksums:
        if not entry['file'].endswith(end):
            # wrong file
            continue
        # workaround for ..cds_from_genomic.fna.gz and ..rna_from_genomic.fna.gz also
        # ending in _genomic.fna.gz, causing bogus matches for the plain fasta
        if (entry['file'].endswith(cds_fasta) and end != cds_fasta) or \
           (entry['file'].endswith(rna_fasta) and end != rna_fasta):
            # still the wrong file
            continue  # pragma: no cover  # somehow coverage misses that this is in fact covered
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
    logger = logging.getLogger("ncbi-genome-download")
    with open(local_file, 'wb') as handle:
        for chunk in response.iter_content(4096):
            handle.write(chunk)

    actual_checksum = md5sum(local_file)
    if actual_checksum != expected_checksum:
        logger.error('Checksum mismatch for %r. Expected %r, got %r',
                     local_file, expected_checksum, actual_checksum)
        return False

    return True


def create_symlink(local_file, symlink_path):
    """Create a relative symbolic link if symlink path is given.

    Parameters
    ----------
    local_file
        relative path to output folder (includes ./ prefix) of file saved
    symlink_path
        relative path to output folder (includes ./ prefix) of symbolic link
        to be created

    Returns
    -------
    bool
        success code

    """
    if symlink_path is not None:
        if os.path.exists(symlink_path) or os.path.lexists(symlink_path):
            os.unlink(symlink_path)
        local_file = os.path.normpath(local_file)
        symlink_path = os.path.normpath(symlink_path)
        num_dirs_upward = len(os.path.dirname(symlink_path).split(os.sep))
        local_relative_to_symlink = num_dirs_upward * (os.pardir + os.sep)
        os.symlink(os.path.join(local_relative_to_symlink, local_file),
                   symlink_path)

    return True


def get_genus_label(entry):
    """Get the genus name of an assembly summary entry."""
    return entry['organism_name'].split(' ')[0]


def get_species_label(entry):
    """Get the species name of an assembly summary entry."""
    parts = entry['organism_name'].split(' ')
    if len(parts) < 2:
        return 'sp.'
    return parts[1]


def get_strain(entry, viral=False):
    """Try to extract a strain from an assemly summary entry.

    First this checks 'infraspecific_name', then 'isolate', then
    it tries to get it from 'organism_name'. If all fails, it
    falls back to just returning the assembly accesion number.
    """
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


def get_strain_label(entry, viral=False):
    """Clean up the strain name so it can be used in a file name."""

    def cleanup(strain):
        strain = strain.strip()
        strain = strain.replace(' ', '_')
        strain = strain.replace(';', '_')
        strain = strain.replace('/', '_')
        strain = strain.replace('\\', '_')
        return strain

    return cleanup(get_strain(entry, viral))
