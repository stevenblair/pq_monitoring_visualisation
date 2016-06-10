#
# Author: Steven Blair, steven.m.blair@strath.ac.uk
#

import calendar
import datetime
import tables
import ujson
import numpy as np
import shelve

import pandas as pd
from collections import OrderedDict
import time

from twisted.web import server, resource
from twisted.internet import reactor
from twisted.web.static import File


class NamedTimer():
    def __init__(self):
        self.enabled = False

        if self.enabled:
            self.things = [('start', time.clock())]

    def add(self, name):
        if self.enabled:
            self.things.append((name, time.clock()))

    def stop(self):
        if self.enabled:
            total = sum([self.things[i][1] - self.things[i - 1][1] for i, x in enumerate(self.things) if i > 0])
            for i, x in enumerate(self.things):
                if i > 0:
                    diff_time = self.things[i][1] - self.things[i - 1][1]
                    print x[0].ljust(32), '{:.3f} s,'.format(diff_time), '{:.1f}%'.format(100.0 * diff_time / total)
            print ''

def get_abbreviated_name(full_name):
    return full_name.replace(' ', '').replace('(', '').replace(')', '').replace('.', '')

def precalculate_heat_map_data():
    all_columns = []
    for node in monitor_tables:
        table = node._f_get_child('readout')
        all_columns = [c._v_pathname for c in table.description._f_walk(type="Col")]
        break

    for node in monitor_tables:
        timer = NamedTimer()
        table = node._f_get_child('readout')
        name = get_abbreviated_name(node._v_title)
        print name

        for column in all_columns[3:]:
            values = [[row['date'], row[column]] for row in table]
            timer.add('heatmap, query')

            values_dict = {}
            for v in values:
                # get mean value for each 1-hour slot
                day = datetime.datetime.utcfromtimestamp(v[0]).replace(minute=0, second=0)
                if day in values_dict:
                    values_dict[day] = (values_dict[day][0] + v[1], values_dict[day][1] + 1)
                else:
                    values_dict[day] = (v[1], 1)
            timer.add('heatmap, loop through values')

            # arrange values into list format
            values_out = []
            for key in values_dict.keys():
                values_out.append([calendar.timegm(key.timetuple()) * 1000, key.hour, values_dict[key][0] / values_dict[key][1]])

            heatmap_precalculated_data[(name, column)] = ujson.dumps(values_out)
            timer.add('heatmap, values_out')
        timer.stop()

def precalculate_daily_resampling():
    all_columns = []
    for node in monitor_tables:
        table = node._f_get_child('readout')
        all_columns = [c._v_pathname for c in table.description._f_walk(type="Col")]
        break

    for node in monitor_tables:
        timer = NamedTimer()
        table = node._f_get_child('readout')
        name = get_abbreviated_name(node._v_title)

        values = [[row[c] for c in all_columns] for row in table]
        timer.add(name + ' query table')
        # print 'length of query results:', len(values)
        
        if len(values) > 0:
            df = pd.DataFrame(values, columns=all_columns)
            timer.add(name + ' create DataFrame')

            df['date'] = pd.to_datetime(df['date'], unit='s')
            timer.add(name + ' convert timestamp to datetime')

            df.set_index('date', inplace=True)
            timer.add(name + ' set_index of DataFrame')

            df2 = df.resample('24H', how=get_resampling_type_dict(all_columns[3:]))
            timer.add(name + ' resampling DataFrame')

            df2.reset_index(inplace=True)
            timer.add(name + ' reset index')

            daily_resampled_data[name] = df2
            timer.add(name + ' store DataFrame')

        timer.stop()


def get_resampling_freq(days_delta):
    resampling_freq = '24H'
    if days_delta <= 2:
        resampling_freq = '5Min'
    elif days_delta < 5:
        resampling_freq = '10Min'
    elif days_delta < 10:
        resampling_freq = '30Min'
    elif days_delta < 20:
        resampling_freq = '1H'
    elif days_delta < 50:
        resampling_freq = '2H'
    elif days_delta < 75:
        resampling_freq = '4H'
    elif days_delta < 100:
        resampling_freq = '6H'
    elif days_delta < 160:
        resampling_freq = '8H'
    elif days_delta < 300:
        resampling_freq = '12H'
    return resampling_freq

def get_resampling_type_dict(columns):
    ret = OrderedDict()
    for col in columns:
        if 'Max' in col:
            ret[col] = 'max'
        elif 'Min' in col:
            ret[col] = 'min'
        else:
            ret[col] = 'mean'
    return ret

def get_monitor(monitor_name):
    for node in monitor_tables:
        name = get_abbreviated_name(node._v_title)
        if name == monitor_name:
            return node._f_get_child('readout')
    return None

def get_monitor_from_tables(monitor_name, tables):
    for node in tables:
        name = get_abbreviated_name(node._v_title)
        if name == monitor_name:
            return node._f_get_child('readout')
    return None

def get_monitor_harmonics(monitor_name, harmonics_phase):
    if harmonics_phase in harmonics_tables:
        harmonics_table_root = harmonics_tables[harmonics_phase]

        for node in harmonics_table_root:
            name = get_abbreviated_name(node._v_title)
            if name == monitor_name:
                return node._f_get_child('readout')
    return None

