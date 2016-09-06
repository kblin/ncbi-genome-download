'''Core functionality of ncbi-genome-download'''
import errno
import hashlib
import logging
import os
from io import StringIO
from collections import namedtuple
from multiprocessing import Pool
import requests
from ncbi_genome_download.summary import SummaryReader

NCBI_URI = 'http://ftp.ncbi.nih.gov/genomes'
SUPPORTED_DOMAINS = ['archaea', 'bacteria', 'fungi', 'invertebrate', 'plant',
                     'protozoa', 'unknown', 'vertebrate_mammalian',
                     'vertebrate_other', 'viral']


FORMAT_NAME_MAP = {
    'genbank': '_genomic.gbff.gz',
    'fasta': '_genomic.fna.gz',
    'features': '_feature_table.txt.gz',
    'gff': '_genomic.gff.gz',
    'protein-fasta': '_protein.faa.gz',
    'genpept': '_protein.gpff.gz',
    'wgs': '_wgsmaster.gbff.gz',
    'cds-fasta': '_cds_from_genomic.fna.gz',
    'rna-fasta': '_rna_from_genomic.fna.gz',
}

ASSEMBLY_LEVEL_MAP = {
    'complete': 'Complete Genome',
    'chromosome': 'Chromosome',
    'scaffold': 'Scaffold',
    'contig': 'Contig'
}


DownloadJob = namedtuple('DownloadJob', ['full_url', 'local_file', 'expected_checksum'])


def download(args):
    '''Download data from NCBI'''

    if args.domain == 'all':
        for domain in SUPPORTED_DOMAINS:
            _download(args.section, domain, args.uri, args.output, args.file_format,
                      args.assembly_level, args.genus, args.species_taxid,
                      args.taxid, args.parallel)
    else:
        _download(args.section, args.domain, args.uri, args.output, args.file_format,
                  args.assembly_level, args.genus, args.species_taxid,
                  args.taxid, args.parallel)


# pylint: disable=too-many-arguments
def _download(section, domain, uri, output, file_format, assembly_level, genus='',
              species_taxid=None, taxid=None, parallel=1):
    '''Download a specified domain form a section'''
    summary_file = get_summary(section, domain, uri)
    entries = parse_summary(summary_file)
    download_jobs = []
    for entry in entries:
        if not entry['organism_name'].startswith(genus.capitalize()):
            logging.debug('Organism name %r does not start with %r as requested, skipping',
                          entry['organism_name'], genus)
            continue
        if species_taxid is not None and entry['species_taxid'] != species_taxid:
            logging.debug('Species TaxID %r different from the one provided %r, skipping',
                          entry['species_taxid'], species_taxid)
            continue
        if taxid is not None and entry['taxid'] != taxid:
            logging.debug('Organism TaxID %r different from the one provided %r, skipping',
                          entry['taxid'], taxid)
            continue
        if assembly_level != 'all' and entry['assembly_level'] != ASSEMBLY_LEVEL_MAP[assembly_level]:
            logging.debug('Skipping entry with assembly level %r', entry['assembly_level'])
            continue
        download_jobs.extend(download_entry(entry, section, domain, output, file_format))

    pool = Pool(processes=parallel)
    pool.map(worker, download_jobs)
# pylint: enable=too-many-arguments


def worker(job):
    '''Run a single download job'''
    req = requests.get(job.full_url, stream=True)
    return save_and_check(req, job.local_file, job.expected_checksum)


def get_summary(section, domain, uri):
    '''Get the assembly_summary.txt file from NCBI and return a StringIO object for it'''
    logging.debug('Downloading summary for %r/%r uri: %r', section, domain, uri)
    url = '{uri}/{section}/{domain}/assembly_summary.txt'.format(
        section=section, domain=domain, uri=uri)
    req = requests.get(url)
    return StringIO(req.text)


def parse_summary(summary_file):
    '''Parse the summary file from TSV format to a csv DictReader'''
    return SummaryReader(summary_file)


def download_entry(entry, section, domain, output, file_format):
    '''Download an entry from the summary file'''
    logging.info('Downloading record %r', entry['assembly_accession'])
    full_output_dir = create_dir(entry, section, domain, output)
    checksums = grab_checksums_file(entry)

    # TODO: Only write this when the checksums file changed
    with open(os.path.join(full_output_dir, 'MD5SUMS'), 'w') as handle:
        handle.write(checksums)

    parsed_checksums = parse_checksums(checksums)

    if file_format == 'all':
        formats = FORMAT_NAME_MAP.keys()
    else:
        formats = [file_format]

    download_jobs = []
    for fmt in formats:
        try:
            if has_file_changed(full_output_dir, parsed_checksums, fmt):
                download_jobs.append(download_file(entry, full_output_dir, parsed_checksums, fmt))
        except ValueError as err:
            logging.error(err)

    return download_jobs


def create_dir(entry, section, domain, output):
    '''Create the output directory for the entry if needed'''
    full_output_dir = os.path.join(output, section, domain, entry['assembly_accession'])
    try:
        os.makedirs(full_output_dir)
    except OSError as err:
        if err.errno == errno.EEXIST and os.path.isdir(full_output_dir):
            pass
        else:
            raise

    return full_output_dir


def grab_checksums_file(entry):
    '''Grab the checksum file for a given entry'''
    http_url = convert_ftp_url(entry['ftp_path'])
    full_url = '{}/md5checksums.txt'.format(http_url)
    req = requests.get(full_url)
    return req.text


def convert_ftp_url(url):
    '''Convert FTP to HTTP URLs'''
    return url.replace('ftp://', 'http://', 1)


def parse_checksums(checksums_string):
    '''Parse a file containing checksums and filenames'''
    checksums_list = []
    for line in checksums_string.split('\n'):
        try:
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
    '''Check if the checksum of a given file has changed'''
    pattern = FORMAT_NAME_MAP[filetype]
    filename, expected_checksum = get_name_and_checksum(checksums, pattern)
    full_filename = os.path.join(directory, filename)
    # if file doesn't exist, it has changed
    if not os.path.isfile(full_filename):
        return True

    actual_checksum = md5sum(full_filename)
    return expected_checksum != actual_checksum


def get_name_and_checksum(checksums, end):
    '''Extract a full filename and checksum from the checksums list for a file ending in given end'''
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
    '''Calculate the md5sum of a file and return the hexdigest'''
    hash_md5 = hashlib.md5()
    with open(filename, 'rb') as handle:
        for chunk in iter(lambda: handle.read(4096), b''):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def download_file(entry, directory, checksums, filetype='genbank'):
    '''Download and verirfy a given file'''
    pattern = FORMAT_NAME_MAP[filetype]
    filename, expected_checksum = get_name_and_checksum(checksums, pattern)
    base_url = convert_ftp_url(entry['ftp_path'])
    full_url = '{}/{}'.format(base_url, filename)
    local_file = os.path.join(directory, filename)

    return DownloadJob(full_url, local_file, expected_checksum)


def save_and_check(response, local_file, expected_checksum):
    '''Save the content of an http response and verify the checksum matches'''

    with open(local_file, 'wb') as handle:
        for chunk in response.iter_content(4096):
            handle.write(chunk)

    actual_checksum = md5sum(local_file)
    if actual_checksum != expected_checksum:
        logging.error('Checksum mismatch for %r. Expected %r, got %r',
                      local_file, expected_checksum, actual_checksum)
        return False

    return True
