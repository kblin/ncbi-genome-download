"""Core functionality of ncbi-genome-download"""
import argparse
import errno
import hashlib
import logging
import os
import sys
from collections import namedtuple
from enum import Enum, unique
from io import StringIO
from multiprocessing import Pool

import requests

from .summary import SummaryReader

# Python < 2.7.9 hack: fix ssl support
if sys.version_info < (2, 7, 9):  # pragma: no cover
    from requests.packages.urllib3.contrib import pyopenssl
    pyopenssl.inject_into_urllib3()

SUPPORTED_TAXONOMIC_GROUPS = ['archaea', 'bacteria', 'fungi', 'invertebrate', 'plant', 'protozoa',
                              'unknown', 'vertebrate_mammalian', 'vertebrate_other', 'viral']


@unique
class EMap(Enum):
    """
    Enumeration of (`key`, `content`) pairs. The name `content` is used, because `value` is
     already an attribute of the Enum instances.
     We use an enumeration to ensure the immutability of the elements.
    """

    def __init__(self, key, content):
        """

        Parameters
        ----------
        key : str
        content : object
        """
        self.key = key
        self.content = content

    @classmethod
    def keys(cls):
        """
        Simulate dict.keys() on this enumeration map

        Returns
        -------
        list
            containing all the keys of this map enumeration
        """
        if not hasattr(cls, '_keys'):
            keys = []
            for _, member in cls.__members__.items():
                keys.append(member.key)
            cls._keys = keys
        return cls._keys

    @classmethod
    def items(cls):
        """
        Simulate dict.items() on this enumeration map

        Returns
        -------
        list of tuple
        """
        if not hasattr(cls, '_items'):
            items = []
            for _, member in cls.__members__.items():
                items.append((member.key, member.content))
            cls._items = items
        return cls._items

    @classmethod
    def get_content(cls, key):
        """
        Shortcut to get the content value for the enumeration map item with the given `key`.

        Parameters
        ----------
        key : str

        Returns
        -------
        type(content)

        """
        if not hasattr(cls, '_as_dict'):
            as_dict = {}
            for emap in list(cls):
                as_dict.update({emap.key: emap.content})
            cls._as_dict = as_dict
        return cls._as_dict[key]


class EFormats(EMap):
    # only needed in Python 2
    __order__ = 'GENBANK FASTA FEATURES GFF PROTFASTA GENREPT WGS CDSFASTA RNAFASTA ASSEMBLYREPORT ASSEMBLYSTATS'
    GENBANK = ('genbank', '_genomic.gbff.gz')
    FASTA = ('fasta', '_genomic.fna.gz')
    FEATURES = ('features', '_feature_table.txt.gz')
    GFF = ('gff', '_genomic.gff.gz')
    PROTFASTA = ('protein-fasta', '_protein.faa.gz')
    GENREPT = ('genpept', '_protein.gpff.gz')
    WGS = ('wgs', '_wgsmaster.gbff.gz')
    CDSFASTA = ('cds-fasta', '_cds_from_genomic.fna.gz')
    RNAFASTA = ('rna-fasta', '_rna_from_genomic.fna.gz')
    ASSEMBLYREPORT = ('assembly-report', '_assembly_report.txt')
    ASSEMBLYSTATS = ('assembly-stats', '_assembly_stats.txt')


class EAssemblyLevels(EMap):
    __order__ = 'COMPLETE CHROMOSOME SCAFFOLD CONTIG'  # only needed in Python 2
    COMPLETE = ('complete', 'Complete Genome')
    CHROMOSOME = ('chromosome', 'Chromosome')
    SCAFFOLD = ('scaffold', 'Scaffold')
    CONTIG = ('contig', 'Contig')


class ERefseqCategories(EMap):
    __order__ = 'REFERENCE REPRESENTATIVE'
    REFERENCE = ('reference', 'reference genome')
    REPRESENTATIVE = ('representative', 'representative genome')


class EDefaults(Enum):
    TAXONOMIC_GROUPS = ['all'] + SUPPORTED_TAXONOMIC_GROUPS
    SECTIONS = ['refseq', 'genbank']
    FORMATS = list(EFormats.keys()) + ['all']
    ASSEMBLY_LEVELS = ['all'] + list(EAssemblyLevels.keys())
    REFSEQ_CATEGORIES = ['all'] + list(ERefseqCategories.keys())
    GENUS = None
    SPECIES_TAXID = None
    TAXID = None
    OUTPUT = os.getcwd()
    URI = 'https://ftp.ncbi.nih.gov/genomes'
    NB_PROCESSES = 1
    TABLE = None

    @property
    def default(self):
        return self.value[0] if isinstance(self.value, list) else self.value

    @property
    def choices(self):
        return self.value if isinstance(self.value, list) else None


