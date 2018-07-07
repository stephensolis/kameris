<h1 align="center">
    <br>
    <img src="https://raw.githubusercontent.com/stephensolis/kameris/master/logo/logo.png" alt="kameris" width="200">
    <br>
    Kameris
    <br>
</h1>

<h4 align="center">A fast, user-friendly analysis and evaluation pipeline for some DNA sequence classification tasks.</h4>

<p align="center">
    <a href="https://pypi.python.org/pypi/kameris">
        <img src="https://badge.fury.io/py/kameris.svg" alt="PyPI">
    </a>
    <img src="https://img.shields.io/pypi/l/kameris.svg" alt="License">
    &nbsp;
    <a href="https://travis-ci.org/stephensolis/kameris">
        <img src="https://travis-ci.org/stephensolis/kameris.svg?branch=master" alt="Travis">
    </a>
    <a href="https://ci.appveyor.com/project/stephensolis/kameris">
        <img src="https://ci.appveyor.com/api/projects/status/7tc4kkrig5xyn4pu?svg=true" alt="Appveyor">
    </a>
    <br>
    <a href="https://www.codacy.com/app/stephensolis/kameris">
        <img src="https://api.codacy.com/project/badge/Grade/2286db6fde1d4b729127f820d7896cd0" alt="Codacy">
    </a>
    <a href="https://codebeat.co/projects/github-com-stephensolis-kameris-master">
        <img src="https://codebeat.co/badges/5826ce1f-ba26-4cd4-a641-d33845023d79" alt="Codebeat">
    </a>
    <a href="https://codeclimate.com/github/stephensolis/kameris/maintainability">
        <img src="https://api.codeclimate.com/v1/badges/0ea51d670aba5f65c707/maintainability" alt="Codeclimate">
    </a>
</p>

## Installing

There are three ways to install this software. Choose whichever one is best for your needs:

**1. If you already have Python 2.7 or 3.4+ installed (recommended):**

Run `pip install kameris`.

**2. If you do not have Python installed or are unable to install software:**

[Click here](https://github.com/stephensolis/kameris/releases/latest) and download the version corresponding to your operating system.
If you use Linux or macOS, you may need to run `chmod +x "path to downloaded program"`.

**3. If you are a developer or want to build your own version of Kameris:**

Clone this repository then run `make install`.

## Citing

If you use this software in your research, please cite:

An open-source k-mer based machine learning tool for fast and accurate subtyping of HIV-1 genomes <br>
Stephen Solis-Reyes, Mariano Avino, Art Poon, Lila Kari <br>
https://www.biorxiv.org/content/early/2018/07/05/362780

## Quick demo

This software is able to train sequence classification models and use them to make predictions.

Before following these instructions, make sure you've installed the software.
If you followed option **1** above and the command `kameris` doesn't work for you, try using `python -m kameris` instead.
If you followed option **2** above and downloaded an executable, replace `kameris` in the instructions below with the name of the executable you downloaded.

### Classifying sequences with an existing model

First, let's classify some HIV-1 sequences.

1. Start by downloading this zip file containing HIV-1 genomes, and extract it to a folder: https://raw.githubusercontent.com/stephensolis/kameris/master/demo/hiv1-genomes.zip.
2. Run `kameris classify hiv1-mlp "path to extracted files"`

This will output the top subtype match for each sequence and write all results to a new file `results.json`.

The `hiv1-mlp` model is able to give class probabilities and a ranked list of predictions, but some models are only able to report the top match. For example, try `kameris classify hiv1-linearsvm "path to extracted files"`

To see other available models, go to https://github.com/stephensolis/kameris-experiments/tree/master/models.

### Training a new model

Now, let's train our own HIV-1 sequence classification models.

1. Create an empty folder and open a terminal in the folder.
2. Create folders `data` and `output`.
3. Run `kameris run-job https://raw.githubusercontent.com/stephensolis/kameris/master/demo/hiv1-lanl.yml https://raw.githubusercontent.com/stephensolis/kameris/master/demo/settings.yml`

Depending on your computer's performance and internet speed, it may take 5-10 minutes to run.
This will automatically download the required datasets and train a simpler version of the [hiv1/lanl-whole experiment from kameris-experiments](https://github.com/stephensolis/kameris-experiments).
This was the exact job used to train the models from the previous section, and these are the same models used in the paper ["An open-source k-mer based machine learning tool for fast and accurate subtyping of HIV-1 genomes"](https://www.biorxiv.org/content/early/2018/07/05/362780).

Now, open `output/hiv1-lanl-whole`. You will notice folders were created for each value of `k`. Within each folder are several files:
- `fasta` contains the FASTA files extracted from the downloaded dataset used for model training and evaluation.
- `metadata.json` contains metadata on the FASTA files used to determine the class for each sequence.
- `cgrs.mm-repr` contains feature vectors for each sequence. See the mentioned paper for more technical details.
- `classification-kmers.json` contains evaluation results after using cross-validation on the dataset. See the mentioned paper for more technical details.
- The `.mm-model` files contain trained models which may be passed to `kameris classify` in order to classify new sequences. **Note** that models trained using Python 2 will not run under Python 3 and vice-versa.
- `log.txt` is a log file containing all the output printed during job execution.
- `rerun-experiment.yml` is a file which may be passed to `kameris run-job` in order to re-run the job and obtain exactly the files found in this directory.

Kameris also includes functionality to summarize results in easy-to-read tables. Try it by running `kameris summarize output/hiv1-lanl-whole`.

You can change the settings used to train the model: first download the files [hiv1-lanl.yml](https://raw.githubusercontent.com/stephensolis/kameris/master/demo/hiv1-lanl.yml) and [settings.yml](https://raw.githubusercontent.com/stephensolis/kameris/master/demo/settings.yml).
Training settings are found in `hiv1-lanl.yml` -- try changing the value of `k` or uncommenting different classifier types.
File storage and logging settings are found in `settings.yml`.
After making changes, run `kameris run-job hiv1-lanl.yml settings.yml` to train your model.

[//]: # (## Documentation)

## Dependencies

This project uses:

- [stephensolis/kameris-backend](https://github.com/stephensolis/kameris-backend) to generate k-mer count vectors and distance matrices
- [scikit-learn](http://scikit-learn.org/) for supervised classifiers
- [Wolfram Mathematica](https://www.wolfram.com/mathematica/) and code based on [stephensolis/modmap-generator](https://github.com/stephensolis/modmap-generator) to generate interactive plots
- [NumPy](https://www.numpy.org/) and [SciPy](https://www.scipy.org/) for MultiDimensional Scaling (MDS)

## License ![License](https://img.shields.io/pypi/l/kameris.svg)

    The MIT License (MIT)

    Copyright (c) 2017 Stephen

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
