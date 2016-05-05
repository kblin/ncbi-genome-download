unit:
	py.test -v

coverage:
	py.test --cov=ncbi_genome_download --cov-report term-missing --cov-report html