def get_data(monitor_name, from_dt, to_dt, columns):
    timer = NamedTimer()
    # rather than blindly cutting samples using the 'step' option, fetch all data then re-sample to reduce data size
    NUMBER_OF_VALUES = 576  # 2 days

    table = get_monitor(monitor_name)

    # check for pre-resampled data
    if (calendar.timegm(from_dt.timetuple()) <= table._v_parent._v_attrs.earliest_date and calendar.timegm(to_dt.timetuple()) >= table._v_parent._v_attrs.latest_date):
        # using all pre-resampled data
        if monitor_name in daily_resampled_data:
            df = daily_resampled_data[monitor_name][columns]
            out = df.to_json(orient="values", date_format='epoch', date_unit='ms')
            # print 'using pre-resampled, number of samples:', len(df)
            return out
    elif get_resampling_freq((to_dt - from_dt).days) == '24H':
        # using a subset of pre-resampled data
        if monitor_name in daily_resampled_data:
            df = daily_resampled_data[monitor_name][columns]
            df2 = df[(df.date >= np.datetime64(from_dt)) & (df.date <= np.datetime64(to_dt))]
            out = df2.to_json(orient="values", date_format='epoch', date_unit='ms')
            # print 'using pre-resampled subset, number of samples:', len(df2)
            return out
    
    # cannot use precalculated values; query data and resample if needed
    values = [[row[c] for c in columns] for row in table.where('(date >= ' + str(calendar.timegm(from_dt.timetuple())) + ') & (date <= ' + str(calendar.timegm(to_dt.timetuple())) + ')')]
    timer.add('query rows')

    # return values, resampling if needed
    if len(values) <= NUMBER_OF_VALUES:
        # convert to JavaScript convention of datetime
        for v in values:
            v[0] = v[0] * 1000
        # print 'not resampling, number of samples:', len(values)

        timer.add('conversion to millisecond')
        timer.stop()
        return ujson.dumps(values)
    else:
        # input_dict = {t: x for t, x in zip(input_t, input_signal)}
        # df = pd.DataFrame(input_signal, index=input_t, columns=['Current_RMS_10_Cycle_Avg_A'])
        days_delta = (to_dt - from_dt).days#len(values) / (24.0 * 12.0)#
        resampling_freq = get_resampling_freq(days_delta)
        resampling_type = get_resampling_type_dict(columns[1:])

        if resampling_freq == '24H' and monitor_name in daily_resampled_data:
            # if 24H sampling required, use precalculated values
            df = daily_resampled_data[monitor_name][columns]
            df2 = df[(df.date >= np.datetime64(from_dt)) & (df.date <= np.datetime64(to_dt))]
            out = df2.to_json(orient="values", date_format='epoch', date_unit='ms')
            # print 'using pre-resampled subset, number of samples:', len(df2)
            return out
        else:
            df = pd.DataFrame(values, columns=columns)
            timer.add('create DataFrame')
            df['date'] = pd.to_datetime(df['date'], unit='s')
            timer.add('convert timestamp to datetime')
            df.set_index('date', inplace=True)
            timer.add('set_index of DataFrame')

            df2 = df.resample(resampling_freq, how=resampling_type)
            timer.add('resampling')
            # df2.fillna(0, inplace=True)

            df2.reset_index(inplace=True)
            out = df2.to_json(orient="values", date_format='epoch', date_unit='ms')
            timer.add('to JSON')
            timer.stop()

            # print 'resampling, number of samples:', len(df2), 'days_delta:', int(days_delta), 'resampling_freq', resampling_freq, "raw values", len(values)
            return out

def get_data_heat_map(monitor_name, columns):
    column = columns[1]

    if PRECALCULATE_HEATMAP_DATA and (monitor_name, column) in heatmap_precalculated_data:
        return heatmap_precalculated_data[(monitor_name, column)]
    else:
        timer = NamedTimer()

        table = get_monitor(monitor_name)
        values = [[row['date'], row[column]] for row in table]
        timer.add('heatmap, query')

        values_dict = {}
        for v in values:
            # get mean value for each 1-hour slot
            day = datetime.datetime.utcfromtimestamp(v[0]).replace(minute=0, second=0)
            if day in values_dict:
                values_dict[day] = (values_dict[day][0] + v[1], values_dict[day][1] + 1)
            else:
                values_dict[day] = (v[1], 1)
        timer.add('heatmap, loop through values')

        # arrange values into list format
        values_out = []
        for key in values_dict.keys():
            values_out.append([calendar.timegm(key.timetuple()) * 1000, key.hour, values_dict[key][0] / values_dict[key][1]])

        timer.add('heatmap, values_out')
        timer.stop()
        return ujson.dumps(values_out)


# def check_angle_range(value_rad, nominal):
#     # potential issues with data:
#         # initial samples are unreliable - captured during installation process
#         # any voltage or current sensor not connected
#         # voltage sequence wrong
#         # voltage phase A inconsistent with system phase A
#         # current sequence wrong (e.g., Ib and Ic swapped)
#         # current sequence correct, but inconsistent with voltage sequence (Ic, Ia, Ib instead of Ia, Ib, Ic)
#         # any current polarity wrong