DownloadJob = namedtuple('DownloadJob',
                         ['full_url', 'local_file', 'expected_checksum', 'symlink_path'])


def argument_parser(version=None):
    """Argument parser for ncbi-genome-download"""
    parser = argparse.ArgumentParser()
    parser.add_argument('group',
                        default=EDefaults.TAXONOMIC_GROUPS.default,
                        help='The NCBI taxonomic group to download (default: %(default)s). '
                        'A comma-separated list of taxonomic groups is also possible. For example: "bacteria,viral"'
                        'Choose from: {choices}'.format(choices=EDefaults.TAXONOMIC_GROUPS.choices))
    parser.add_argument('-s', '--section', dest='section',
                        choices=EDefaults.SECTIONS.choices,
                        default=EDefaults.SECTIONS.default,
                        help='NCBI section to download (default: %(default)s)')
    parser.add_argument('-F', '--format', dest='file_format',
                        default=EDefaults.FORMATS.default,
                        help='Which format to download (default: %(default)s).'
                        'A comma-separated list of formats is also possible. For example: "fasta,assembly-report". '
                        'Choose from: {choices}'.format(choices=EDefaults.FORMATS.choices))
    parser.add_argument('-l', '--assembly-level', dest='assembly_level',
                        choices=EDefaults.ASSEMBLY_LEVELS.choices,
                        default=EDefaults.ASSEMBLY_LEVELS.default,
                        help='Assembly level of genomes to download (default: %(default)s)')
    parser.add_argument('-g', '--genus', dest='genus',
                        default=EDefaults.GENUS.default,
                        help='Only download sequences of the provided genus. '
                        'A comma-seperated list of genera is also possible. For example: "Streptomyces coelicolor,Escherichia coli".'
                        '(default: %(default)s)')
    parser.add_argument('-T', '--species-taxid', dest='species_taxid',
                        default=EDefaults.SPECIES_TAXID.default,
                        help='Only download sequences of the provided species NCBI taxonomy ID. '
                             'A comma-separated list of species taxids is also possible. For example: "52342,12325". '
                             '(default: %(default)s)')
    parser.add_argument('-t', '--taxid', dest='taxid',
                        default=EDefaults.TAXID.default,
                        help='Only download sequences of the provided NCBI taxonomy ID. '
                             'A comma-separated list of taxids is also possible. For example: "9606,9685". '
                             '(default: %(default)s)')
    parser.add_argument('-R', '--refseq-category', dest='refseq_category',
                        choices=EDefaults.REFSEQ_CATEGORIES.choices,
                        default=EDefaults.REFSEQ_CATEGORIES.default,
                        help='Only download sequences of the provided refseq category (default: %(default)s)')
    parser.add_argument('-o', '--output-folder', dest='output',
                        default=EDefaults.OUTPUT.default,
                        help='Create output hierarchy in specified folder (default: %(default)s)')
    parser.add_argument('-H', '--human-readable', dest='human_readable', action='store_true',
                        help='Create links in human-readable hierarchy (might fail on Windows)')
    parser.add_argument('-u', '--uri', dest='uri',
                        default=EDefaults.URI.default,
                        help='NCBI base URI to use (default: %(default)s)')
    parser.add_argument('-p', '--parallel', dest='parallel', type=int, metavar="N",
                        default=EDefaults.NB_PROCESSES.default,
                        help='Run %(metavar)s downloads in parallel (default: %(default)s)')
    parser.add_argument('-r', '--retries', dest='retries', type=int, metavar="N",
                        default=0,
                        help='Retry download %(metavar)s times when connection to NCBI fails ('
                             'default: %(default)s)')
    parser.add_argument('-m', '--metadata-table', type=str,
                        help='Save tab-delimited file with genome metadata')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='increase output verbosity')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='print debugging information')
    parser.add_argument('-V', '--version', action='version', version=version,
                        help='print version information')
    return parser


