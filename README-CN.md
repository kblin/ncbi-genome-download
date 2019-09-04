# NCBI基因组下载脚本

> Translate by [jamesyang](https://github.com/jamesyangget), the translation may not be timely. If you can't find it in the Chinese version, you can refer to the original document.
> 由[jamesyang](https://github.com/jamesyangget)翻译，翻译可能不及时，如果在中文文档里找不到需要的东西，你可以参考原文档。

一些脚本在他们刚刚重组他们的FTP后从NCBI下载细菌和真菌基因组。

从[Mick Watson的Kraken下载程序脚本](http://www.opiniomics.org/building-a-kraken-database-with-new-ftp-structure-and-no-gi-numbers/) 中获得的想法，这些[脚本](http://www.opiniomics.org/building-a-kraken-database-with-new-ftp-structure-and-no-gi-numbers/)也可以在Mick的[GitHub](https://github.com/mw55309/Kraken_db_install_scripts)仓库中找到。然鹅，Mick是~~用Perl语言编写的~~ 特定用于实际构建 Kraken 数据库（如宣传的那样）。

所以这是一组专注于实际基因组下载的脚本。

## 安装

``` bash 
pip install ncbi-genome-download
```

或者，从GitHub克隆此存储库，然后运行（在python虚拟环境中）

``` bash 
pip install .
```

如果在旧版本的Python上失败，请先尝试更新您的`pip`工具：

``` bash 
pip install --upgrade pip
```

然后重新运行`ncbi-genome-download`安装。

或者，用`conda`安装`ncbi-genome-download`。请参阅 Anaconda/miniconda 网站以安装发行版（强烈推荐）[https://conda.io/miniconda.html](https://conda.io/miniconda.html) 安装后可以执行以下操作：

``` bash 
conda install -c bioconda ncbi-genome-download
```

`ncbi-genome-download`仅在Python团队仍活跃支持下的Python版本上开发和测试。目前，这些代表版本有2.7，3.4，3.5和3.6。具体来说，没有尝试在2.7或3.4之前的Python版本下进行测试。

如果您的系统停留在旧版本的Python上，请考虑使用[Homebrew](http://brew.sh/)或[Linuxbrew](http://linuxbrew.sh/)等工具来获取更新版本。

## 用法

要从NCBI下载GenBank格式的所有RefSeq服务器里细菌的基因组，请运行以下命令：

``` bash 
ncbi-genome-download bacteria
```

下载多个组也是可能的：

``` bash 
ncbi-genome-download bacteria,viral
```

如果您的连接速度相当快，您可能希望尝试并行运行多个下载：

``` bash 
ncbi-genome-download bacteria --parallel 4
```

要从NCBI下载GenBank格式的所有GenBank服务器里真菌的基因组，请运行：

``` bash 
ncbi-genome-download --section genbank fungi
```

要下载FASTA格式的所有病毒的基因组，请运行：

``` bash 
ncbi-genome-download --format fasta viral
```

可以通过提供格式列表来下载多种格式，或者只是下载所有格式：

``` bash 
ncbi-genome-download --format fasta,assembly-report viral
ncbi-genome-download --format all viral
```

要从RefSeq服务器里以GenBank格式仅下载完整的细菌基因组，请运行：

``` bash 
ncbi-genome-download --assembly-level complete bacteria
```

通过提供列表，可以一次下载多个装配级别：

``` bash 
ncbi-genome-download --assembly-level complete,chromosome bacteria
```

要从RefSeq服务器里以GenBank格式仅下载细菌参考基因组，请运行：

``` bash 
ncbi-genome-download --refseq-category reference bacteria
```

要从RefSeq服务器里下载*Streptomyces*属的细菌基因组，请运行：

``` bash 
ncbi-genome-download --genus Streptomyces bacteria
```

**注意**：这是仅由NCBI提供的有机体名称上的简单字符串匹配。

您也可以使用它来轻松下载某些物种的基因组：

``` bash 
ncbi-genome-download --genus "Streptomyces coelicolor" bacteria
```

**注意**：引号很重要。同样，这是NCBI提供的有机体名称上的简单字符串匹配。

多个属也是可能的：

``` bash 
ncbi-genome-download --genus "Streptomyces coelicolor,Escherichia coli" bacteria
```

您还可以将属名放入文件`my_genera.txt`中，每行一个生物体，例如：

``` text 
Streptomyces
Amycolatopsis
```

然后，通过`--genus`选项将该`my_genera.txt`文件路径传递，如下所示：

``` bash 
ncbi-genome-download --genus my_genera.txt bacteria
```

**注意**：上述命令将从RefSeq下载所有*Streptomyces*和*Amycolatopsis*的基因组。

您可以使用该`--fuzzy-genus`选项使字符串匹配模糊。如果您需要匹配NCBI生物体名称中间的值，这可能很方便，如下所示：

``` bash 
ncbi-genome-download --genus coelicolor --fuzzy-genus bacteria
```

**注意**：上述命令将从RefSeq任何地方下载其生物体名称中含有“coelicolor”的所有细菌基因组。

要根据NCBI物种分类标识ID下载RefSeq里细菌的基因组，请运行：

``` bash 
ncbi-genome-download --species-taxid 562 bacteria
```

**注意**：上述命令将下载属于*coelicolor*的RefSeq里所有基因组。

要根据NCBI分类标识ID下载RefSeq里特定细菌基因组，请运行：

``` bash 
ncbi-genome-download --taxid 511145 bacteria
```

**注意**：上述命令将下载属于*Escherichia coli*的RefSeq里的基因组*。**K-12 substr。**MG1655*。

也可以通过以逗号分隔的列表提供数字来下载多种物种出租车或出租车：

``` bash 
ncbi-genome-download --taxid 9606,9685 --assembly-level chromosome vertebrate_mammalian
```

**注意**：上面的命令将下载猫和人的参考基因组。

此外，您可以将多个物种taxid放入一个文件中，每行一个并将该文件名分别传递给`--species-taxid`或`--taxid`参数。

假设您有一个`my_taxids.txt`文件包含以下内容：

``` text
9606
9685
```

你可以下载猫和人的参考基因组，如下所示：

``` bash 
ncbi-genome-download --taxid my_taxids.txt --assembly-level chromosome vertebrate_mammalian
```

也可以创建可读的目录结构，并行镜像 NCBI 使用的布局：

``` bash 
ncbi-genome-download --human-readable bacteria
```

这将使用链接指向NCBI目录结构中的相应文件，因此可以节省文件空间。请注意，某些Windows文件系统和旧版Windows不支持链接。

也可以使用该`--human-readable`选项重新运行先前的下载。在这种情况下，`ncbi-genome-download`不会下载任何新的基因组文件，只需创建可读的目录结构。请注意，如果在NCBI端更改了任何文件，将触发文件下载。

根据您的筛选器，有个`--dry-run`选项可显示加入下载哪些：

``` bash 
ncbi-genome-download --dry-run bacteria
```

如果要筛选程序集摘要文件的“与类型材料的关系”列，可以使用该`--type-material`选项。可能的值是“any”，“all”，“type”，“reference”，“synonym”，“proxytype”和/或“neotype”。“any”将包括与定义的类型材料值无关的装配体，“all”将仅下载具有定义值的装配体。可以给出多个值，用逗号分隔：

``` bash 
ncbi-genome-download --type-material type,reference
```

默认情况下，ncbi-genome-download缓存相应分类组的程序集摘要文件一天。您可以用`--no-cache --help`选项跳过使用缓存文件。如果要删除任何缓存文件，输出也会显示缓存目录。

要获得所有选项的概述，请运行

``` bash 
ncbi-genome-download --help
```

### 作为一种方法

您也可以将其用作方法调用。传递上述被转述的关键字参数（`_`而不是`-`）或用`--help`：

``` python 
import ncbi_genome_download as ngd
ngd.download()
```

**注意**：要指定分类组，如*bacteria*，请使用`group`关键字。

### 贡献的脚本： `gimme_taxa.py`

此脚本可让您找出要传递给哪些TaxID ，并将编写一个简单的“每行一项”文件来传递给它。它使用`ngd ete3`工具包，因此，如果它尚未满足，请参阅其站点来安装依赖项。

您可以使用特定的TaxID或科学名称查询数据库。该脚本的主要功能是返回指定父 taxa 的所有子 taxa。脚本具有各种选项，用于在输出中写入哪些信息。

基本调用可能如下所示：

``` bash 
# Fetch all descendent taxa for Escherichia (taxid 561):
python gimme_taxa.py -o ~/mytaxafile.txt 561

# Alternatively, just provide the taxon name
python gimme_taxa.py -o all_descendent_taxids.txt Escherichia

# You can provide multiple taxids and/or names
python gimme_taxa.py -o all_descendent_taxids.txt 561,Methanobrevibacter
```

首次使用时，默认情况下将在主目录中创建一个小的sqlite数据库（使用`--database`标志更改位置）。您可以使用该`--update`标志更新此数据库。请注意，如果数据库不在您的主目录中，则必须使用该`--database`数据库进行指定，否则将在主目录中创建新数据库。

要查看所有帮助：

``` bash 
python gimme_taxa.py
python gimme_taxa.py -h
python gimme_taxa.py --help
```

## 许可证

所有代码在Apache许可证版本2下都可用，有关详细信息，请参阅该 [`LICENSE`](https://github.com/kblin/ncbi-genome-download/blob/master/LICENSE)文件。
