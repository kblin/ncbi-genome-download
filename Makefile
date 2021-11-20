unit:
	py.test -v

coverage:
	py.test --cov=ncbi_genome_download --cov-report term-missing --cov-report html

lint:
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 . --count --exit-zero --max-complexity=20 --statistics
