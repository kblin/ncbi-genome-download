# NCBI Genome Downloading Scripts

[![Build Status](http://github.drone.secondarymetabolites.org/api/badges/kblin/ncbi-genome-download/status.svg)](http://github.drone.secondarymetabolites.org/kblin/ncbi-genome-download)

Some script to download bacterial and fungal genomes from NCBI after they
restructured their FTP a while ago.

Idea shamelessly stolen from [Mick Watson's Kraken downloader
scripts](http://www.opiniomics.org/building-a-kraken-database-with-new-ftp-structure-and-no-gi-numbers/)
that can also be found in [Mick's GitHub
repo](https://github.com/mw55309/Kraken_db_install_scripts). However, Mick's
scripts are ~~written in Perl~~ specific to actually building a Kraken database
(as advertised).

So this is a set of scripts that focuses on the actual genome downloading.

## Installation

```
pip install ncbi-genome-download
```


Alternatively, clone this repository from GitHub, then run (in a python virtual environment)
```
pip install .
```

## Usage

To download all bacterial RefSeq genomes in GenBank format from NCBI, run the following:

```
ncbi-genome-download bacteria
```

To download all fungal GenBank genomes from NCBI in GenBank format, run:
```
ncbi-genome-download --section genbank fungi
```

To download all viral RefSeq genomes in FASTA format, run:
```
ncbi-genome-download --format fasta viral
```

To download only completed bacterial RefSeq genomes in GenBank format, run:
```
ncbi-genome-download --assembly-level complete bacteria
```

To download bacterial RefSeq genomes of the genus _Streptomyces_, run:
```
ncbi-genome-download --genus Streptomyces bacteria
```
**Note**: This is a simple string match on the organism name provided by NCBI only.


To get an overview of all options, run
```
ncbi-genome-download --help
```

## License
All code is available under the Apache License version 2, see the
[`LICENSE`](LICENSE) file for details.