def download(**kwargs):
    """
    Download data from NCBI
    Parameters
    ----------
    section : str
        NCBI directory
    group : str
        Taxonomic group
    uri : str
    output : str
        directory in which to save the downloaded files
    file_format : str
        of the saved files
    assembly_level : str
        as defined by NCBI
    refseq_category: str
        as defined by NCBI
    genus : str
        "organism_name" in NCBI
    species_taxid : str
        as defined by NCBI
    taxid : str
        as defined by NCBI
    human_readable : bool
    parallel: int
        to use multiprocessing for requests
    table : str
        file to store metadata
    Returns
    -------
    int
        success code
    """
    # Parse and pre-process keyword arguments
    args = argparse.Namespace()

    args.section = kwargs.pop('section', EDefaults.SECTIONS.default)
    args.uri = kwargs.pop('uri', EDefaults.URI.default)
    args.output = kwargs.pop('output', EDefaults.OUTPUT.default)
    args.file_format = kwargs.pop('file_format', EDefaults.FORMATS.default)
    args.assembly_level = kwargs.pop('assembly_level', EDefaults.ASSEMBLY_LEVELS.default)
    args.refseq_category = kwargs.pop('refseq_category', EDefaults.REFSEQ_CATEGORIES.default)
    args.genus = kwargs.pop('genus', EDefaults.GENUS.default)
    args.species_taxid = kwargs.pop('species_taxid', EDefaults.SPECIES_TAXID.default)
    args.taxid = kwargs.pop('taxid', EDefaults.TAXID.default)
    args.human_readable = kwargs.pop('human_readable', False)
    args.parallel = kwargs.pop('parallel', EDefaults.NB_PROCESSES.default)
    args.metadata_table = kwargs.pop('metadata_table', EDefaults.TABLE.default)
    assert len(kwargs) == 0, "Unrecognized option(s): {}".format(kwargs.keys())

    return args_download(args)

def args_download(args):
    """
    Download data from NCBI
    Using the argument parser object.

    Parameters
    ----------
    args: Namespace
        Arguments from argument_parser
_
    Returns
    -------
    int
        success code

    """
    # Parse and pre-process keyword arguments

    assert args.section in EDefaults.SECTIONS.choices, "Unsupported section: {}".format(args.section)

    groups = args.group.split(',')

    for group in groups:
        assert group in EDefaults.TAXONOMIC_GROUPS.choices, "Unsupported group: {}".format(group)
    if 'all' in groups:
        groups = SUPPORTED_TAXONOMIC_GROUPS

    formats = args.file_format.split(',')
    for format in formats:
        assert format in EDefaults.FORMATS.choices, \
            "Unsupported file format: {file_format}".format(file_format=format)
    if 'all' in formats:
        formats = EFormats.keys()

    assert args.assembly_level in EDefaults.ASSEMBLY_LEVELS.choices, \
        "Unsupported assembly level: {}".format(args.assembly_level)
    assert args.refseq_category in EDefaults.REFSEQ_CATEGORIES.choices, \
        "Unsupported refseq_category: {}".format(args.refseq_category)

    if args.metadata_table:
        logging.info('Creating metadata file: %r', args.metadata_table)
        with open(args.metadata_table, 'wt') as metadata_table:
            metadata_table.write(get_table_header())

    if args.taxid:
        taxid_list = args.taxid.split(',')
    else:
        taxid_list = []
    if args.species_taxid:
        species_taxid_list = args.species_taxid.split(',')
    else:
        species_taxid_list = []

    if args.genus:
        genus_list = args.genus.split(',')
    else:
        genus_list = []

    # Actual logic
    try:
        download_jobs = []
        for group in groups:
            download_jobs.extend(
                _download(args.section, group, args.uri, args.output, formats, args.assembly_level, genus_list,
                          species_taxid_list, taxid_list, args.human_readable, args.refseq_category, args.metadata_table))

        pool = Pool(processes=args.parallel)
        jobs = pool.map_async(worker, download_jobs)
        try:
            # 0xFFFF is just "a really long time"
            jobs.get(0xFFFF)
        except KeyboardInterrupt:  # pragma: no cover
            # TODO: Actually test this once I figure out how to do this in py.test
            logging.error("Interrupted by user")
            return 1


    except requests.exceptions.ConnectionError as err:
        logging.error('Download from NCBI failed: %r', err)
        # Exit code 75 meas TEMPFAIL in C/C++, so let's stick with that for now.
        return 75
    return 0


