"""Test the argument parsing."""
from ncbi_genome_download.core import argument_parser


def test_formats():
    """Test the -F/--formats option works as expected."""
    args = ['-F', 'genbank', 'bacteria']
    parser = argument_parser()
    ns = parser.parse_args(args=args)
    assert ns.file_formats == 'genbank'

    args = ['--formats', 'fasta', 'bacteria']
    parser = argument_parser()
    ns = parser.parse_args(args=args)
    assert ns.file_formats == 'fasta'

    args = ['--formats', 'genbank,fasta', 'bacteria']
    parser = argument_parser()
    ns = parser.parse_args(args=args)
    assert ns.file_formats == 'genbank,fasta'


def test_assembly_levels():
    """Test the -l/--assembly-levels option works as expected."""
    args = ['-l', 'complete', 'bacteria']
    parser = argument_parser()
    ns = parser.parse_args(args=args)
    assert ns.assembly_levels == 'complete'

    args = ['--assembly-levels', 'chromosome', 'bacteria']
    parser = argument_parser()
    ns = parser.parse_args(args=args)
    assert ns.assembly_levels == 'chromosome'

    args = ['--assembly-levels', 'complete,chromosome', 'bacteria']
    parser = argument_parser()
    ns = parser.parse_args(args=args)
    assert ns.assembly_levels == 'complete,chromosome'


def test_assembly_accessions():
    """Test the -A/--assembly-accessions option works as ecpected."""
    args = ['-A', 'GCF_000203835.1', 'bacteria']
    parser = argument_parser()
    ns = parser.parse_args(args=args)
    assert ns.assembly_accessions == 'GCF_000203835.1'

    args = ['--assembly-accessions', 'GCF_000203835.1,GCF_000444875.1', 'bacteria']
    parser = argument_parser()
    ns = parser.parse_args(args=args)
    assert ns.assembly_accessions == 'GCF_000203835.1,GCF_000444875.1'

    args = ['--assembly-accessions', 'some/path/here.txt', 'bacteria']
    parser = argument_parser()
    ns = parser.parse_args(args=args)
    assert ns.assembly_accessions == 'some/path/here.txt'


def test_relation_to_type_materials():
    """Test the -M/--type-materials option works as expected."""
    # Empty args should default to 'all'
    args = ['bacteria']
    parser = argument_parser()
    ns = parser.parse_args(args)
    assert ns.type_materials == 'any'

    args = ['-M', 'type', 'bacteria']
    parser = argument_parser()
    ns = parser.parse_args(args)
    assert ns.type_materials == 'type'

    args = ['-M', 'type,synonym', 'fungi']
    parser = argument_parser()
    ns = parser.parse_args(args)
    assert ns.type_materials == 'type,synonym'

    args = ['--type-materials', 'reference', 'fungi']
    parser = argument_parser()
    ns = parser.parse_args(args)
    assert ns.type_materials == 'reference'

    args = ['-M', 'all', 'fungi']
    parser = argument_parser()
    ns = parser.parse_args(args)
    assert ns.type_materials == 'all'
