"""
Perform various queries and tasks with the NCBI taxonomy database,
via the ETE3 toolkit.

Depends on ETE3 (obviously).

TODO:
  - Add some of the tree functionality?
  - Offer more CLI options for arguments to subcommands?
     -> E.g. collapse_subspecies to get_descendent_taxa
  - Alter script to query multiple taxids at once for topology etc?
  - Include some functionality in future for the Phlyo methods in ETE?
  - Consider making update trigger automatically if certain time has elapsed?
    -> Would need to check if that logic already exists in ete.
  - Make lineage also print out with the scientific names
    -> names = ncbi.get_taxid_translator(lineage)... etc
  - Allow users to specify a different directory for the tax_dump
"""

__author__ = "Joe R. J. Healey"
__version__ = "1.0"
__title__ = "gimme_taxa"
__license__ = "Apache2.0"
__author_email__ = "J.R.J.Healey@warwick.ac.uk"


# Check script compatibilities and module requirements

import sys
# Some logic for the future in case removing py2.7 support
#       if sys.version_info[0] is not 3 and sys.version_info[2] is not 6:
#               raise Exception("This script requires python3.6.0+ - Currently running: %s.%s.%s" % (
#                               sys.version_info[0], sys.version_info[1], sys.version_info[2]))

try:
	from ete3 import NCBITaxa
except ImportError:
	print(
"""
The ete3 import failed, the module doesn't appear to be installed
(at least in the PYTHONPATH for this python binary").

Try running:
 $ python -m pip install ete3

or 

 $ conda install -c etetoolkit ete3 ete_toolchain
""")
	sys.exit(1)


def get_args():
	"""Parse command line arguments"""
	import argparse
    
	try:
		parser = argparse.ArgumentParser(description='Perform queries against the NCBI Taxa database. This script is still somewhat experimental.')
		parser.add_argument('-v',
				'--verbose',
				action='count',
				default=0,
				help='Verbose behaviour. Supports 3 levels at present: Off = 0, Info = 1, Verbose = 2. [Def = 0]')
		parser.add_argument('--update',
				action='store_true',
				help='Update the local taxon database before querying. Recommended if not used for a while. [Def = False]')
		parser.add_argument('-t',
				'--taxid',
				action='store',
				type=int,
				help='The numerical TaxID to query. (e.g. 561)')
		parser.add_argument('-n',
				'--name',
				action='store',
				help='Provide a scientific name instead of a TaxID, if you\'re too lazy to find it out! (e.g. Escherichia).') 
		parser.add_argument('-o',
				'--outfile',
				action='store',
				help='Output file to store the descendent TaxIDs for the query.')
		if len(sys.argv) == 1:
			parser.print_help(sys.stderr)
			sys.exit(1)
	except:
		print("An exception occurred with argument parsing. Check your provided options.")
		sys.exit(1)

	return parser.parse_args()


def pretty(d, indent=0):
	"""A prettier way to print nested dicts"""
	for key, value in d.items():
		print('  ' * indent + str(key))
		if isinstance(value, dict):
			pretty(value, indent+1)
		else:
			print('  ' * (indent+1) + str(value))


def main():
	"""Make queries against NCBI Taxa databases"""
	# Get commandline args		
	args = get_args()
	
	# Instantiate the ete NCBI taxa object
	ncbi = NCBITaxa()

	if args.verbose > 1:
		print("Taxa database is stored under ~/.etetoolkit/taxa.sqlite")

	# Update the database if required.
	if args.update is True:
		if args.verbose > 1:
			print("Updating the taxonomy database. This may take several minutes...")
		ncbi.update_taxonomy_database()

	# If a name was provided instead of a TaxID, convert and store it.
	if args.name:
		args.taxid = ncbi.get_name_translator([args.name])[args.name][0]
	
	if args.verbose > 0:
		tax_dict = {}
		# If a name was provided, simply add it to dict
		if args.name:
			tax_dict['Name'] = args.name
		# If not, do the opposite conversion to the above and store that
		else:
                	tax_dict['Name'] = ncbi.get_taxid_translator([args.taxid])[args.taxid]
                # Continue to populate the taxa dict with other information
		tax_dict['TaxID'] = args.taxid
		tax_dict['Rank'] = ncbi.get_rank([args.taxid])
		tax_dict['Lineage'] = ncbi.get_taxid_translator(ncbi.get_lineage(args.taxid))


		print("Information about your selected taxa:")
		pretty(tax_dict)
	
	# Main feature of the script is to get all taxa within a given group.	
	descendent_taxa = ncbi.get_descendant_taxa(args.taxid)
	descendent_taxa_names = ncbi.translate_to_names(descendent_taxa)
	print("Descendent taxa for TaxID: %s" % (args.taxid))

	# Under python3, zip = izip. In python2, this list could be very large, and memory intensive
	# Suggest the script is run with python3
	if args.verbose > 0:
		for dtn, dt in zip(descendent_taxa_names, descendent_taxa):
			print("%s\t%s" % (dtn, dt))
	
	if args.outfile:
		with open(args.outfile, 'w') as ofh:
			for id in descendent_taxa:
				ofh.write(str(id) + '\n')


if __name__ == "__main__":
	main()