#     value_deg = np.rad2deg(value_rad)
#     threshold = 45.0

#     if nominal == 0.0:
#         # phase A - may wrap around zero
#         if ((360.0 - threshold) <= value_deg <= 360) or (0.0 <= value_deg <= threshold):
#             return 1.0
#     elif nominal == 240:
#         # phase B
#         if ((240.0 - threshold) <= value_deg <= (240 + threshold)):
#             return 1.0
#     elif nominal == 120:
#         # phase C
#         if ((120.0 - threshold) <= value_deg <= (120 + threshold)):
#             return 1.0

#     return -1.0

# def is_pos_seq(values_rad):
#     values_deg = np.rad2deg(values_rad)
#     threshold = 45.0
#     ret = [False, False, False]
    
#     # phase A - may wrap around zero
#     if ((360.0 - threshold) <= values_deg[0] <= 360) or (0.0 <= values_deg[0] <= threshold):
#         ret[0] = True

#     # phase B
#     if ((240.0 - threshold) <= values_deg[1] <= (240 + threshold)):
#         ret[1] = True

#     # phase C
#     if ((120.0 - threshold) <= values_deg[2] <= (120 + threshold)):
#         ret[2] = True

#     if all(ret):
#         return True

#     return False


# def phasor_between(phasor, a, b):
#     print '  phasor:', phasor, 'a:', a, 'b:', b
#     from_a = 180 - abs(abs(phasor - a) - 180);
#     from_b = 180 - abs(abs(phasor - b) - 180);
#     print '    ', from_a, from_b

def phasor_diff(phasor, target):
    return 180 - abs(abs(phasor - target) - 180);

def find_phase_A_index_and_offset(phasors):
    results = []
    for p in phasors:
        results.append(phasor_diff(p, 0.0))
    for p in phasors:
        results.append(phasor_diff(p, 180.0))

    return results.index(min(results)), min(results)

def identify_phase(phasor):
    if phasor > 330.0 or phasor <= 30.0:
        return 'Ia'
    if phasor > 210.0 and phasor <= 270.0:
        return 'Ib'
    if phasor > 90.0 and phasor <= 150.0:
        return 'Ic'
    if phasor > 150.0 and phasor <= 210.0:
        return '-Ia'
    if phasor > 30.0 and phasor <= 90.0:
        return '-Ib'
    if phasor > 270.0 and phasor <= 330.0:
        return '-Ic'

def is_phase_A(phasor):
    if phasor > 330.0 or phasor <= 30.0:
        return True
    return False

def is_phase_B(phasor):
    if phasor > 210.0 and phasor <= 270.0:
        return True
    return False

def is_phase_C(phasor):
    if phasor > 90.0 and phasor <= 150.0:
        return True
    return False

def add_angle(a, b):
    total = a + b
    if (total >= 360.0):
        total = total - 360.0
    return total

def add_angle_rad(a, b):
    total = a + b
    if (total >= 2 * np.pi):
        total = total - (2 * np.pi)
    return total

def neg_seq_mag(a, b, c):
    b_ang_new = add_angle(b[1], 240.0)
    c_ang_new = add_angle(c[1], 120.0)

    re = a[0] * np.cos(a[1] * np.pi / 180.0) + b[0] * np.cos(b_ang_new * np.pi / 180.0) + c[0] * np.cos(c_ang_new * np.pi / 180.0)
    im = a[0] * np.sin(a[1] * np.pi / 180.0) + b[0] * np.sin(b_ang_new * np.pi / 180.0) + c[0] * np.sin(c_ang_new * np.pi / 180.0)

    return np.sqrt(re*re + im*im)

def pos_seq_mag(a, b, c):
    b_ang_new = add_angle(b[1], 120.0)
    c_ang_new = add_angle(c[1], 240.0)

    re = a[0] * np.cos(a[1] * np.pi / 180.0) + b[0] * np.cos(b_ang_new * np.pi / 180.0) + c[0] * np.cos(c_ang_new * np.pi / 180.0)
    im = a[0] * np.sin(a[1] * np.pi / 180.0) + b[0] * np.sin(b_ang_new * np.pi / 180.0) + c[0] * np.sin(c_ang_new * np.pi / 180.0)

    return np.sqrt(re*re + im*im)

def any_negative_phase(a, b, c):
    # a[1] between 90 and 270
    if a[1] >= 90.0 and a[1] < 270.0:
        return True

    # b[1] between 315 and 135 (wrapped around zero)
    if b[1] >= 330.0 or b[1] < 150.0:
        return True

    # c[1] between 45 and 225
    if c[1] >= 210.0 or c[1] < 30.0:
        return True

    return False

