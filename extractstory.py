#!/usr/bin/env python3
# -*- coding: utf8 -*-
#-------------------------------------------------------------------------------
# created on: 12-09-2018
# filename: extractstory.py
# author: brendan
# last modified: 12-09-2018 19:28
#-------------------------------------------------------------------------------
"""
Code to extract the story surrounding large shock events
"""
import tarfile
import numpy as np
import datetime as dt
import dateutil.relativedelta as rdelta
import matplotlib.pyplot as plt
import matplotlib.dates as dts
import pickle
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


def calc_max_shock_ix(rank, l_bound):
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
    max_event = 0
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
        
        # keep track of the indexes of the largest event
        if area > max_event:
            max_event = area
            max_ix = event_ix
    
    return max_ix
 

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


def fill_missing_dates(rank_list, shock_dates, cutoff=100001):
    """ Fill missing dates if the list of ranks is missing them, and set them
    as the lowest possible value.
    """
    for key, values in rank_list.items():
        if len(values) < len(shock_dates):
            dates, ranks = zip(*values)
            for date in shock_dates:
                if date not in dates:
                    values.append((date, cutoff))
        values = sorted(values)
        if len(values) > len(shock_dates):
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


def test_rank(rank_list, word, n):
    """ Check each word for similarity to the distribution of the word we
    desire. Return the top n words.
    """
    _, base_check = zip(*sorted(rank_list[word]))
    # just subtract the mean of the dataset, to make the mean 0
    std_base_check = [data - np.mean(base_check) for data in base_check]
    
    words = []
    for key, values in rank_list.items():
        if key == word:
            continue

        _, test_check = zip(*sorted(values))
        # move the data to a mean of 0
        std_test_check = [data - np.mean(test_check) for data in test_check]
        score = brendan_whitney_test(std_base_check, std_test_check)
        
        words.append((score, key))
        
    words = sorted(words)
    return words[:n]


def comparison_date_plot(compare_words, full_word_data, start_date, end_date):
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
                       date >= start_date and date <= end_date]

        date, rank = zip(*this_event)
        ax.plot(date, rank, label=word)
    
    base_event = sorted(full_word_data[WORD])
    this_event = [(date, data) for date, data in base_event if
                   date >= start_date and date <= end_date]

    date, rank = zip(*this_event)
    ax.plot(date, rank, 'k-', label=WORD)
    ax.set_xlabel('Month')
    ax.set_ylabel('Rank')
    ax.invert_yaxis()
    ax.xaxis.set_major_formatter(myFmt)
    ax.legend()
    ax.set_title('Rank plot for {} in {}'.format(WORD, YEAR))
    fig.savefig('plots/{}-{}-shock-event-comparison.jpg'.format(WORD, YEAR))
    plt.close(fig)


def main(CUTOFF=100001):
    """ Run the program with the 3 global varables taken from the arg parsing
    """
    try:
        with open('data/{}-{}-full-data.pkl'.format(WORD, YEAR), 'rb') as f:
            full_data = pickle.load(f, encoding='bytes')
    except:
        full_data = []
        with tarfile.open(TARFILE, mode='r:gz') as f:
            for member in f:
                if member.isfile():
                    # parse the date from the file name
                    date_str = member.name.split('.')[0][-10:]
                    try:
                        date = dt.datetime.strptime(date_str, '%Y-%m-%d')
                    except ValueError:
                        print(member.name.split('.'))
                    if date.year == YEAR or date.year == YEAR - 1:
                        # flag to record if the word was found in the file
                        found = False
                        for line in f.extractfile(member):
                            if WORD in line.decode():
                                rank = int(line.decode().split()[-1])
                                full_data.append((date, rank))
                                found = True
                                break
                        # if the word isn't found give it the max rank
                        if not found:
                            rank = CUTOFF
                            full_data.append((date, rank))

        full_data = sorted(full_data)
        with open('data/{}-{}-full-data.pkl'.format(WORD, YEAR), 'wb') as f:
            pickle.dump(full_data, f)

    median_data = []
    for date, _ in full_data:
        if date.year == YEAR:
            median_data.append(calc_prev_median(date, full_data))

    year_data = [(date, data) for date, data in full_data if date.year == YEAR]

    date, rank = zip(*year_data)
    _, _, u_bound, _ = zip(*median_data)

    shock_ix = calc_max_shock_ix(rank, u_bound)
    
    shock_dates = date[shock_ix[0]:shock_ix[-1]]
    word_dict = get_word_ranks(shock_dates[0], shock_dates[-1])
    word_dict = fill_missing_dates(word_dict, shock_dates)

    _, compare_words = zip(*test_rank(word_dict, WORD, 10))

    comparison_date_plot(compare_words, word_dict, shock_dates[0],
                         shock_dates[-1])


if __name__ == '__main__':
    """ put the relevant code in the if statement, so I can import
    calc_prev_median without running the full script, and passing in command 
    line arguments
    """
    parser = argparse.ArgumentParser(
        description="Make a word plot with shifting median for a given year")
    parser.add_argument('word',
                        help='the words to shock detect')
    parser.add_argument('year', nargs='?', default=2018,
                        help='the year of concern for the plot')
    args = parser.parse_args()
    
    # global variables defined
    TARFILE = 'top_daily_words_uni.tar_.gz'
    WORD = args.word
    YEAR = args.year
    # max rank of table
    CUTOFF = 100001

    main() 
