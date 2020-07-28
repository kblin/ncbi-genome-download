# NCBI基因组下载脚本

> Translate by [jamesyang](https://github.com/jamesyangget), the translation may not be timely. If you can't find it in the Chinese version, you can refer to the original document.
> 
> 由[jamesyang](https://github.com/jamesyangget)翻译，翻译可能不及时，如果在中文文档里找不到需要的东西，你可以参考原文档。

从NCBI下载重组FTP后的细菌和真菌基因组的一些脚本

从 [Mick Watson的Kraken下载程序脚本](http://www.opiniomics.org/building-a-kraken-database-with-new-ftp-structure-and-no-gi-numbers/) 中获得的想法，这些[脚本](http://www.opiniomics.org/building-a-kraken-database-with-new-ftp-structure-and-no-gi-numbers/)也可以在Mick的[GitHub](https://github.com/mw55309/Kraken_db_install_scripts)仓库中找到。然而，Mick是~~用Perl语言编写的~~ 专门用于实际构建 Kraken 数据库（如广告所示）。

因此，这是一组侧重于实际基因组下载的脚本。

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

或者，`ncbi-genome-download`也被打包在`conda`。请参阅 Anaconda/miniconda 网站以安装发行版（强烈推荐）[https://conda.io/miniconda.html](https://conda.io/miniconda.html) 安装后可以执行以下操作：

``` bash 
conda install -c bioconda ncbi-genome-download
```

`ncbi-genome-download`仅在Python团队仍活跃支持下的Python版本上开发和测试。目前，这些代表版本有3.5，3.6，3.7和3.8。具体来说，没有尝试在3.5之前的Python版本下进行测试。

如果您的系统停留在旧版本的 Python 上，请考虑使用 [Homebrew](http://brew.sh/) 等工具获取更新版本。

`ncbi-genome-download`0.2.12是支持Python2的最后一个版本。

## 使用

要从NCBI RefSeq下载GenBank格式的所有的细菌基因组，请运行以下命令：

``` bash 
ncbi-genome-download bacteria
```

也可以下载多个组：

``` bash 
ncbi-genome-download bacteria,viral
```

**注意**：查看所有可用组，请参阅 `ncbi-genome-download --help`，或只是使用`all`来检查所有组。命名更具体的组将减少下载大小和查找要下载的序列所需的时间。

如果您的连接速度相当快，您可能需要尝试并行运行多个下载：

``` bash 
ncbi-genome-download bacteria --parallel 4
```

要从NCBI GenBank下载GenBank格式的所有的真菌基因组，请运行：

``` bash 
ncbi-genome-download --section genbank fungi
```

要从RefSeq下载所有FASTA格式的病毒基因组，请运行：

``` bash 
ncbi-genome-download --formats fasta viral
```

可以通过提供格式列表或仅下载所有格式来下载多种格式：

``` bash 
ncbi-genome-download --formats fasta,assembly-report viral
ncbi-genome-download --formats all viral
```

仅从RefSeq下载GenBank格式的细菌全基因组，请运行：

``` bash 
ncbi-genome-download --assembly-levels complete bacteria
```

通过提供列表，可以一次下载多个程序集级别：

``` bash 
ncbi-genome-download --assembly-levels complete,chromosome bacteria
```

仅从RefSeq下载GenBank格式的细菌参考基因组，请运行：

``` bash 
ncbi-genome-download --refseq-categories reference bacteria
```

要从RefSeq下载*Streptomyces*（链霉菌）属的细菌基因组，请运行：

``` bash 
ncbi-genome-download --genera Streptomyces bacteria
```

**注意**：这是仅由NCBI提供的有机体名称上的简单字符串匹配。

您也可以用一点小技巧来下载特定物种的基因组

``` bash 
ncbi-genome-download --genera "Streptomyces coelicolor" bacteria
```

**注意**：引号很重要。同样，这是NCBI提供的有机体名称上的简单字符串匹配。

也可以有多个属：

``` bash 
ncbi-genome-download --genera "Streptomyces coelicolor,Escherichia coli" bacteria
```

您还可以将属名放入一个文件中，每行一个有机体，例如：

``` text 
Streptomyces
Amycolatopsis
```

然后，将该文件的路径（例如`my_genera.txt`）传递给 `--genera` 选项，如下所示：

``` bash 
ncbi-genome-download --genera my_genera.txt bacteria
```

**注意**：上述命令将从RefSeq下载所有*Streptomyces*（链球菌）和*Amycolatopsis*（拟无枝菌酸菌）的基因组。

您可以使用`--fuzzy-genus`选项模糊匹配字符串。如果您需要匹配NCBI生物体名称中间的值，这很方便，如下所示：

``` bash 
ncbi-genome-download --genera coelicolor --fuzzy-genus bacteria
```

**注意**：上述命令将从 RefSeq 下载所有含有“coelicolor”的细菌基因组。

要基于NCBI物种分类ID从RefSeq下载细菌基因组，请运行：

``` bash 
ncbi-genome-download --species-taxids 562 bacteria
```

**注意**：上述命令将下载属于*Escherichia coli*（大肠杆菌）的所有RefSeq基因组。

要基于NCBI分类标识ID从RefSeq下载特定细菌基因组，请运行：

``` bash 
ncbi-genome-download --taxids 511145 bacteria
```

**注意**：上述命令将从 RefSeq 下载属于*Escherichia coli str. K-12 substr. MG1655*的基因组 。

也可以下载多种分类ID或通过在逗号分隔列表中提供数字来下载多种分类ID物种：

``` bash 
ncbi-genome-download --taxids 9606,9685 --assembly-levels chromosome vertebrate_mammalian
```

**注意**：上述命令将下载猫和人类的参考基因组。

此外，您可以将多个物种分类ID或物种分类ID放入一个文件中，每行一个，并将该文件名分别传递给`--species-taxids`或`--taxids`参数。

假设您有一个`my_taxids.txt`文件包含以下内容：

``` text
9606
9685
```

你可以下载猫和人的参考基因组，如下所示：

``` bash 
ncbi-genome-download --taxids my_taxids.txt --assembly-levels chromosome vertebrate_mammalian
```

也可以创建可读的目录结构，并行镜像 NCBI 使用的布局：

``` bash 
ncbi-genome-download --human-readable bacteria
```

这将使用链接指向NCBI目录结构中的相应文件，因此可以节省文件空间。请注意，链接不支持某些Windows文件系统和旧版Windows。

也可以使用该`--human-readable`选项重新运行先前的下载。在这种情况下，`ncbi-genome-download`不会下载任何新的基因组文件，只需创建可读的目录结构。请注意，如果在NCBI端更改了任何文件，将触发文件下载。

根据您的筛选器，有个`--dry-run`选项可显示下载哪些加入：

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

此脚本允许您找出要传递给 `ngd` 的 物种分类ID，并将编写一个简单的每行一项文件以传递给它。它使用 `ete3` 工具包，因此，如果尚未满足，请参阅其站点来安装依赖项。

您可以使用特定的 物种分类ID 或科学名称查询数据库。脚本的主要功能是返回指定父 taxa 的所有子 taxa。该脚本具有用于在输出中写入的信息的各种选项。

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