def correct_waveform_phasors(monitor_name):
    harmonics_phases = ['Ia', 'Ib', 'Ic']

    for h in harmonics_phases:
        table = get_monitor_harmonics(monitor_name, h)
        print table.nrows
    # nrows = get_monitor_harmonics(monitor_name, 'Ia').nrows
    # print nrows

    longest_table = max([get_monitor_harmonics(monitor_name, h).nrows for h in harmonics_phases])

    if longest_table > 0:
        earliest_date = min([get_monitor_harmonics(monitor_name, h)._v_parent._v_attrs.earliest_date for h in harmonics_phases])
        latest_date = max([get_monitor_harmonics(monitor_name, h)._v_parent._v_attrs.latest_date for h in harmonics_phases])
        # print longest_table, earliest_date, latest_date

        # return

        # check each 15 min interval
        for date in range(earliest_date, latest_date + 900, 900):
            phasors = []


            for h in harmonics_phases:
                table = get_monitor_harmonics(monitor_name, h)

                p = [(row['H1_mag'], row['H1_ang'] * 180.0 / (np.pi)) for row in table.where('date == ' + str(date))]
                
                if len(p) == 1:
                    phasors.append(p[0])

            # check data exists and in valid magnitude range
            if len(phasors) == 3 and all(m >= 50.0 for m in [phasors[0][0], phasors[1][0], phasors[2][0]]):
                # print 'pos seq mag:', pos_seq_mag(phasors[0], phasors[1], phasors[2])
                # print 'neg seq mag:', neg_seq_mag(phasors[0], phasors[1], phasors[2])

                # only take action if current negative sequence is greater than 50% (relative to rated current)
                # (this will cater for wrong sequence and current polarity errors, regardless of power factor)
                if (neg_seq_mag(phasors[0], phasors[1], phasors[2]) / 5.0) > 50.0 or any_negative_phase(phasors[0], phasors[1], phasors[2]):
                    # print phasors
                    phase_A, offset = find_phase_A_index_and_offset([phasors[0][1], phasors[1][1], phasors[2][1]])
                    # print phase_A, offset
                    # print add_angle(phasors[0][1], offset), add_angle(phasors[1][1], offset), add_angle(phasors[2][1], offset)

                    # first find the phase closest to 0deg (or 180deg) and normalise all phasor angles
                    # print phasor_diff(phasors[0][1], 0.0), phasor_diff(phasors[1][1], 0.0), phasor_diff(phasors[2][1], 0.0)
                    # print phasor_diff(phasors[0][1], 180.0), phasor_diff(phasors[1][1], 180.0), phasor_diff(phasors[2][1], 180.0)
                    first_col = identify_phase(add_angle(phasors[0][1], offset))
                    second_col = identify_phase(add_angle(phasors[1][1], offset))
                    third_col = identify_phase(add_angle(phasors[2][1], offset))
                    col_changes = [first_col, second_col, third_col]

                    if first_col == 'Ia' and second_col == 'Ib' and third_col == 'Ic':
                        # print 'correct sequence and polarity'
                        pass
                    else:
                        # print 'incorrect sequence and/or polarity'
                        indices = {}
                        original_rows = {}
                        updated_rows = {}
                        for h in harmonics_phases:
                            table = get_monitor_harmonics(monitor_name, h)
                            indices[h] = table.get_where_list('date == ' + str(date))
                            original_rows[h] = table[indices[h]]
                            # original_rows[h] = table.where('date == ' + str(date))
                            # print 'len(original_rows[h]):', len(original_rows[h])
                            # print original_rows[h]
                            # print all_cols

                        # update magnitudes and/or sequence
                        for ch, original_phase in zip(col_changes, harmonics_phases):
                            updated_rows[ch.replace('-', '')] = original_rows[original_phase]
                            if '-' in ch:
                                for j, r in enumerate(updated_rows[ch.replace('-', '')]):
                                    updated_rows[ch.replace('-', '')][j][6] = add_angle_rad(updated_rows[ch.replace('-', '')][j][6], np.pi)

                                # TODO need to rotate every harmonic, or just fundamental?

                                # print 'updated to:', updated_rows[ch.replace('-', '')][0][6]
                                # print updated_rows[ch.replace('-', '')][0]
                                # for col in updated_rows[ch.replace('-', '')]:
                                #     updated_rows[ch.replace('-', '')][6] = add_angle_rad(updated_rows[ch.replace('-', '')][6], np.pi)
                                #     # print col
                                #     if 'H1_ang' in col:
                                #         print 'updating:', col, updated_rows[ch.replace('-', '')][col]
                                #         updated_rows[ch.replace('-', '')][col] = add_angle_rad(updated_rows[ch.replace('-', '')][col], np.pi)
                                #     # if 'H1_mag' in col:
                                #     #     updated_rows[original_phase][col] = updated_rows[original_phase][col] * -1.0
                                # # updated_rows[ch.replace('-', '')] = [original_rows[original_phase] * -1.0 if 'H1_mag' in col for col in original_rows[original_phase]]


                        for h in harmonics_phases:
                            table = get_monitor_harmonics(monitor_name, h)
                            # table.modify_rows(start=start, stop=stop, rows=updated_rows[h])
                            if h not in indices:
                                print 'h not in indices'
                            if h not in updated_rows:
                                print 'h not in updated_rows', col_changes

                            if h in indices and h in updated_rows:
                                table[indices[h]] = updated_rows[h]
            else:
                # print 'invalid date', len(phasors), phasors
                pass


