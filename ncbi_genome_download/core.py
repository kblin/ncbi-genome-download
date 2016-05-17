import errno
import hashlib
import logging
import os
import requests
from io import StringIO

from ncbi_genome_download.summary import SummaryReader

NCBI_URI = 'http://ftp.ncbi.nih.gov/genomes'
supported_domains = ['archaea', 'bacteria', 'fungi', 'invertebrate', 'plant',
                     'protozoa', 'unknown', 'vertebrate_mammalian',
                     'vertebrate_other', 'viral']


format_name_map = {
    'genbank': '_genomic.gbff.gz',
    'fasta': '_genomic.fna.gz',
    'features': '_feature_table.txt.gz',
    'gff': '_genomic.gff.gz',
    'protein-fasta': '_protein.faa.gz',
    'genpept': '_protein.gbpff.gz',
    'wgs': '_wgsmaster.gbff.gz',
}

assembly_level_map = {
    'complete': 'Complete Genome',
    'scaffold': 'Scaffold',
    'contig': 'Contig'
}


def download(args):
    '''Download data from NCBI'''

    if args.domain == 'all':
        for domain in supported_domains:
            _download(args.section, domain, args.uri, args.output, args.file_format,
                      args.assembly_level, args.genus)
    else:
        _download(args.section, args.domain, args.uri, args.output, args.file_format,
                  args.assembly_level, args.genus)


def _download(section, domain, uri, output, file_format, assembly_level, genus=''):
    '''Download a specified domain form a section'''
    summary_file = get_summary(section, domain, uri)
    entries = parse_summary(summary_file)
    for entry in entries:
        if not entry['organism_name'].startswith(genus.capitalize()):
            logging.debug('Organism name %r does not start with %r as requested, skipping',
                          entry['organism_name'], genus)
            continue
        if assembly_level != 'all' and entry['assembly_level'] != assembly_level_map[assembly_level]:
            logging.debug('Skipping entry with assembly level %r', entry['assembly_level'])
            continue
        download_entry(entry, section, domain, uri, output, file_format)


def get_summary(section, domain, uri):
    '''Get the assembly_summary.txt file from NCBI and return a StringIO object for it'''
    logging.debug('Downloading summary for %r/%r uri: %r', section, domain, uri)
    url = '{uri}/{section}/{domain}/assembly_summary.txt'.format(
        section=section, domain=domain, uri=uri)
    r = requests.get(url)
    return StringIO(r.text)


def parse_summary(summary_file):
    '''Parse the summary file from TSV format to a csv DictReader'''
    return SummaryReader(summary_file)


def download_entry(entry, section, domain, uri, output, file_format):
    '''Download an entry from the summary file'''
    logging.info('Downloading record %r', entry['assembly_accession'])
    full_output_dir = create_dir(entry, section, domain, output)
    checksums = grab_checksums_file(entry)

    # TODO: Only write this when the checksums file changed
    with open(os.path.join(full_output_dir, 'MD5SUMS'), 'w') as fh:
        fh.write(checksums)

    parsed_checksums = parse_checksums(checksums)

    if file_format == 'all':
        formats = format_name_map.keys()
    else:
        formats = [file_format]

    for f in formats:
        try:
            if has_file_changed(full_output_dir, parsed_checksums, f):
                download_file(entry, full_output_dir, parsed_checksums, f)
        except ValueError as e:
            logging.error(e)


def create_dir(entry, section, domain, output):
    '''Create the output directory for the entry if needed'''
    full_output_dir = os.path.join(output, section, domain, entry['assembly_accession'])
    try:
        os.makedirs(full_output_dir)
    except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(full_output_dir):
            pass
        else:
            raise

    return full_output_dir


def grab_checksums_file(entry):
    '''Grab the checksum file for a given entry'''
    http_url = convert_ftp_url(entry['ftp_path'])
    full_url = '{}/md5checksums.txt'.format(http_url)
    r = requests.get(full_url)
    return r.text


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
    pattern = format_name_map[filetype]
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
        filename = entry['file']
        expected_checksum = entry['checksum']
        return filename, expected_checksum
    raise ValueError('No entry for file ending in {!r}'.format(end))


def md5sum(filename):
    '''Calculate the md5sum of a file and return the hexdigest'''
    hash_md5 = hashlib.md5()
    with open(filename, 'rb') as fh:
        for chunk in iter(lambda: fh.read(4096), b''):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def download_file(entry, directory, checksums, filetype='genbank'):
    '''Download and verirfy a given file'''
    pattern = format_name_map[filetype]
    filename, expected_checksum = get_name_and_checksum(checksums, pattern)
    base_url = convert_ftp_url(entry['ftp_path'])
    full_url = '{}/{}'.format(base_url, filename)
    local_file = os.path.join(directory, filename)

    r = requests.get(full_url, stream=True)

    with open(local_file, 'wb') as fh:
        for chunk in r.iter_content(4096):
            fh.write(chunk)

    actual_checksum = md5sum(local_file)
    if actual_checksum != expected_checksum:
        logging.error('Checksum mismatch for %r. Expected %r, got %r',
                      local_file, expected_checksum, actual_checksum)
        return False

    return True
