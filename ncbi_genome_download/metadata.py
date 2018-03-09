"""Keep track of download entry metadata."""
import os

_METADATA = None
_DEFAULT_COLUMNS = [
    'assembly_accession',
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
    'local_filename',
]


def get(columns=None):
    """Get or create MetaData singleton."""
    if columns is None:
        columns = _DEFAULT_COLUMNS

    global _METADATA
    if not _METADATA:
        _METADATA = MetaData(columns)

    return _METADATA


def clear():
    """Clear the MetaData singleton."""
    global _METADATA
    _METADATA = None


class MetaData(object):
    """Singleton tracking download entry metadata."""

    def __init__(self, columns):
        """Initialise the columns of metadata to store."""
        if 'local_filename' not in columns:
            raise ValueError("No 'local_filename' column specified for metadata table")

        self.columns = columns

        class MetaDataRow(object):
            """A row of metadata."""

            __slots__ = columns

            def write(self, handle):
                """Write metadata row to handle."""
                values = []
                for col in self.__slots__:
                    values.append(getattr(self, col, ''))
                handle.write(u"\t".join(values))
                handle.write(u"\n")

        self.rowClass = MetaDataRow
        self.rows = []

    def add(self, entry, local_file):
        """Add a metadata row."""
        row = self.rowClass()

        for key, val in entry.items():
            if key in self.columns:
                setattr(row, key, val)

        row.local_filename = os.path.join('.', os.path.relpath(local_file))

        self.rows.append(row)

    def write(self, handle):
        """Write metadata to handle."""
        handle.write(u"\t".join(self.columns))
        handle.write(u"\n")
        for row in self.rows:
            row.write(handle)
