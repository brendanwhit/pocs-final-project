#!/usr/bin/env python3
# -*- coding: utf8 -*-
#-------------------------------------------------------------------------------
# created on: 11-14-2018
# filename: explorefiles.py
# author: brendan
# last modified: 11-14-2018 16:35
#-------------------------------------------------------------------------------
"""
Use this to quickly explore some files for use.
First use is to explore the contents of the two non date files
"""
import tarfile
import datetime as dt
home_directory = 'top_daily_words_uni'
filename = '{}.tar_.gz'.format(home_directory)

with tarfile.open(filename, mode='r:gz') as f:
    for member in f:
        if member.isfile():
            # parse the date from the file name
            date_str = member.name.split('.')[0][-10:]
            try:
                date = dt.datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                # see what the two non date files are
                myf = f.extractfile(member)
                print(member.name)
                for line in myf:
                    print(line)
                    break

