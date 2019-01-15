#!/usr/bin/env python3
# -*- coding: utf8 -*-
#-------------------------------------------------------------------------------
# created on: 11-28-2018
# filename: findshock.py
# author: brendan
# last modified: 12-09-2018 19:26
#-------------------------------------------------------------------------------
"""
Code to detect schock value from the data taken to make word plots
"""
import tarfile
import numpy as np
import datetime as dt
import dateutil.relativedelta as rdelta
import matplotlib.pyplot as plt
import matplotlib.dates as dts
import pickle
from makewordplot import calc_prev_median
from scipy.stats import ks_2samp

WORD = 'cave'
YEAR = 2018
k = 1.5
test = 'bw'

TARFILE = 'top_daily_words_uni.tar_.gz'


def daterange(start_date, end_date):
    """ Make a date range iterator
    """
    for n in range(int((end_date - start_date).days)+1):
         yield start_date + dt.timedelta(n)


def main_date_plot(full_date, start_date, end_date):
    """ Make a date plot based on the data fed in the range of the start_date
    and end_date
    """
    fig, ax = plt.subplots()
    loc = dts.MonthLocator()
    if end_date - start_date < dt.timedelta(days=90):
        myFmt = dts.DateFormatter('%m-%d')
    else:
        myFmt = dts.DateFormatter('%m')
    
    # check if full data is a list of lists
    this_event = [(date, data) for date, data in full_data if
                      date >= prev_date and date <= final_date]

    date, rank = zip(*this_event)

    ax.plot(date, rank, 'k-')

    ax.set_xlabel('Month')
    ax.set_ylabel('Rank')
    ax.invert_yaxis()
    ax.xaxis.set_major_formatter(myFmt)
    ax.set_title('Rank plot for {} in {}'.format(WORD, YEAR))
    fig.savefig('plots/{}-{}-shock-event.jpg'.format(WORD, YEAR))
    plt.close(fig)


def comparison_date_plot(compare_words, full_word_data, start_date, end_date,
                        test):
    """Plot the comparison words with a legend for readability
    """
    fig, ax = plt.subplots()
    loc = dts.MonthLocator()
    if end_date - start_date < dt.timedelta(days=90):
        myFmt = dts.DateFormatter('%m-%d')
    else:
        myFmt = dts.DateFormatter('%m')
    
    for word in compare_words:
        event_list = sorted(full_word_data[word])
        this_event = [(date, data) for date, data in event_list if
                       date >= prev_date and date <= final_date]

        date, rank = zip(*this_event)
        ax.plot(date, rank, label=word)
    
    base_event = sorted(full_word_data[WORD])
    this_event = [(date, data) for date, data in base_event if
                   date >= prev_date and date <= final_date]

    date, rank = zip(*this_event)
    ax.plot(date, rank, 'k-', label=WORD)
    ax.set_xlabel('Month')
    ax.set_ylabel('Rank')
    ax.invert_yaxis()
    ax.xaxis.set_major_formatter(myFmt)
    ax.legend()
    ax.set_title('Rank plot for {} in {}'.format(WORD, YEAR))
    fig.savefig('plots/{}-{}-shock-event-comparison-{}.jpg'.format(WORD, YEAR,
                                                                  test))
    plt.close(fig)


def get_word_ranks(start_date, end_date):
    """ Get a dictionary of the word to word ranks for the date range
    specified. This will be used to determine which words are most similar to
    the word that has shock value
    """
    word_dict = {}

    with tarfile.open(TARFILE, mode='r:gz') as f:
            for member in f:
                if member.isfile():
                    # parse the date from the file name
                    date_str = member.name.split('.')[0][-10:]
                    try:
                        date = dt.datetime.strptime(date_str, '%Y-%m-%d')
                    except ValueError:
                        print(member.name.split('.'))
                    if date >= start_date and date <= end_date:
                        print('{} ...'.format(date))
                        # flag to record if the word was found in the file
                        for i, line in enumerate(f.extractfile(member)):
                            info = line.decode().split()
                            try:
                                word_dict[info[1]].append((date,
                                                           int(info[-1])))
                            except KeyError:
                                try:
                                    word_dict[info[1]] = [(date,
                                                           int(info[-1]))]
                                except ValueError:
                                    continue

    return word_dict


def remove_duplicates(rank_list):
    """ Remove values from duplicate days, using the smaller rank value from
    duplicates
    """
    dates_seen = []
    ranks_seen = []
    for date, rank in rank_list:
        if date in dates_seen:
            ix = dates_seen.index(date)
            if rank < ranks_seen[ix]:
                ranks_seen[ix] = rank
        else:
            dates_seen.append(date)
            ranks_seen.append(rank)
    return list(zip(dates_seen, ranks_seen))


