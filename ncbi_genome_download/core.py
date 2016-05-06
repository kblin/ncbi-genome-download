import csv
import errno
import hashlib
import logging
import os
import requests
from StringIO import StringIO

NCBI_URI = 'http://ftp.ncbi.nih.gov/genomes'
supported_domains = ['archaea', 'bacteria', 'fungi', 'invertebrate', 'plant',
                     'protozoa', 'unknown', 'vertebrate_mammalian',
                     'vertebrate_other', 'viral']


def download(args):
    '''Download data from NCBI'''
    if args.domain == 'all':
        for domain in supported_domains:
            _download(args.section, domain, args.uri, args.output)
    else:
        _download(args.section, args.domain, args.uri, args.output)


def _download(section, domain, uri, output):
    '''Download a specified domain form a section'''
    summary = get_summary(section, domain, uri)
    entries = parse_summary(summary)
    for entry in entries:
        download_entry(entry, section, domain, uri, output)


def get_summary(section, domain, uri):
    '''Get the assembly_summary.txt file from NCBI and return a StringIO object for it'''
    logging.debug('Downloading summary for %r/%r uri: %r', section, domain, uri)
    url = '{uri}/{section}/{domain}/assembly_summary.txt'.format(
        section=section, domain=domain, uri=uri)
    r = requests.get(url)
    return StringIO(r.content)


def parse_summary(summary):
    '''Parse the summary file from TSV format to a csv DictReader'''
    # skip the leading 2 comment characters in the header to get nicer names
    comment = summary.read(2)
    if comment != '# ':
        # Huh, unexpected header, just go back to whereever we were before
        idx = summary.tell()
        summary.seek(max(0, idx - 2))

    reader = csv.DictReader(summary, dialect='excel-tab')
    return reader


def download_entry(entry, section, domain, uri, output):
    '''Download an entry from the summary file'''
    logging.info('Downloading record %r', entry['assembly_accession'])
    full_output_dir = create_dir(entry, section, domain, output)
    checksums = grab_checksums_file(entry)

    # TODO: Only write this when the checksums file changed
    with open(os.path.join(full_output_dir, 'MD5SUMS'), 'w') as fh:
        fh.write(checksums)

    parsed_checksums = parse_checksums(checksums)
    if has_gbk_file_changed(full_output_dir, parsed_checksums):
        download_gbk_file(entry, full_output_dir, parsed_checksums)


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


def has_gbk_file_changed(directory, checksums):
    '''Check if the checksum of a given gbk file has changed'''
    filename, expected_checksum = get_name_and_checksum(checksums, '_genomic.gbff.gz')
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


def md5sum(filename):
    '''Calculate the md5sum of a file and return the hexdigest'''
    hash_md5 = hashlib.md5()
    with open(filename, 'rb') as fh:
        for chunk in iter(lambda: fh.read(4096), b''):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def download_gbk_file(entry, directory, checksums):
    '''Download and verirfy a given gbk file'''
    filename, expected_checksum = get_name_and_checksum(checksums, '_genomic.gbff.gz')
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