# pylint and I disagree on code style here. Shut up, pylint.
# pylint: disable=too-many-arguments
def _download(section, group, uri, output, file_formats, assembly_level, genera, species_taxids,
              taxids, human_readable, refseq_category, table):
    """
    Sole purpose is to ease the tests, no argument checking is done here: they must be processed
    previously.
    You *SHALL NOT* call this directly, but always call download()!

    Parameters
    ----------
    section
    group
    uri
    output
    file_formats
    assembly_level
    genus
    species_taxids
    taxids
    human_readable
    refseq_category

    Returns
    -------
    list of DownloadJob

    """
    summary_file = get_summary(section, group, uri)
    entries = parse_summary(summary_file)
    download_jobs = []
    def in_genus_list(species, genus_list):
        for genus in genus_list:
            if species.startswith(genus.capitalize()):
                return True
        return False

    for entry in entries:
        if genera and not in_genus_list(entry['organism_name'],genera):
            logging.debug('Organism name %r does not start with any in %r, skipping',
                          entry['organism_name'], genera)
            continue
        if species_taxids and entry['species_taxid'] not in species_taxids:
            logging.debug('Species TaxID %r does not match with any in %r, skipping',
                          entry['species_taxid'], species_taxids)
            continue
        if taxids and entry['taxid'] not in taxids:
            logging.debug('Organism TaxID %r does not match with any in %r, skipping',
                          entry['taxid'], taxids)
            continue
        if assembly_level != 'all' \
                and entry['assembly_level'] != EAssemblyLevels.get_content(assembly_level):
            logging.debug('Skipping entry with assembly level %r', entry['assembly_level'])
            continue
        if refseq_category != 'all' and entry['refseq_category'] != ERefseqCategories.get_content(refseq_category):
            logging.debug('Skipping entry with refseq_category %r, not %r', entry['refseq_category'], refseq_category)
            continue
        download_jobs.extend(
            download_entry(entry, section, group, output, file_formats, human_readable, table))
    return download_jobs
# pylint: enable=too-many-arguments


def worker(job):
    """Run a single download job"""
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


def get_summary(section, domain, uri):
    """Get the assembly_summary.txt file from NCBI and return a StringIO object for it"""
    logging.debug('Downloading summary for %r/%r uri: %r', section, domain, uri)
    url = '{uri}/{section}/{domain}/assembly_summary.txt'.format(
        section=section, domain=domain, uri=uri)
    req = requests.get(url)
    return StringIO(req.text)


def parse_summary(summary_file):
    """Parse the summary file from TSV format to a csv DictReader"""
    return SummaryReader(summary_file)


# pylint and I disagree on code style here. Shut up, pylint.
# pylint: disable=too-many-arguments
def download_entry(entry, section, domain, output, file_formats, human_readable, table=None):
    """Download an entry from the summary file"""
    logging.info('Downloading record %r', entry['assembly_accession'])
    full_output_dir = create_dir(entry, section, domain, output)

    symlink_path = None
    if human_readable:
        symlink_path = create_readable_dir(entry, section, domain, output)

    checksums = grab_checksums_file(entry)

    # TODO: Only write this when the checksums file changed
    with open(os.path.join(full_output_dir, 'MD5SUMS'), 'w') as handle:
        handle.write(checksums)

    parsed_checksums = parse_checksums(checksums)

    download_jobs = []
    for fmt in file_formats:
        try:
            if has_file_changed(full_output_dir, parsed_checksums, fmt):
                download_jobs.append(
                    download_file_job(entry, full_output_dir, parsed_checksums, fmt, symlink_path, table))
            elif need_to_create_symlink(full_output_dir, parsed_checksums, fmt, symlink_path):
                download_jobs.append(
                    create_symlink_job(full_output_dir, parsed_checksums, fmt, symlink_path))
        except ValueError as err:
            logging.error(err)

    return download_jobs
# pylint: enable=too-many-arguments


def create_dir(entry, section, domain, output):
    """Create the output directory for the entry if needed"""
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
    """Create the a human-readable directory to link the entry to if needed"""
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
    """Grab the checksum file for a given entry"""
    http_url = convert_ftp_url(entry['ftp_path'])
    full_url = '{}/md5checksums.txt'.format(http_url)
    req = requests.get(full_url)
    return req.text


def convert_ftp_url(url):
    """Convert FTP to HTTPS URLs"""
    return url.replace('ftp://', 'https://', 1)


def parse_checksums(checksums_string):
    """Parse a file containing checksums and filenames"""
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
    """Check if the checksum of a given file has changed"""
    pattern = EFormats.get_content(filetype)
    filename, expected_checksum = get_name_and_checksum(checksums, pattern)
    full_filename = os.path.join(directory, filename)
    # if file doesn't exist, it has changed
    if not os.path.isfile(full_filename):
        return True

    actual_checksum = md5sum(full_filename)
    return expected_checksum != actual_checksum


def need_to_create_symlink(directory, checksums, filetype, symlink_path):
    """Check if we need to create a symlink for an existing file"""
    # If we don't have a symlink path, we don't need to create a symlink
    if symlink_path is None:
        return False

    pattern = EFormats.get_content(filetype)
    filename, _ = get_name_and_checksum(checksums, pattern)
    full_filename = os.path.join(directory, filename)
    symlink_name = os.path.join(symlink_path, filename)

    if os.path.islink(symlink_name):
        existing_link = os.readlink(symlink_name)
        if full_filename == existing_link:
            return False

    return True