def fill_missing_dates(rank_list, start_date, end_date, cutoff=100001):
    """ Fill missing dates if the list of ranks is missing them, and set them
    as the lowest possible value.
    """
    for key, values in rank_list.items():
        if len(values) < (end_date - start_date).days + 1:
            dates, ranks = zip(*values)
            for date in daterange(start_date, end_date):
                if date not in dates:
                    values.append((date, cutoff))
        values = sorted(values)
        if len(values) > (end_date - start_date).days + 1:
            values = remove_duplicates(values)
        
        rank_list[key] = values
    return rank_list


def brendan_whitney_test(dist1, dist2, cumulative=True):
    """ My own test to determine the words that are most similar
    """
    if len(dist1) != len(dist2):
        raise ValueError('Distributions do not have the same length')
    
    if cumulative:
        cum_dist = 0
        for i in range(len(dist1)):
            cum_dist += (dist1[i] - dist2[i]) ** 2

        return cum_dist
    
    max_dist = 0
    for i in range(len(dist1)):
        dist = (dist1[i] - dist2[i]) ** 2
        if dist > max_dist:
            max_dist = dist
        # exponentially decay the weights of the distance between points
        # cum_dist += np.exp(-i) * (dist1[i] - dist2[i]) ** 2
    
    return max_dist


def test_rank(rank_list, word, n, test='bw'):
    """ Check each word for similarity to the distribution of the word we
    desire. Return the top n words.
    """
    tests = ['bw', 'ks']
    if test not in test:
        raise ValueError('Invalid test used. Need to choose either {} or {}\
                         tests.'.format(*tests))

    _, base_check = zip(*sorted(rank_list[word]))
    # just subtract the mean of the dataset, to make the mean 0
    std_base_check = [data - np.mean(base_check) for data in base_check]
    
    print(std_base_check)

    words = []
    for key, values in rank_list.items():
        if key == word:
            continue

        _, test_check = zip(*sorted(values))
        # move the data to a mean of 0
        std_test_check = [data - np.mean(test_check) for data in test_check]
        if test == 'bw':
            score = brendan_whitney_test(std_base_check, std_test_check)
        else:
            score, _ = ks_2samp(std_base_check, std_test_check)
        
        words.append((score, key))
        
    words = sorted(words)
    print(words[:n])
    return words[:n]


with open('data/{}-{}-full-data.pkl'.format(WORD, YEAR), 'rb') as f:
    full_data = pickle.load(f, encoding='bytes')

median_data = []
for date, _ in full_data:
    if date.year == YEAR:
        median_data.append(calc_prev_median(date, full_data))

year_data = [(date, data) for date, data in full_data if date.year == YEAR]

date, rank = zip(*year_data)
_, _, u_bound, _ = zip(*median_data)

rank_arr = np.array(rank)
ubound_arr = np.array(u_bound)
x = np.arange(len(rank_arr))
z = rank_arr - ubound_arr
shock_ix = (z < 0).nonzero()[0]
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

print(event_sizes)
print(max(event_sizes))

print(shock_ix)
print(events)
shock_check = list(zip(date, rank, u_bound))
shock_dates = [(date, u_bound - rank) for date, rank, u_bound in shock_check 
               if rank < u_bound]

shock_events = []
day = dt.timedelta(days=1)
past_date = 0
for date, shock_value in shock_dates:
    if past_date:
        if date - past_date == day:
            past_shock += shock_value
            length += 1
        else:
            # only care about events longer than 1 day
            if length > 1:
                shock_events.append((past_date, past_shock, length))
            length = 1
            past_shock = shock_value
        past_date = date
    else:
        past_date = date
        past_shock = shock_value
        length = 1

shock_events.append((past_date, past_shock, length))

"""
i = 0
for end_date, shock_score, event_length in shock_events:
    i += 1
    start_date = end_date - dt.timedelta(days=event_length-1)
    print(start_date, end_date)
    prev_date = start_date - dt.timedelta(days=1)
    final_date = end_date + dt.timedelta(days=10)

    main_date_plot(year_data, prev_date, final_date)

    word_dict = get_word_ranks(prev_date, final_date)
    complete_dict = fill_missing_dates(word_dict, prev_date, final_date)
    
    scores, words = zip(*test_rank(complete_dict, WORD, 10, test))
    
    comparison_date_plot(words, complete_dict, prev_date, final_date, test)
"""
