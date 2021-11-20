from ncbi_genome_download import jobs


def test_job_eq():
    args = ['foo', 'bar', 'baz', 'blub']
    job_a = jobs.DownloadJob(*args)
    job_b = jobs.DownloadJob(*args)
    job_c = jobs.DownloadJob('this', 'one', 'is', 'different')

    assert job_a == job_b
    assert job_a != job_c
    assert job_b != args
