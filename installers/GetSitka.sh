#!/bin/sh
##
## script to install Sitka on Linux or MacOS
## using a Miniforge environment and installing
## all required packages with conda or pip

prefix=$HOME/sitka_spruce
sitkurl='sitka_spruce'

uname=`uname`
condaurl="https://github.com/conda-forge/miniforge/releases/latest/download"

condafile="Miniforge3-$uname-$(uname -m).sh"

logfile=GetSitka.log

## set list of conda packages to install from conda-forge
cforge_pkgs="python==3.13.10 numpy=>2.3.0 scipy=>1.15 matplotlib=>3.10 h5py=>3.13 wxpython=>4.2.4"
unset CONDA_EXE CONDA_PYTHON_EXE CONDA_PREFIX PROJ_LIB

## get command line options
for opt ; do
  option=''
  case "$opt" in
    -*=*)
        optarg=`echo "$opt" | sed 's/[-_a-zA-Z0-9]*=//'`
        option=`echo "$opt" | sed 's/=.*//' | sed 's/-*//'`
        ;;
    *)
        option=`echo "$opt" | sed 's/^-*//'`
        optarg=
        ;;
  esac
  case "$option" in
    prefix)        prefix=$optarg ;;
    -h | h | -help | --help | help) cat<<EOF
Usage: GetSitka.sh [options]
Options:
  --prefix=PREFIX             base directory for installation [$prefix]
EOF
    exit 0
    ;;

   *)
       echo " unknown option "  $opt
       exit 1
       ;;
  esac
done

## test for prefix already existing
if [ -d $prefix ] ; then
   echo "##Error: $prefix exists."
   exit 0
fi


echo "##############  " | tee $logfile
echo "##  This script will install Sitka-Spruce for $uname to $prefix" | tee -a $logfile
echo "##  " | tee -a $logfile
echo "##  The following packages will be taken from conda-forge:" | tee -a $logfile
echo "##        $cforge_pkgs " | tee -a $logfile
echo "##  " | tee -a $logfile
echo "##  See GetSitka.log for complete log and error messages" | tee -a $logfile
echo "##############  " | tee -a $logfile


## download miniconda installer if needed
if [ ! -f $condafile ] ; then
    echo "## Downloading Miniconda installer for $uname" | tee -a $logfile
    echo "#>  /usr/bin/curl -L $condaurl/miniconda/$condafile -O " | tee -a $logfile
    /usr/bin/curl -L $condaurl/$condafile -O | tee -a $logfile
fi

# install and update miniconda
echo "##  Installing Miniconda for $uname to $prefix" | tee -a $logfile
echo "#>  sh ./$condafile -b -p $prefix " | tee -a $logfile
sh ./$condafile -b -p $prefix | tee -a $logfile

export PATH=$prefix/bin:$PATH

echo "##  Installing packages from conda-forge"  | tee -a $logfile
echo "#> $prefix/bin/conda install -yc conda-forge $cforge_pkgs " | tee -a $logfile
$prefix/bin/conda install -y -c conda-forge $cforge_pkgs
$prefix/bin/conda list

echo "##Installing sitka-spruce as 'pip install \"$sitkaurl\"'"  | tee -a $logfile
echo "#> $prefix/bin/pip install \"$sitkaurl\""| tee -a $logfile
$prefix/bin/pip install "$sitkaurl" | tee -a $logfile

## create desktop shortcuts
echo "## Creating desktop shortcuts"
$prefix/bin/sitka -m

## create desktop shortcuts
echo "## Set up initial conda environment for your shell"
$prefix/bin/conda init

echo "##############  " | tee -a $logfile
echo "##  Sitka Installation to $prefix done." | tee -a $logfile
echo "##  "| tee -a $logfile
echo "##  To use from a terminal, check you $SHELL start up scripts.  You may want to add:"  | tee -a $logfile
echo "        export PATH=$prefix/bin:\$PATH"  | tee -a $logfile
echo "##  "| tee -a $logfile
echo "##  See GeSitka.log for complete log and error messages" | tee -a $logfile
echo "##############  " | tee -a $logfile
