#!/usr/bin/env python3
# -*- coding: utf8 -*-
#-------------------------------------------------------------------------------
# created on: 11-14-2018
# filename: shockdetector.py
# author: brendan
# last modified: 12-06-2018 20:57
#-------------------------------------------------------------------------------
"""
Detect the shocking words, and caclulate their scores. To be executable on the
VACC
"""
import tarfile
import numpy as np
import dateutil.relativedelta as rdelta
import datetime as dt
import argparse


def calc_prev_median(date, data, k=1.5):
    """ Calculate the median for a certain date from the data of the previous
    six months of data.
    """
    earliest_date = date - rdelta.relativedelta(months=6)
    # keep only the data in this range
    my_data = []
    for check_date, rank in data:
        if check_date >= earliest_date and check_date <= date:
            my_data.append(rank)
    
    median = np.median(my_data)
    first_quart = np.percentile(my_data, 25)
    third_quart = np.percentile(my_data, 75)
    IQR = third_quart - first_quart

    lower_bound = first_quart - k * IQR
    # make sure the lower bound doesn't go below 1
    lower_bound = lower_bound if lower_bound > 1 else 1
    upper_bound = third_quart + k * IQR

    return (date, median, lower_bound, upper_bound)


def calc_max_shock(rank, l_bound):
    """ Calculate the max shock score given the rank of the word and the lower
    bound on those scores
    """
    rank_arr = np.array(rank)
    lbound_arr = np.array(l_bound)
    z = rank_arr - lbound_arr
    shock_ix = (z < 0).nonzero()[0]
    # if there is no shock return 0
    if shock_ix.size == 0:
        return 0
    # we know that the lines will cross again before the min shock_ix and max
    # shock_ix, so we need to account for that
    # add the index before and after the shock event
    new_ixs = []
    events = []
    event = 0
    for ix in shock_ix:
        # if the previous index is not there start a new event
        if (shock_ix != ix - 1).all():
            new_ixs.append(ix - 1)
            events.append(event)
        new_ixs.append(ix)
        events.append(event)
        if (shock_ix != ix + 1).all():
            new_ixs.append(ix + 1)
            events.append(event)
            event += 1

    # create an empty array to keep track of event sizes, where index is event
    # number and the value is the event size
    event_sizes = np.empty(max(events)+1)
    shock_ix = np.array(new_ixs)
    events = np.array(events)
    # loop through unique events to calculate trapezoidal area
    for event in range(min(events), max(events) + 1):
        # first shrink z to the event
        this_event = (events == event)
        # boil down indices to just event
        event_ix = np.where(this_event, shock_ix, 0)
        # remove zeros, from event index
        event_ix = event_ix[event_ix != 0]
        event_z = z[event_ix]
        
        # find the area of the first and last triangles of the event
        first_intersect = - 1 / (event_z[1] - event_z[0]) * event_z[0]
        last_intersect = - 1 / (event_z[-1] - event_z[-2]) * event_z[-2]
        
        area = 0.5 * (1 - first_intersect) * abs(event_z[1])
        area += 0.5 * last_intersect * abs(event_z[-2])
        
        # find the area of the middle if it exists
        if len(event_ix) > 3:
            middle = event_z[1:-1]
            middle_areas = abs(middle[:-1] + middle[1:]) * 0.5
            area += middle_areas.sum()

        event_sizes[event] = area
    
    return max(event_sizes)


def get_max_shock(word):
    """Run the program with the word and year specified
    """
    print('Gathering Data...')
    full_data = []
    with tarfile.open(TARFILE, mode='r:gz') as f:
        for member in f:
            if member.isfile():
                # parse the date from the file name
                date_str = member.name.split('.')[0][-10:]
                try:
                    date = dt.datetime.strptime(date_str, '%Y-%m-%d')
                except ValueError:
                    continue
                
                if date.year == YEAR or date.year == YEAR - 1:
                    # flag to record if the word was found in the file
                    found = False
                    for line in f.extractfile(member):
                        if word in line.decode():
                            rank = int(line.decode().split()[-1])
                            full_data.append((date, rank))
                            found = True
                            break
                    # if the word isn't found give it the max rank
                    if not found:
                        rank = CUTOFF
                        full_data.append((date, rank))

    full_data = sorted(full_data)
    year_data = [(date, data) for date, data in full_data if date.year == YEAR]
    
    print('Calculating Shock...')
    median_data = []
    for date, _ in year_data:
        median_data.append(calc_prev_median(date, full_data))

    _, _, l_bound, _ = zip(*median_data)
    _, rank = zip(*year_data)

    max_shock = calc_max_shock(rank, l_bound)
    return max_shock


def main():
    """Run the code to calculate the max shock for each word and then save the
    outputs to a new file
    """
    with open('{}/{}.txt'.format(CWD, JOBID), 'w') as sfile:
        for word in WORDS:
            shock_val = get_max_shock(word)
            sfile.write('{},{}\n'.format(word, shock_val))


if __name__ == '__main__':
    """ put the relevant code in the if statement, so I can import
    calc_prev_median without running the full script, and passing in command 
    line arguments
    """
    parser = argparse.ArgumentParser(
        description="Make a word plot with shifting median for a given year")
    parser.add_argument('CWD', help='current working directory')
    parser.add_argument('JOBID', help='job id for the VACC')
    parser.add_argument('words', nargs='?',
                        help='the words to shock detect')
    parser.add_argument('year', nargs='?', default=2018,
                        help='the year of concern for the plot')
    args = parser.parse_args()
    
    # global variables defined
    CWD = args.CWD
    TARFILE = '{}/top_daily_words_uni.tar_.gz'.format(CWD)
    JOBID = args.JOBID
    WORDS = args.words.split(',')
    YEAR = args.year
    # max rank of table
    CUTOFF = 100001

    main()
