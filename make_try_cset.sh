#!/bin/sh -x
g++ try_cset.cpp -o try_cset -lz $(correction config --cflags --ldflags --rpath)
