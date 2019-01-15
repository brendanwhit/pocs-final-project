#!/usr/bin/env python3
# -*- coding: utf8 -*-
#-------------------------------------------------------------------------------
# created on: 12-09-2018
# filename: rankshock.py
# author: brendan
# last modified: 12-11-2018 13:04
#-------------------------------------------------------------------------------
"""
Rank the shock value of certain words on Twitter
"""
def sort_scores(wordlist):
    return sorted(wordlist, key=lambda x: x[1], reverse=True)


missing_words = []
user_names = []
hash_tags = []
words = []
with open('popular-scores.txt', 'r') as myfile:
    for line in myfile:
        word, score = line.strip().split(',')
        if score == 'nan':
            missing_words.append(word)
        elif '@' in word:
            user_names.append((word, float(score)))
        elif '#' in word:
            hash_tags.append((word, float(score)))
        else:
            words.append((word, float(score)))

print(missing_words)
print(sort_scores(user_names)[:10])
print(sort_scores(hash_tags)[:10])
print(sort_scores(words)[:10])
