#!/usr/bin/env python3
# -*- coding: utf8 -*-
#-------------------------------------------------------------------------------
# created on: 12-06-2018
# filename: generate_word_list.py
# author: brendan
# last modified: 12-10-2018 15:24
#-------------------------------------------------------------------------------
"""
Generate a list of all the words in the tarfile for 2018
"""
import tarfile
import datetime as dt
import csv

YEAR = 2018
THRESHOLD = 365
TARFILE = 'top_daily_words_uni.tar_.gz'

word2count2018 = {}
word2count2017 = {}

with tarfile.open(TARFILE, mode='r:gz') as f:
    for member in f:
        if member.isfile():
            # parse the date from the file name
            date_str = member.name.split('.')[0][-10:]
            try:
                date = dt.datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                print(member.name.split('.'))
            if date.year == YEAR:
                print('{}...'.format(date))
                # keep track of words already seen
                seen2018 = set()
                for line in f.extractfile(member):
                    info = line.decode().split()
                    # only add a word to word set if it doesn't already exist
                    # in the set
                    # skip the header row
                    if info[1] in seen2018 or info[1] == 'Counts':
                        continue
                    try:
                        word2count2018[info[1]] += 1
                    except KeyError:
                        word2count2018[info[1]] = 1
                    seen2018.add(info[1])
            elif date.year == YEAR-1:
                print('{}...'.format(date))
                # keep track of words already seen
                seen2017 = set()
                for line in f.extractfile(member):
                    info = line.decode().split()
                    # only add a word to word set if it doesn't already exist
                    # in the set
                    # skip the header row
                    if info[1] in seen2017 or info[1] == 'Counts':
                        continue
                    try:
                        word2count2017[info[1]] += 1
                    except KeyError:
                        word2count2017[info[1]] = 1
                    seen2017.add(info[1])                

sort2018 = sorted(word2count2018.items(), key=lambda x: x[1], reverse=True)
sort2017 = sorted(word2count2017.items(), key=lambda x: x[1], reverse=True) 

print(sort2018[:100])
print(sort2017[:100])

# only 304 days in 2018 for the data
words2018 = set([word for word, count in sort2018 if count >= 304])
# 2017 only has 364 days
words2017 = set([word for word, count in sort2017 if count >= 364])

my_words = words2018.intersection(words2017)
print(my_words)
print(len(my_words))

row2words = {}
counter=0
for word in my_words:
    if counter > 999:
        counter = 0
    try:
        row2words[counter].append(word)
    except KeyError:
        row2words[counter] = [word]
    counter += 1

print(len(row2words.keys()))
with open('popular_words.txt', 'w') as wfile:
    mywriter = csv.writer(wfile, delimiter=' ')
    mywriter.writerows(row2words.values())
        

