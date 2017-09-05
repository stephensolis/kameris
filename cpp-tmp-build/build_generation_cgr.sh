#!/bin/sh

icpc generation_cgr.cpp -Icpp -lpthread -lboost_filesystem  -lboost_system -O3 -no-prec-div -fp-model fast=2 -xHost -o generation_cgr
