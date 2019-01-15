#!/usr/bin/env python3
# -*- coding: utf8 -*-
#-------------------------------------------------------------------------------
# created on: 11-12-2018
# filename: makewordplot.py
# author: brendan
# last modified: 12-11-2018 21:26
#-------------------------------------------------------------------------------
"""
Parse the rank file to make a plot of the rank of a particular word
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


def main(WORD, LOG, YEAR, CUTOFF=100001):
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


    fig, ax = plt.subplots()
    loc = dts.MonthLocator()
    myFmt = dts.DateFormatter('%m')
    
    median_plot = []
    for date, _ in full_data:
        if date.year == YEAR:
            median_plot.append(calc_prev_median(date, full_data))

    # make the plots only for 2018
    plot_data = full_data
    plot_data = [(date, rank) for date, rank in full_data if date.year == YEAR]
    
    rdate, rank = zip(*plot_data)

    mdate, median, upper_bound, lower_bound = zip(*median_plot)

    # calculate the standard deviation, to note points that rise much higher
    # the typical values of the plot
    filename = 'plots/{}-{}-baseline-comparison'.format(WORD, YEAR)
    ylabel = 'Rank'

    if LOG:
        rank = np.log10(rank)
        median = np.log10(median)
        upper_bound = np.log10(upper_bound)
        lower_bound = np.log10(lower_bound)
        ylabel = 'Log Rank'
        filename = '{}-LOG'.format(filename)

    ax.plot(rdate, rank, 'k-')
    ax.plot(mdate, median, 'r--')
    ax.fill_between(mdate, upper_bound, lower_bound, color='r', alpha=0.3,
                    linewidth=0)
    # ax[1].axhspan(first_quart - k * IQR, third_quart + k * IQR, color='r',
                  # alpha=0.25, lw=0)
    ax.set_xlabel('Month')
    ax.set_ylabel(ylabel)
    ax.invert_yaxis()
    ax.xaxis.set_major_formatter(myFmt)
    ax.set_title('Rank plot for {} in {}'.format(WORD, YEAR))
    fig.savefig('{}.jpg'.format(filename))
    plt.close(fig)

if __name__ == '__main__':
    """ put the relevant code in the if statement, so I can import
    calc_prev_median without running the full script, and passing in command 
    line arguments
    """
    parser = argparse.ArgumentParser(
        description="Make a word plot with shifting median for a given year")
    parser.add_argument('word',
                        help='the word for plotting')
    parser.add_argument('log', nargs='?', default=False,
                        help='boolean flag to produce a log plot')
    parser.add_argument('year', nargs='?', default=2018,
                        help='the year of concern for the plot')
    args = parser.parse_args()

    home_directory = 'top_daily_words_uni'
    TARFILE = '{}.tar_.gz'.format(home_directory)
    WORD = args.word
    print(WORD)
    LOG = bool(args.log)
    print(LOG)
    YEAR = args.year
    print(YEAR)
    # the number to multiply the IQR by to indicate extreme values vs. outliers

    main(WORD, LOG, YEAR)