def get_data_waveform(monitor_name, harmonics_type, from_dt):
    if INDIVIDUAL_HARMONICS:
        timer = NamedTimer()

        harmonics_phases = ['Va', 'Vb', 'Vc']
        if harmonics_type == 'current':
            harmonics_phases = ['Ia', 'Ib', 'Ic']

        waveforms = [[], [], []]
        DC = []
        mags = []
        angs = []

        for h in harmonics_phases:
            table = get_monitor_harmonics(monitor_name, h)
            all_columns = [c._v_pathname for c in table.description._f_walk(type="Col")]

            mag = [[row[c] for c in all_columns if 'mag' in c and 'inter' not in c] for row in table.where('date == ' + str(calendar.timegm(from_dt.timetuple())))]
            ang = [[row[c] for c in all_columns if 'ang' in c] for row in table.where('date == ' + str(calendar.timegm(from_dt.timetuple())))]
            
            if len(mag) > 0:
                DC.append(mag[0][0])
                mags.append(mag[0][1:])
                angs.append(ang[0][1:])

            timer.add('waveforms, query ' + h)

        if len(mags) > 0:
            phase_polarity = [1.0, 1.0, 1.0]

            waveform_duration = 0.04    # seconds
            F_nom = 50.0                # Hz
            steps = 400
            timestep = waveform_duration / steps

            t_values = np.linspace(0.0, waveform_duration, steps, endpoint=False)
            harmonics_numbers = np.array(range(1, 64))
            f_values = 2 * np.pi * 50.0 * harmonics_numbers

            for i in range(0, steps):
                t = i * timestep
                # loop through phase numbers, and generate waveform time series
                for n in [0, 1, 2]:
                    v = phase_polarity[n] * (DC[n] + np.sum(np.array(mags[n]) * np.sin(t * f_values + np.array(angs[n]))))
                    waveforms[n].append(v)

            # if harmonics_type == 'voltage' and change_seq:
            #     waveforms[1], waveforms[2] = waveforms[2], waveforms[1]

            # # for manually testing output waveforms
            # for v in waveforms:
            #     print v

        timer.add('waveforms, waveforms')
        timer.stop()
        return ujson.dumps(waveforms)


def get_data_harmonics(monitor_name, harmonics_type, from_dt, show_fundamental=True, to_pu=False, interharmonics=False):
    if INDIVIDUAL_HARMONICS:
        timer = NamedTimer()

        harmonics_phases = ['Va', 'Vb', 'Vc']
        if harmonics_type == 'current':
            harmonics_phases = ['Ia', 'Ib', 'Ic']

        mags = []

        for h in harmonics_phases:
            table = get_monitor_harmonics(monitor_name, h)
            all_columns = [c._v_pathname for c in table.description._f_walk(type="Col")]

            if interharmonics:
                mag = [[row[c] for c in all_columns if 'inter_mag' in c or 'H1_mag' in c] for row in table.where('date == ' + str(calendar.timegm(from_dt.timetuple())))]
            else:
                mag = [[row[c] for c in all_columns if 'mag' in c and 'inter' not in c] for row in table.where('date == ' + str(calendar.timegm(from_dt.timetuple())))]
                

            if len(mag) > 0:
                fundamental_mag = mag[-1][1]
                mags.append(mag[0])
                if not show_fundamental and not interharmonics:
                    mags[-1][1] = 0.0
                if to_pu:
                    for i, v in enumerate(mags[-1]):
                        mags[-1][i] = mags[-1][i] * 100.0 / fundamental_mag

                if interharmonics:
                    mags[-1].remove(mags[-1][1])

            timer.add('harmonics, query ' + h)

        values_out = []
        if len(mags) > 0:
            # harmonic_numbers = np.arange(0, 64, step=0.5).tolist()#range(0, 64)
            # if interharmonics:
            #     harmonic_numbers = []
            #     harmonic_numbers_integer = range(0, 64)
            #     for h in harmonic_numbers_integer:
            #         # harmonic_numbers.append(str(h))
            #         harmonic_numbers.append(str(h) + ' interharmonic')
            # else:
            #     harmonic_numbers = range(0, 64)
            harmonic_numbers = range(0, 64)

            values_out = [harmonic_numbers, mags[0], mags[1], mags[2]]

        timer.add('harmonics, waveforms')
        timer.stop()
        return ujson.dumps(values_out)


