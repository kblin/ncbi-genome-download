"""Module for download and symlink jobs."""


class DownloadJob(object):
    """Collection of data for a download job."""

    __slots__ = ['full_url', 'local_file', 'expected_checksum', 'symlink_path']

    def __init__(self, full_url, local_file, expected_checksum, symlink_path):
        """Initialise the download job."""
        self.full_url = full_url
        self.local_file = local_file
        self.expected_checksum = expected_checksum
        self.symlink_path = symlink_path

    def __eq__(self, other):
        """Check for equality."""
        if not isinstance(other, DownloadJob):
            return False

        return self.full_url == other.full_url and \
            self.local_file == other.local_file and \
            self.expected_checksum == other.expected_checksum and \
            self.symlink_path == other.symlink_path
