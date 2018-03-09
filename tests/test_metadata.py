"""Tests for the metadata classes."""

import pytest

from io import StringIO

from ncbi_genome_download import metadata


def test_init():
    """Test initialising the MetaData object."""
    metadata.clear()
    with pytest.raises(ValueError):
        metadata.get(['alice', 'bob'])

    metadata.get()


def test_write():
    """Test writing the MetaData object."""
    metadata.clear()
    # Just some fake columns, and local_filename because that is required.
    mtable = metadata.get([u'foo', u'bar', u'local_filename'])
    fake_entry = dict(foo=u"foo_value", bar=u"bar_value")
    mtable.add(fake_entry, u'foo/bar/baz.gbk')
    handle  = StringIO()
    expected = u"""foo\tbar\tlocal_filename
foo_value\tbar_value\t./foo/bar/baz.gbk
"""

    mtable.write(handle)
    assert handle.getvalue() == expected