def get_name_and_checksum(checksums, end):
    """Extract a full filename and checksum from the checksums list for a file ending in given end"""
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
    """Calculate the md5sum of a file and return the hexdigest"""
    hash_md5 = hashlib.md5()
    with open(filename, 'rb') as handle:
        for chunk in iter(lambda: handle.read(4096), b''):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def download_file_job(entry, directory, checksums, filetype='genbank', symlink_path=None, table=None):
    """Download and verirfy a given file"""
    pattern = EFormats.get_content(filetype)
    filename, expected_checksum = get_name_and_checksum(checksums, pattern)
    base_url = convert_ftp_url(entry['ftp_path'])
    full_url = '{}/{}'.format(base_url, filename)
    local_file = os.path.join(directory, filename)
    full_symlink = None
    if symlink_path is not None:
        full_symlink = os.path.join(symlink_path, filename)

    if table is not None:
        write_table_line(entry, table, local_file)

    return DownloadJob(full_url, local_file, expected_checksum, full_symlink)


def create_symlink_job(directory, checksums, filetype, symlink_path):
    """Create a symlink for an already downloaded file"""
    pattern = EFormats.get_content(filetype)
    filename, _ = get_name_and_checksum(checksums, pattern)
    local_file = os.path.join(directory, filename)
    full_symlink = os.path.join(symlink_path, filename)
    return DownloadJob(None, local_file, None, full_symlink)


def save_and_check(response, local_file, expected_checksum):
    """Save the content of an http response and verify the checksum matches"""

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
    """Create a symlink if symlink path is given"""
    if symlink_path is not None:
        if os.path.exists(symlink_path) or os.path.lexists(symlink_path):
            os.unlink(symlink_path)

        os.symlink(os.path.abspath(local_file), symlink_path)

    return True


def get_genus_label(entry):
    """Get the genus name of an assembly summary entry"""
    return entry['organism_name'].split(' ')[0]


def get_species_label(entry):
    """Get the species name of an assembly summary entry"""
    return entry['organism_name'].split(' ')[1]


def get_strain_label(entry, viral=False):
    """Try to extract a strain from an assemly summary entry

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


def get_table_header():
    header_parts = ['assembly_accession',
                    'bioproject',
                    'biosample',
                    'wgs_master',
                    'excluded_from_refseq',
                    'refseq_category',
                    'relation_to_type_material',
                    'taxid',
                    'species_taxid',
                    'organism_name',
                    'infraspecific_name',
                    'isolate',
                    'version_status',
                    'assembly_level',
                    'release_type',
                    'genome_rep',
                    'seq_rel_date',
                    'asm_name',
                    'submitter',
                    'gbrs_paired_asm',
                    'paired_asm_comp',
                    'ftp_path',
                    'local_filename']
    return '\t'.join(header_parts) + '\n'


def get_table_line(entry, genome_filename):
    line_parts = [entry.get('assembly_accession', ''),
                  entry.get('bioproject', ''),
                  entry.get('biosample', ''),
                  entry.get('wgs_master', ''),
                  entry.get('excluded_from_refseq', ''),
                  entry.get('refseq_category', ''),
                  entry.get('relation_to_type_material', ''),
                  entry.get('taxid', ''),
                  entry.get('species_taxid', ''),
                  entry.get('organism_name', ''),
                  entry.get('infraspecific_name', ''),
                  entry.get('isolate', ''),
                  entry.get('version_status', ''),
                  entry.get('assembly_level', ''),
                  entry.get('release_type', ''),
                  entry.get('genome_rep', ''),
                  entry.get('seq_rel_date', ''),
                  entry.get('asm_name', ''),
                  entry.get('submitter', ''),
                  entry.get('gbrs_paired_asm', ''),
                  entry.get('paired_asm_comp', ''),
                  entry.get('ftp_path', ''),
                  './' + os.path.relpath(genome_filename)]
    return '\t'.join(line_parts) + '\n'


def write_table_line(entry, table_filename, genome_filename):
    with open(table_filename, 'at') as metadata_table:
        table_line = get_table_line(entry, genome_filename)
        try:
            metadata_table.write(table_line)
        except UnicodeEncodeError:
            ascii_table_line = ''.join([i if ord(i) < 128 else '?' for i in table_line])
            metadata_table.write(ascii_table_line)