def get_data_harmonic_trends(monitor_name, harmonics_type, harmonic_numbers, from_dt, to_dt, show_fundamental=False, to_pu=False):
    if INDIVIDUAL_HARMONICS:
        timer = NamedTimer()
        NUMBER_OF_VALUES = 576  # 2 days

        harmonics_phases = ['Va', 'Vb', 'Vc']
        if harmonics_type == 'current':
            harmonics_phases = ['Ia', 'Ib', 'Ic']

        harmonic_column_labels = ['date'] + ['H' + str(n) + '_mag' for n in harmonic_numbers]
        mags_sum = np.zeros(1 + len(harmonic_numbers))
        timer.add('harmonics trends, init')
        dfs = []

        for h in harmonics_phases:
            table = get_monitor_harmonics(monitor_name, h)
            mags = [[row[c] for c in harmonic_column_labels] for row in table.where('(date >= ' + str(calendar.timegm(from_dt.timetuple())) + ') & (date <= ' + str(calendar.timegm(to_dt.timetuple())) + ')')]
            if len(mags) > 0:
                df = pd.DataFrame(mags, columns=['date'] + harmonic_numbers)
                df['date'] = pd.to_datetime(df['date'], unit='s')
                df.set_index('date', inplace=True)
                dfs.append(df)
                timer.add('harmonics trends, query ' + h)

        if len(dfs) == 0:
            return '[]'

        df_concat = pd.concat(dfs)
        df_mean = df_concat.groupby(level=0).mean()

        if to_pu:
            df_mean = df_mean.div(df_mean[1], axis='index') * 100.0
        # if not show_fundamental:
        #     df_mean.drop(1, axis=1, inplace=True)
        #     harmonic_numbers.remove(1)

        # use pandas to resample, if needed
        if len(df_mean) <= NUMBER_OF_VALUES:
            df_mean.reset_index(inplace=True)
            # print 'not resampling'
            values_out = []
            for col in df_mean.columns.values:
                if col == 'date':
                    values_out.append((df_mean[col].values.astype(np.int64) // 10 ** 6).tolist())
                else:
                    values_out.append(df_mean[col].tolist())

            return ujson.dumps(values_out)
        else:
            days_delta = (to_dt - from_dt).days#len(df_mean) / (24.0 * 4.0)
            resampling_freq = get_resampling_freq(days_delta)
            resampling_type = 'mean'

            df2 = df_mean.resample(resampling_freq, how=resampling_type)
            # print 'resampling, number of samples:', len(df2), 'days_delta:', days_delta, 'resampling_freq', resampling_freq
            timer.add('harmonics trends, resampling')

            df2.replace([np.inf, -np.inf], np.nan, inplace=True)
            df2.dropna(inplace=True)
            df2.reset_index(inplace=True)

            # TODO use same approach for other plot types, rather than to_json?
            values_out = []
            for col in df2.columns.values:
                if col == 'date':
                    values_out.append((df2[col].values.astype(np.int64) // 10 ** 6).tolist())
                else:
                    values_out.append(df2[col].tolist())

            timer.add('harmonics trends, reorganise output')
            timer.stop()

            return ujson.dumps(values_out)


def precalculate_monitors_list():
    if len(monitors_list) == 0:
        for node, harmonics_node in zip(monitor_tables, harmonics_tables['Va']):
            monitor_name_index = get_abbreviated_name(node._v_title)

            harmonics_earliest_date = max([harmonics_tables[f]._f_get_child(monitor_name_index)._v_attrs.earliest_date for f in harmonics_tables])
            harmonics_latest_date = min([harmonics_tables[f]._f_get_child(monitor_name_index)._v_attrs.latest_date for f in harmonics_tables])
            
            monitors_list.append({
                'monitor_name_index': monitor_name_index,
                'monitor_name': node._v_title,
                'monitor_name_formatted': node._v_attrs.secondary_name_formatted,
                'ring_ID': node._v_attrs.ring_ID,
                'primary_name': node._v_attrs.primary_name_formatted,
                'earliest_date': node._v_attrs.earliest_date,
                'latest_date': node._v_attrs.latest_date,
                'harmonics_earliest_date': harmonics_earliest_date,
                'harmonics_latest_date': harmonics_latest_date,
                'total_rows': int(node._v_attrs.total_rows),
                'total_days': int(node._v_attrs.total_days)
            })

        monitors_list.sort(key=lambda x:(x['primary_name'], x['monitor_name_formatted']))



def get_monitors_from_ring_ID(ring_ID):
    matches = []

    for m in monitors_list:
        if ring_ID == m['ring_ID']:
            matches.append(m)

    return matches

def precalculate_C2C_events():
    shelf = shelve.open('sorted_events')
    sorted_events = shelf['sorted_events']
    shelf.close()

    for m in monitors_list:
        C2C_events[m['monitor_name_index']] = {
            'NOP_opened': [],
            'NOP_closed': [],
        }

    for ring_ID, events in sorted_events.iteritems():
        monitors = get_monitors_from_ring_ID(ring_ID)
        for event in events:
            for m in monitors:
                if event[1] == 'Closed':
                    C2C_events[m['monitor_name_index']]['NOP_closed'].append({"t": int(time.mktime(event[0].timetuple()) * 1000), "duration_ms": 0.0})
                else:
                    C2C_events[m['monitor_name_index']]['NOP_opened'].append({"t": int(time.mktime(event[0].timetuple()) * 1000), "duration_ms": 0.0})


class MonitorsResource(resource.Resource):
    isLeaf = True
    
    def render_GET(self, request):
        # e.g.: http://localhost/monitors
        request.setHeader("content-type", "application/json")
        return ujson.dumps(monitors_list)


class EventsResource(resource.Resource):
    isLeaf = True
    
    def render_GET(self, request):
        # e.g.: http://localhost/events
        request.setHeader("content-type", "application/json")
        uri_parts = request.uri.split('/')
        monitor_name = uri_parts[2]
        columns = ['date', 'Event_Type', 'duration_ms']

        values = []
        out = {}
        if monitor_name:
            table = get_monitor_from_tables(monitor_name, event_tables)
            values = [{c: row[c] for c in columns} for row in table]

            for v in values:
                if v['Event_Type'] not in out.keys():
                    out[v['Event_Type']] = [{"t": v['date'] * 1000, "duration_ms": v['duration_ms']}]
                else:
                    out[v['Event_Type']].append({"t": v['date'] * 1000, "duration_ms": v['duration_ms']})

            out['NOP_opened'] = C2C_events[monitor_name]['NOP_opened']
            out['NOP_closed'] = C2C_events[monitor_name]['NOP_closed']

        return ujson.dumps(out)

class EventWaveformResource(resource.Resource):
    isLeaf = True
    
    def render_GET(self, request):
        # e.g.: http://localhost/event/ASHTONPK171032/1372849093
        #       http://localhost/event/ONEILLS314504/1361346002
        #       http://localhost/event/THEARTHS167632/1361793957
        #       http://localhost/event/ASHTONPK171032/1396195657
        request.setHeader("content-type", "application/json")
        uri_parts = request.uri.split('/')
        monitor_name = uri_parts[2]
        date = uri_parts[3]

        columns = [
            'two_part',
            'Milliseconds',
            'N_E__V',
            'L1_N__V',
            'L2_N__V',
            'L3_N__V',
            'L1_Amp__A',
            'L2_Amp__A',
            'L3_Amp__A',
            'N_Amp__A'
        ]

        values = []
        if monitor_name:
            table = get_monitor_from_tables(monitor_name, event_tables)
            values = [{c: row[c] if c == columns[0] else row[c].tolist() for c in columns} for row in table.where('date == ' + date)]
            if len(values) == 1:
                return ujson.dumps(values[0])

        return '{}'


class DataResource(resource.Resource):
    isLeaf = True

    def render_GET(self, request):
        # e.g.: http://localhost/rms/GREENLN231207/from/2013/08/23/12:00:00/to/2013/08/23/19:15:00/Current_RMS_10_Cycle_Avg_A/VAR_L2_10_Cycle_Max_kVAR
        request.setHeader("content-type", "application/json")

        uri_parts = request.uri.split('/')
        monitor_name = uri_parts[2]
        from_year = uri_parts[4]
        from_month = uri_parts[5]
        from_day = uri_parts[6]
        from_time = uri_parts[7]
        from_date_str = from_year + '-' + from_month + '-' + from_day + ' ' + from_time
        from_dt = datetime.datetime.strptime(from_date_str, '%Y-%m-%d %H:%M:%S')
        to_year = uri_parts[9]
        to_month = uri_parts[10]
        to_day = uri_parts[11]
        to_time = uri_parts[12]
        to_date_str = to_year + '-' + to_month + '-' + to_day + ' ' + to_time
        to_dt = datetime.datetime.strptime(to_date_str, '%Y-%m-%d %H:%M:%S')

        max_len = len(uri_parts)
        columns = ['date']
        for i in range(13, max_len):
            columns.append(uri_parts[i])

        data = get_data(monitor_name, from_dt, to_dt, columns)
        ret = '{' +\
            '"error":"none",' + \
            '"monitor_name":"' + monitor_name + '",' + \
            '"from":"' + from_date_str + '",' + \
            '"to":"' + to_date_str + '",' + \
            '"columns":' + ujson.dumps(columns) + ',' + \
            '"data":' + data + '}'

        return ret


class AnnualHeatMapResource(resource.Resource):
    isLeaf = True

    def render_GET(self, request):
        request.setHeader("content-type", "application/json")

        uri_parts = request.uri.split('/')
        monitor_name = uri_parts[2]
        max_len = len(uri_parts)

        if max_len != 4:
            return ujson.dumps({'error': 'data column not specified'})

        columns = ['date']
        for i in range(3, max_len):
            columns.append(uri_parts[i])

        if len(columns) != 2:
            return ujson.dumps({'error': 'too many columns specified'})


        data = get_data_heat_map(monitor_name, columns)
        ret = '{' + \
            '"error":"none",' + \
            '"monitor_name":"' + monitor_name + '",' + \
            '"columns":' + ujson.dumps(columns) + ',' + \
            '"data":' + data + '}'
        return ret


class WaveformResource(resource.Resource):
    isLeaf = True

    def render_GET(self, request):
        # e.g.: http://localhost/waveforms/voltage/ASHTONPK171032/2013/08/10/11:45:00
        #       http://localhost/waveforms/current/ASHTONPK171032/2013/08/10/11:30:00
        request.setHeader("content-type", "application/json")

        uri_parts = request.uri.split('/')
        monitor_name = uri_parts[2]
        harmonics_type = uri_parts[3]
        from_year = uri_parts[4]
        from_month = uri_parts[5]
        from_day = uri_parts[6]
        from_time = uri_parts[7]
        from_date_str = from_year + '-' + from_month + '-' + from_day + ' ' + from_time
        from_dt = datetime.datetime.strptime(from_date_str, '%Y-%m-%d %H:%M:%S')

        data = get_data_waveform(monitor_name, harmonics_type, from_dt)
        ret = '{' + \
            '"error":"none",' + \
            '"monitor_name":"' + monitor_name + '",' + \
            '"from":"' + from_date_str + '",' + \
            '"harmonics_type":"' + harmonics_type + '",' + \
            '"data":' + data + '}'
        return ret


class HarmonicsResource(resource.Resource):
    isLeaf = True

    def render_GET(self, request):
        # e.g.: http://localhost/harmonics/voltage/ASHTONPK171032/2013/08/10/11:45:00
        #       http://localhost/harmonics/current/ASHTONPK171032/2013/08/10/11:30:00
        request.setHeader("content-type", "application/json")

        uri_parts = request.uri.split('/')
        monitor_name = uri_parts[2]
        harmonics_type = uri_parts[3]
        from_year = uri_parts[4]
        from_month = uri_parts[5]
        from_day = uri_parts[6]
        from_time = uri_parts[7]
        from_date_str = from_year + '-' + from_month + '-' + from_day + ' ' + from_time
        from_dt = datetime.datetime.strptime(from_date_str, '%Y-%m-%d %H:%M:%S')

        show_fundamental = True
        if 'nofundamental' in uri_parts:
            show_fundamental = False

        to_pu = False
        if 'perunit' in uri_parts:
            to_pu = True

        interharmonics = False
        if 'interharmonics' in uri_parts:
            interharmonics = True

        data = get_data_harmonics(monitor_name, harmonics_type, from_dt, show_fundamental, to_pu, interharmonics)
        ret = '{' + \
            '"error":"none",' + \
            '"monitor_name":"' + monitor_name + '",' + \
            '"from":"' + from_date_str + '",' + \
            '"harmonics_type":"' + harmonics_type + '",' + \
            '"data":' + data + '}'
        return ret


class HarmonicsTrendsResource(resource.Resource):
    isLeaf = True

    def render_GET(self, request):
        # e.g.: http://localhost/rms/GREENLN231207/from/2013/08/23/12:00:00/to/2013/08/23/19:15:00/Current_RMS_10_Cycle_Avg_A/VAR_L2_10_Cycle_Max_kVAR
        request.setHeader("content-type", "application/json")

        uri_parts = request.uri.split('/')
        monitor_name = uri_parts[2]
        harmonics_type = uri_parts[3]
        from_year = uri_parts[5]
        from_month = uri_parts[6]
        from_day = uri_parts[7]
        from_time = uri_parts[8]
        from_date_str = from_year + '-' + from_month + '-' + from_day + ' ' + from_time
        from_dt = datetime.datetime.strptime(from_date_str, '%Y-%m-%d %H:%M:%S')
        to_year = uri_parts[10]
        to_month = uri_parts[11]
        to_day = uri_parts[12]
        to_time = uri_parts[13]
        to_date_str = to_year + '-' + to_month + '-' + to_day + ' ' + to_time
        to_dt = datetime.datetime.strptime(to_date_str, '%Y-%m-%d %H:%M:%S')

        show_fundamental = True
        if 'nofundamental' in uri_parts:
            show_fundamental = False

        to_pu = False
        if 'perunit' in uri_parts:
            to_pu = True

        harmonic_numbers = [1, 2, 3, 5, 7, 9, 11, 13, 15, 17]
        data = get_data_harmonic_trends(monitor_name, harmonics_type, harmonic_numbers, from_dt, to_dt, show_fundamental, to_pu)
        ret = '{' +\
            '"error":"none",' + \
            '"monitor_name":"' + monitor_name + '",' + \
            '"harmonic_numbers":' + ujson.dumps(harmonic_numbers) + ',' + \
            '"from":"' + from_date_str + '",' + \
            '"to":"' + to_date_str + '",' + \
            '"data":' + data + '}'

        return ret


FILENAME = 'data/monitoring-data-float32-no-compression.h5'
HARMONICS_FILENAMES = {
    'Va': 'data/L1-N(V) Harmonics.h5',
    'Vb': 'data/L2-N(V) Harmonics.h5',
    'Vc': 'data/L3-N(V) Harmonics.h5',
    'Ia': 'data/L1(A) Harmonics.h5',
    'Ib': 'data/L2(A) Harmonics.h5',
    'Ic': 'data/L3(A) Harmonics.h5'
}
EVENT_FILENAME = 'data/event-data.h5'

INDIVIDUAL_HARMONICS = True
IN_MEMORY = False
USING_SSL = False
PRECALCULATE_DAILY_RESAMPLING = False
PRECALCULATE_HEATMAP_DATA = False

monitors_list = []
daily_resampled_data = {}
heatmap_precalculated_data = {}
harmonics_tables = {}
C2C_events = {}
# negative_batch_map = {}

if __name__ == '__main__':
    # open database file
    if IN_MEMORY:
        # note that 'driver_core_backing_store=0' disables persisting changes to disk
        h5file = tables.open_file(FILENAME, driver="H5FD_CORE", driver_core_backing_store=0)
    else:
        h5file = tables.open_file(FILENAME)
    monitor_tables = h5file.root

    # find_negative_real_power_measurements()

    if INDIVIDUAL_HARMONICS:
        for f in HARMONICS_FILENAMES:
            h5file = tables.open_file(HARMONICS_FILENAMES[f], mode='a')
            harmonics_tables[f] = h5file.root

    h5file = tables.open_file(EVENT_FILENAME)
    event_tables = h5file.root

    precalculate_monitors_list()
    precalculate_C2C_events()


    for m in monitors_list:
        print m['monitor_name_index']
        correct_waveform_phasors(m['monitor_name_index'])
