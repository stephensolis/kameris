<h1 align="center">
    <br>
    <img src="https://raw.githubusercontent.com/stephensolis/modmap-toolkit/master/logo/logo.png" alt="modmap-toolkit" width="200">
    <br>
    modmap-toolkit
    <br>
</h1>

<h4 align="center">A fast, user-friendly analysis and evaluation pipeline for some DNA sequence classification tasks.</h4>

<p align="center">
    <a href="https://pypi.python.org/pypi/modmap-toolkit">
        <img src="https://badge.fury.io/py/modmap-toolkit.svg" alt="PyPI">
    </a>
    <img src="http://img.shields.io/:license-mit-blue.svg" alt="License">
    &nbsp;
    <a href="https://travis-ci.org/stephensolis/modmap-toolkit">
        <img src="https://travis-ci.org/stephensolis/modmap-toolkit.svg?branch=master" alt="Travis">
    </a>
    <a href="https://ci.appveyor.com/project/stephensolis/modmap-toolkit">
        <img src="https://ci.appveyor.com/api/projects/status/v22hru9wvvdhsv8q?svg=true" alt="Appveyor">
    </a>
    &nbsp;
    <a href="https://www.codacy.com/app/stephensolis/modmap-toolkit">
        <img src="https://api.codacy.com/project/badge/Grade/2286db6fde1d4b729127f820d7896cd0" alt="Codacy">
    </a>
    <a href="https://codebeat.co/projects/github-com-stephensolis-modmap-toolkit-maste">
        <img src="https://codebeat.co/badges/d344663e-21af-402e-a95f-b030b6a6ca2d" alt="Codebeat">
    </a>
    <a href="https://codeclimate.com/github/stephensolis/modmap-toolkit/maintainability">
        <img src="https://api.codeclimate.com/v1/badges/7dcf996e9fcb35d8db7d/maintainability" alt="Codeclimate">
    </a>
</p>

This project uses:

- [stephensolis/modmap-generator-cpp](https://github.com/stephensolis/modmap-generator-cpp) to generate kmer count vectors and distance matrices
- [scikit-learn](http://scikit-learn.org/) for supervised classifiers
- [Wolfram Mathematica](https://www.wolfram.com/mathematica/) and code based on [stephensolis/modmap-generator-mma](https://github.com/stephensolis/modmap-generator-mma) to generate interactive plots
- [NumPy](http://www.numpy.org/) and [SciPy](https://www.scipy.org/) for MultiDimensional Scaling (MDS)

## License ![License](http://img.shields.io/:license-mit-blue.svg)

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
