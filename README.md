# BobGen
Python script to convert `.csv` files from [EpicsConversion](https://github.com/BGomulka/EpicsConversion) to Phoebus XML `.bob` files

## Usage Guide

By default, `BobGen.py` works wthin your current working directory. If run without arguments, it will automatically process the first `.csv` file found in that directory.

To test the script with extra details, run it in test mode. This will only process files that begin with the word "test":
```bash
python3 BobGen.py -t -v
```
For a quick reference guide, run:
```bash
python3 BobGen.py -h
