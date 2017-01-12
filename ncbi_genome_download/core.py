'''Core functionality of ncbi-genome-download'''
import errno
import hashlib
import logging
import os
import sys
from io import StringIO
from collections import namedtuple
from multiprocessing import Pool
from ncbi_genome_download.summary import SummaryReader

import requests

# Python < 2.7.9 hack: fix ssl support
if sys.version_info < (2, 7, 9):  # pragma: no cover
    from requests.packages.urllib3.contrib import pyopenssl
    pyopenssl.inject_into_urllib3()


NCBI_URI = 'https://ftp.ncbi.nih.gov/genomes'
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


DownloadJob = namedtuple('DownloadJob', ['full_url', 'local_file', 'expected_checksum', 'symlink_path'])


def download(args):
    '''Download data from NCBI'''
    try:
        if args.domain == 'all':
            for domain in SUPPORTED_DOMAINS:
                _download(args.section, domain, args.uri, args.output, args.file_format,
                          args.assembly_level, args.genus, args.species_taxid,
                          args.taxid, args.human_readable, args.parallel)
        else:
            _download(args.section, args.domain, args.uri, args.output, args.file_format,
                      args.assembly_level, args.genus, args.species_taxid,
                      args.taxid, args.human_readable, args.parallel)
    except requests.exceptions.ConnectionError as err:
        logging.error('Download from NCBI failed: %r', err)
        # Exit code 75 meas TEMPFAIL in C/C++, so let's stick with that for now.
        return 75
    return 0


# pylint: disable=too-many-arguments
def _download(section, domain, uri, output, file_format, assembly_level, genus='',
              species_taxid=None, taxid=None, human_readable=False, parallel=1):
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
        download_jobs.extend(download_entry(entry, section, domain, output, file_format, human_readable))

    pool = Pool(processes=parallel)
    pool.map(worker, download_jobs)
# pylint: enable=too-many-arguments


def worker(job):
    '''Run a single download job'''
    if job.full_url is not None:
        req = requests.get(job.full_url, stream=True)
        ret = save_and_check(req, job.local_file, job.expected_checksum)
        if not ret:
            return ret
    return create_symlink(job.local_file, job.symlink_path)


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


def download_entry(entry, section, domain, output, file_format, human_readable):
    '''Download an entry from the summary file'''
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

    if file_format == 'all':
        formats = FORMAT_NAME_MAP.keys()
    else:
        formats = [file_format]

    download_jobs = []
    for fmt in formats:
        try:
            if has_file_changed(full_output_dir, parsed_checksums, fmt):
                download_jobs.append(download_file_job(entry, full_output_dir, parsed_checksums, fmt, symlink_path))
            elif need_to_create_symlink(full_output_dir, parsed_checksums, fmt, symlink_path):
                download_jobs.append(create_symlink_job(full_output_dir, parsed_checksums, fmt, symlink_path))
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


def create_readable_dir(entry, section, domain, output):
    '''Create the a human-readable directory to link the entry to if needed'''
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
    '''Grab the checksum file for a given entry'''
    http_url = convert_ftp_url(entry['ftp_path'])
    full_url = '{}/md5checksums.txt'.format(http_url)
    req = requests.get(full_url)
    return req.text


def convert_ftp_url(url):
    '''Convert FTP to HTTPS URLs'''
    return url.replace('ftp://', 'https://', 1)


def parse_checksums(checksums_string):
    '''Parse a file containing checksums and filenames'''
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
    '''Check if the checksum of a given file has changed'''
    pattern = FORMAT_NAME_MAP[filetype]
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

    pattern = FORMAT_NAME_MAP[filetype]
    filename, _ = get_name_and_checksum(checksums, pattern)
    full_filename = os.path.join(directory, filename)
    symlink_name = os.path.join(symlink_path, filename)

    if os.path.islink(symlink_name):
        existing_link = os.readlink(symlink_name)
        if full_filename == existing_link:
            return False

    return True


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


def download_file_job(entry, directory, checksums, filetype='genbank', symlink_path=None):
    '''Download and verirfy a given file'''
    pattern = FORMAT_NAME_MAP[filetype]
    filename, expected_checksum = get_name_and_checksum(checksums, pattern)
    base_url = convert_ftp_url(entry['ftp_path'])
    full_url = '{}/{}'.format(base_url, filename)
    local_file = os.path.join(directory, filename)
    full_symlink = None
    if symlink_path is not None:
        full_symlink = os.path.join(symlink_path, filename)

    return DownloadJob(full_url, local_file, expected_checksum, full_symlink)


def create_symlink_job(directory, checksums, filetype, symlink_path):
    """Create a symlink for an already downloaded file"""
    pattern = FORMAT_NAME_MAP[filetype]
    filename, _ = get_name_and_checksum(checksums, pattern)
    local_file = os.path.join(directory, filename)
    full_symlink = os.path.join(symlink_path, filename)
    return DownloadJob(None, local_file, None, full_symlink)


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


def create_symlink(local_file, symlink_path):
    """Create a symlink if symlink path is given"""
    if symlink_path is not None:
        if os.path.exists(symlink_path) or os.path.lexists(symlink_path):
            os.unlink(symlink_path)

        os.symlink(os.path.abspath(local_file), symlink_path)

    return True


def get_genus_label(entry):
    '''Get the genus name of an assembly summary entry'''
    return entry['organism_name'].split(' ')[0]


def get_species_label(entry):
    '''Get the species name of an assembly summary entry'''
    return entry['organism_name'].split(' ')[1]


def get_strain_label(entry, viral=False):
    '''Try to extract a strain from an assemly summary entry

    First this checks 'infraspecific_name', then 'isolate', then
    it tries to get it from 'organism_name'. If all fails, it
    falls back to just returning the assembly accesion number.
    '''
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
