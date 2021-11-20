#!/usr/bin/env python3

"""
Perform various queries and tasks with the NCBI taxonomy database,
via the ETE3 toolkit.

Depends on ETE3 (obviously).

"""

__author__ = "Joe R. J. Healey; Nick Youngblut"
__version__ = "1.1"
__title__ = "gimme_taxa"
__license__ = "Apache2.0"
__author_email__ = "jrj.healey@gmail.com"


# Check script compatibilities and module requirements
import sys
import argparse
try:
    from ete3 import NCBITaxa
except ImportError as exc:

    # There are other reasons why this import may fail
    # Thus make sure to print the import error as well.
    msg = """
The ete3 import failed, the module doesn't appear to be installed
(at least in the PYTHONPATH for this python binary").

Try running:
 $ python -m pip install ete3 six

or

 $ conda install -c etetoolkit ete3 ete_toolchain

Exception: %s
""" % exc
    print(msg)
    sys.exit(1)


def get_args():
    """Parse command line arguments
    """
    desc = 'Perform queries against the NCBI Taxa database'
    epi = """DESCRIPTION:
    This script lets you find out what TaxIDs to pass to ngd, and will write
    a simple one-item-per-line file to pass in to it. It utilises the ete3
    toolkit, so refer to their site to install the dependency if it's not
    already satisfied.

    You can query the database using a particular TaxID, or a scientific name.
    The primary function of the script is to return all the child taxa of the
    specified parent taxa. If specified with -v verbose flags however, the
    script will also print out some information about the lineages etc.

    WARNING: This script is still somewhat experimental
    """
    parser = argparse.ArgumentParser(description=desc, epilog=epi,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('taxid', metavar='taxid', type=str,
                        help='A comma-separated list of TaxIDs and/or taxon names. (e.g. 561,2172)')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='Verbose behaviour. Supports 3 levels at present: Off = 0, Info = 1, Verbose = 2. (default: %(default)s)')  # noqa: E501
    parser.add_argument('-d', '--database', type=str, default=None,
                        help='NCBI taxonomy database file path. If "None", it will be downloaded (default: %(default)s)')  # noqa: E501
    parser.add_argument('-u', '--update', action='store_true', default=False,
                        help='Update the local taxon database before querying. Recommended if not used for a while. (default: %(default)s)')  # noqa: E501
    parser.add_argument('-j', '--just-taxids', action='store_true', default=False,
                        help='Just write out a list of taxids an no other information (default: %(default)s)')
    parser.add_argument('-i', '--taxon-info', action='store_true', default=False,
                        help='Just write out rank & lineage info on the provided taxids (default: %(default)s)')
    parser.add_argument('-o', '--outfile', action='store',
                        help='Output file to store the descendent TaxIDs for the query.')
    return parser.parse_args()


def desc_taxa(taxid, ncbi, outFH, just_taxids=False):
    """Write descendent taxa for taxid
    """
    # Main feature of the script is to get all taxa within a given group.
    descendent_taxa = ncbi.get_descendant_taxa(taxid)
    descendent_taxa_names = ncbi.translate_to_names(descendent_taxa)

    if just_taxids:
        for taxid in descendent_taxa:
            outFH.write(str(taxid) + '\n')
    else:
        for dtn, dt in zip(descendent_taxa_names, descendent_taxa):
            x = [str(x) for x in [taxid, dt, dtn]]
            outFH.write('\t'.join(x) + '\n')


def taxon_info(taxid, ncbi, outFH):
    """Write info on taxid
    """
    taxid = int(taxid)
    tax_name = ncbi.get_taxid_translator([taxid])[taxid]
    rank = list(ncbi.get_rank([taxid]).values())[0]
    lineage = ncbi.get_taxid_translator(ncbi.get_lineage(taxid))
    lineage = ['{}:{}'.format(k, v) for k, v in lineage.items()]
    lineage = ';'.join(lineage)
    x = [str(x) for x in [tax_name, taxid, rank, lineage]]
    outFH.write('\t'.join(x) + '\n')


def name2taxid(taxids, ncbi):
    """Converting taxon names to taxids
    """
    new_taxids = []
    for taxid in taxids:
        try:
            new_taxids.append(ncbi.get_name_translator([taxid])[taxid][0])
        except KeyError:
            try:
                new_taxids.append(int(taxid))
            except ValueError:
                msg = 'Error: cannot convert to taxid: {}'
                raise ValueError(msg.format(taxid))

    return new_taxids


def main():
    """Make queries against NCBI Taxa databases
    """
    # Get commandline args
    args = get_args()

    # Instantiate the ete NCBI taxa object
    ncbi = NCBITaxa(dbfile=args.database)
    # dbfile location
    if args.verbose > 1:
        sys.stderr.write('Taxa database is stored at {}\n'.format(ncbi.dbfile))

    # Update the database if required.
    if args.update is True:
        if args.verbose > 1:
            msg = 'Updating the taxonomy database. This may take several minutes...\n'
            sys.stderr.write(msg)
        ncbi.update_taxonomy_database()

    # If names were provided in taxid list, convert to taxids
    args.taxid = args.taxid.replace('"', '').replace("'", '').split(',')
    args.taxid = name2taxid(args.taxid, ncbi)

    # Output
    if args.outfile is None:
        outFH = sys.stdout
    else:
        outFH = open(args.outfile, 'w')
    # header
    if args.taxon_info:
        outFH.write('\t'.join(['name', 'taxid', 'rank', 'lineage']) + '\n')
    elif not args.just_taxids:
        outFH.write('\t'.join(['parent_taxid',
                               'descendent_taxid',
                               'descendent_name']) + '\n')
    # body
    for taxid in args.taxid:
        if args.taxon_info:
            taxon_info(taxid, ncbi, outFH)
        else:
            desc_taxa(taxid, ncbi,  outFH, args.just_taxids)

    outFH.close()


if __name__ == "__main__":
    main()
