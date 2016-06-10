import calendar
import datetime
import time
import tables
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt

from scipy import signal
from scipy import interpolate
from scipy.signal import butter, filtfilt
from scipy.interpolate import UnivariateSpline
from scipy.interpolate import splev
from scipy.interpolate import splrep
from scipy.interpolate import spline

import numpy.linalg as npl


matplotlib.rcParams['ps.useafm'] = True
matplotlib.rcParams['pdf.use14corefonts'] = True
# matplotlib.rcParams['text.usetex'] = True





# location = 'BKGEORGEST166081' # commercial/industrial
# location = 'ABBEYNATIONAL166068' # only a few days
location = 'ASHTONPK171032'
data_column = 'Current_RMS_10_Cycle_Max_A'
from_date_str = '2013/01/01/00:00:00'
to_date_str = '2015/04/01/00:00:00'
from_dt = datetime.datetime.strptime(from_date_str, '%Y/%m/%d/%H:%M:%S')
to_dt = datetime.datetime.strptime(to_date_str, '%Y/%m/%d/%H:%M:%S')
days_delta = (to_dt - from_dt).days
target_number_of_points = 500


def nanrms(x, axis=None):
    return np.sqrt(np.nanmean(np.square(x), axis=axis))
    # return np.sqrt(np.mean(np.square(x)))

def corr(x, y):
    # assert len(x) == len(y)
    n = len(x)
    # assert n > 0
    avg_x = np.mean(x)
    avg_y = np.mean(y)
    diffprod = 0
    xdiff2 = 0
    ydiff2 = 0
    for i in range(n):
        xdiff = x[i] - avg_x
        ydiff = y[i] - avg_y
        diffprod += xdiff * ydiff
        xdiff2 += xdiff * xdiff
        ydiff2 += ydiff * ydiff

    return diffprod / np.sqrt(xdiff2 * ydiff2)


class NamedTimer():
    def __init__(self):
        self.things = [('start', time.clock())]

    def add(self, name):
        self.things.append((name, time.clock()))

    def stop(self):
        total = sum([self.things[i][1] - self.things[i - 1][1] for i, x in enumerate(self.things) if i > 0])
        for i, x in enumerate(self.things):
            if i > 0:
                diff_time = self.things[i][1] - self.things[i - 1][1]
                print x[0].ljust(40), '{:.3f} s,'.format(diff_time), '{:.1f}%'.format(100.0 * diff_time / total)


class MyUnivariateSpline(UnivariateSpline):
    @classmethod
    def _from_tck(cls, t, c, k):
        self = cls.__new__(cls)
        self._eval_args = t, c, k
        #_data == x,y,w,xb,xe,k,s,n,t,c,fp,fpint,nrdata,ier
        self._data = [None,None,None,None,None,k,None,len(t),t,c,None,None,None,None]
        return self
 
    def derivative_spline(self):
        """
        Compute the derivative spline of a spline in FITPACK tck
        representation.
        """
        t, c, k = self._eval_args
        if k <= 0:
            raise ValueError("Cannot differentiate order 0 spline")
        # Compute the denominator in the differentiation formula.
        dt = t[k+1:-1] - t[1:-k-1]
        # Compute the new coefficients
        d = (c[1:-1-k] - c[:-2-k]) * k / dt
        # Adjust knots
        t2 = t[1:-1]
        # Pad coefficient array to same size as knots (FITPACK convention)
        d = np.r_[d, [0]*k]
        # Done, return a new spline
        return self._from_tck(t2, d, k-1)



def get_resampling_freq(original_num_samples, days_delta2):
    # # num_days = {days: }
    samples_per_day = 12 * 24
    # decimate_by = np.ceil(original_num_samples / target_number_of_points)
    # new_interval = int(np.round(original_num_samples * samples_per_day) / decimate_by)

    days_delta = float(original_num_samples) / float(samples_per_day)

    # target_number_of_points = days_delta * rate_per_day
    rate_per_day = target_number_of_points / days_delta
    rate_in_mins = float(rate_per_day) / (24.0 * 60.0)
    interval = int(np.round(1.0 / rate_in_mins))

    print 'days', days_delta, 'rate_per_day', rate_per_day, 'rate_in_mins', rate_in_mins, 'interval', interval

    return str(interval) + 'Min', str(int(np.round(interval / 2))) + 'Min'

    # resampling_freq = '24H'
    # loffset = '12H'
    # if days_delta <= 4:
    #     resampling_freq = '5Min'
    #     loffset = '2.5min'
    # elif days_delta < 8:
    #     resampling_freq = '10Min'
    #     loffset = '5min'
    # elif days_delta < 15:
    #     resampling_freq = '30Min'
    #     loffset = '15min'
    # elif days_delta < 30:
    #     resampling_freq = '1H'
    #     loffset = '30min'
    # elif days_delta < 60:
    #     resampling_freq = '2H'
    #     loffset = '1H'
    # elif days_delta < 120:
    #     resampling_freq = '240Min'
    #     loffset = '2H'
    # elif days_delta < 180:
    #     resampling_freq = '6H'
    #     loffset = '3H'
    # elif days_delta < 240:
    #     resampling_freq = '8H'
    #     loffset = '4H'
    # elif days_delta < 480:
    #     resampling_freq = '12H'
    #     loffset = '6H'
    # return resampling_freq, loffset

# TODO could use df2.to_json(orient="index") on resampled df to get valid output (could change JSON format to help UI code)?

# TODO multi-stage method, depending on time range and number of samples allowed
#      do freq analysis to determine best method?


def get_monitor(monitor_name):
    for node in monitor_tables:
        name = node._v_title.replace(' ', '').replace('(', '').replace(')', '').replace('.', '')
        if name == monitor_name:
            return node._f_get_child('readout')
    return None


def get_all_data(monitor_name, columns):
    from_dt = datetime.datetime.strptime(from_date_str, '%Y/%m/%d/%H:%M:%S')
    to_dt = datetime.datetime.strptime(to_date_str, '%Y/%m/%d/%H:%M:%S')

    table = get_monitor(monitor_name)
    values = [[row[c] for c in columns] for row in table.where('(date >= ' + str(calendar.timegm(from_dt.timetuple())) + ') & (date <= ' + str(calendar.timegm(to_dt.timetuple())) + ')')]

    return values


def get_all_data_padded(monitor_name,  columns):
    from_dt = datetime.datetime.strptime(from_date_str, '%Y/%m/%d/%H:%M:%S')
    to_dt = datetime.datetime.strptime(to_date_str, '%Y/%m/%d/%H:%M:%S')

    table = get_monitor(monitor_name)
    values = [[row[c] for c in columns] for row in table.where('(date >= ' + str(calendar.timegm(from_dt.timetuple())) + ') & (date <= ' + str(calendar.timegm(to_dt.timetuple())) + ')')]

    values_out = []
    normal_diff = 5 * 60
    for i, v in enumerate(values):
        if i == 0:
            values_out.append(v)
        elif i == len(values) - 1:
            continue
        else:
            diff = values[i][0] - values[i - 1][0]
            if diff > normal_diff:
                # print 'diff:', diff, values[i - 1][0], values[i][0]
                num_missing = (diff / normal_diff)
                # print '  num_missing:', num_missing
                for j in range(1, num_missing):
                    # print values[i - 1][0] + j * 300
                    values_out.append([values[i - 1][0] + j * 300, 0])    # TODO may be more data columns
            values_out.append(v)

    return values_out


# def decimate(x, q):

def movingaverage(interval, window_size):
    window = np.ones(int(window_size)) / float(window_size)
    return np.convolve(interval, window, 'same')



def do_sinc_resample(x, y, xnew):
    m, n = (len(x), len(xnew))
    T = 1./n
    A = np.zeros((m, n))

    for i in range(0,m):
        A[i, :] = np.sinc((x[i] - xnew) / T)

    return npl.lstsq(A, y)[0]


def do_spline_resample(x, y, xnew):
    return splev(xnew, splrep(x, y))



print pd.__version__, tables.__version__

timer = NamedTimer()

plots = []


# h5file = tables.open_file('../pqube/monitoring-data.h5', mode="r")
# signal_data = h5file.root.ABBEYNATIONAL166068.readout
# data_frame = pd.DataFrame.from_records(signal_data)

# print data_frame.query("index < 1370952000")#.describe()

# h5file.close()


store = pd.HDFStore('data/monitoring-data-float32-no-compression.h5')
DF_test = store['/' + location + '/readout']
# print 'index:', DF_test.index
DF_test.set_index('date', inplace=True) # TODO needed?
# print 'index:', DF_test.index

# from pandas.io.pytables import Term
# print DF_test.select("index > 50 & columns=[data_column]")#.describe()
# print DF_test[data_column].describe()


# print store.select('ABBEYNATIONAL166068/readout', "index > 50 & columns=[data_column]")

timer.add('open file and index')

# print DF_test.describe()
series = DF_test[data_column]
result = DF_test.query('(index >= 1370952000 & index <= 1370954100)')

# result = DF_test['Current_RMS_10_Cycle_Avg_A', DF_test.index <= 1370954100]#'(index >= 1370952000 & index <= 1370954100)']

print result[data_column]
# print series[(series.index >= 1370952000, series.index <= 1370954100)]#.query('(date > 1)')


store.close()

timer.add('query and print DF')



# open database file in memory
f = tables.open_file('data/monitoring-data-float32-no-compression.h5')#, driver="H5FD_CORE")
monitor_tables = f.root

timer.add('open file')

# all_data = get_all_data('ASHTONPK171032', ['date', data_column])
all_data = get_all_data(location, ['date', data_column])

timer.add('get data')

# input_samples = range(0, len(all_data))
input_t_raw = [a[0] for a in all_data]
input_t = [datetime.datetime.utcfromtimestamp(int(a[0])) for a in all_data]
input_signal = [a[1] for a in all_data]

timer.add('reformat data')

# input_dict = {t: x for t, x in zip(input_t, input_signal)}
index = pd.date_range(input_t[0], input_t[-1], freq='5Min')
# df = pd.DataFrame(input_signal, index=input_t, columns=[data_column])
df = pd.DataFrame(all_data, columns=['date', data_column])
df['date'] = pd.to_datetime(df['date'], unit='s')
df.set_index('date', inplace=True)
# print df.describe()

# print df.describe()
# print df
# df.set_index(index, append=True, inplace=True)
# df1 = df.reindex(index=index, columns=list(df.columns))

timer.add('create and reindex DataFrame')

decimation_factor = int(np.ceil(len(input_signal) / target_number_of_points))
decimated = input_signal[::decimation_factor]
decimated_raw_t = input_t_raw[::decimation_factor]
decimated_t = [datetime.datetime.utcfromtimestamp(int(a)) for a in decimated_raw_t]
# print 'input_t_raw', datetime.datetime.utcfromtimestamp(int(input_t_raw[0])), input_t_raw[0]
# print 'decimated_flitflit', datetime.datetime.utcfromtimestamp(int(decimated_flitflit_raw_t[0])), decimated_flitflit_t[0]

# for i in range(50):
#     print datetime.datetime.utcfromtimestamp(int(input_t_raw[i])), datetime.datetime.utcfromtimestamp(int(decimated_flitflit_raw_t[i]))

# Zero-phase filter
plots.append({'x': decimated_t, 'y': decimated, 'label': 'Decimation', 'hide': False})
timer.add(plots[-1]['label'])

# print df1[data_column]value_counts()
d = {}
for col in df.columns.values.tolist():
    if 'Max' in col:
        d[col] = 'max'
    elif 'Min' in col:
        d[col] = 'min'
    else:
        d[col] = 'mean'

print df.describe()
resampling_freq, loffset = get_resampling_freq(len(input_signal), days_delta)
print 'days:', days_delta, 'resampling_freq', resampling_freq, 'loffset', loffset
df2 = df.resample(resampling_freq, how=d, loffset=loffset)#, label='right', closed='right', base=0
print df2.describe()


# TODO update c2c website with loffset; test with emulated "laggy" Chrome dev mode
# TODO do fractional sampling periods (e.g. 1.1H) affect performance?


plots.append({'x': df2.index, 'y': df2[data_column], 'label': 'pandas re-sampling', 'hide': False})
timer.add(plots[-1]['label'])


# print pd.isnull(df1).describe()
# print df[data_column]
# print df[0:5].describe()


# # check for duplicates
# print set([x for x in input_t_raw if input_t_raw.count(x) > 1])

# moving_avg = movingaverage(input_signal, 3)
# print 'moving average:'
# print moving_avg, len(moving_avg)

# TODO supports min and max?
df_rolling_mean = pd.rolling_max(df, int(np.round(float(len(input_t_raw)) / float(target_number_of_points))), how=d, center=True)

plots.append({'x': df_rolling_mean.index, 'y': df_rolling_mean[data_column], 'label': 'pandas moving average', 'hide': True})
timer.add(plots[-1]['label'])


print 'len(input_signal)', len(input_signal), 'target_number_of_points', target_number_of_points, 'decimation_factor', decimation_factor
df_rolling_mean_decimated = df_rolling_mean.iloc[::decimation_factor, :]
# print df[:decimation_factor], len(df)
# print df_rolling_mean[:decimation_factor], len(df_rolling_mean)
plots.append({'x': df_rolling_mean_decimated.index, 'y': df_rolling_mean_decimated[data_column], 'label': 'pandas moving maxmium, decimated', 'hide': False})
timer.add(plots[-1]['label'])



x2 = np.linspace(input_t_raw[0], input_t_raw[-1], target_number_of_points)
x2_t = [datetime.datetime.utcfromtimestamp(int(a)) for a in x2]

# sinc_resample = do_sinc_resample(input_t_raw, input_signal, x2)

# timer.add('sinc_resample')

# # spline_resample = spline(input_t_raw, input_signal, x2)


# this gives the same result as the normal cubic spline method, but takes about 50 s
# spline_resample_UnivariateSpline = UnivariateSpline(input_t_raw, input_signal)
# spline_resample = spline_resample_UnivariateSpline(x2)


critical_frquency = 1.41 * target_number_of_points / float(len(input_signal))
b, a = butter(5, critical_frquency)
filtfilt_filtered = filtfilt(b, a, input_signal)

plots.append({'x': input_t, 'y': filtfilt_filtered, 'label': 'LPF', 'hide': True})
timer.add(plots[-1]['label'])


# note that signal.decimate() uses an order 8 Chebyshev type I filter; it works for the data but not on the time values
# also note that it results in a significant phase shift

# decimated_flitflit_scipy = signal.decimate(filtfilt_filtered, decimation_factor)
# decimated_flitflit_scipy_raw_t = signal.decimate(input_t_raw, decimation_factor)
# decimated_flitflit_scipy_t = [datetime.datetime.utcfromtimestamp(int(a)) for a in decimated_flitflit_scipy_raw_t]
# plots.append({'x': decimated_flitflit_scipy_t, 'y': decimated_flitflit_scipy, 'label': 'filtfilt decimated (scipy)', 'hide': False})
# timer.add(plots[-1]['label'])



decimated_flitflit = filtfilt_filtered[::decimation_factor]
decimated_flitflit_raw_t = input_t_raw[::decimation_factor]
decimated_flitflit_t = [datetime.datetime.utcfromtimestamp(int(a)) for a in decimated_flitflit_raw_t]
# print 'input_t_raw', datetime.datetime.utcfromtimestamp(int(input_t_raw[0])), input_t_raw[0]
# print 'decimated_flitflit', datetime.datetime.utcfromtimestamp(int(decimated_flitflit_raw_t[0])), decimated_flitflit_t[0]

# for i in range(50):
#     print datetime.datetime.utcfromtimestamp(int(input_t_raw[i])), datetime.datetime.utcfromtimestamp(int(decimated_flitflit_raw_t[i]))

# Zero-phase filter
plots.append({'x': decimated_flitflit_t, 'y': decimated_flitflit, 'label': 'LPF, decimated', 'hide': False})
timer.add(plots[-1]['label'])



spline_resample = do_spline_resample(input_t_raw, input_signal, x2)
plots.append({'x': x2_t, 'y': spline_resample, 'label': 'Cubic spline interpolation', 'hide': False})
timer.add(plots[-1]['label'])


# diff = np.diff(filtfilt_filtered, n=1).tolist()
# diff.append(0)
# # diff.insert(0, 0)
# print len(diff), len(filtfilt_filtered), len(input_t)
# # diff.pop()

# plots.append({'x': input_t, 'y': diff, 'label': 'differentiated', 'hide': True})
# timer.add(plots[-1]['label'])


# max_diff = []
# # note: not sure about this method, but it doesn't work well even for ~2048 points
# # sorted_dt = sorted(zip(diff, filtfilt_filtered, input_t), key=lambda k: abs(k[0]), reverse=True)
# # for i, (dt, x, t) in enumerate(sorted_dt):
# #     if i > 0 and ((sorted_dt[i - 1][0] < 0 and sorted_dt[i][0] > 0) or (sorted_dt[i - 1][0] > 0 and sorted_dt[i][0] < 0)):
# #         if len(max_diff) < target_number_of_points:
# #             max_diff.append((t, x))
# #     #     # print dt, t, x


# # note that this "root-seeker" includes many insignificant roots (even with pre-filtering), and thus needs many points to represent original waveform
# sorted_dt = sorted([(d, ff, in_t) for d, ff, in_t in zip(diff, filtfilt_filtered, input_t) if abs(d) < 1.0], key=lambda k: abs(np.mean(filtfilt_filtered) - k[1]), reverse=True)
# print 'len(sorted_dt)', len(sorted_dt)
# for i, (dt, x, t) in enumerate(sorted_dt):
#     if len(max_diff) < target_number_of_points:
#         max_diff.append((t, x))
# # TODO can second derivative be used to infer importance of points (i.e. only pick one point near peaks)?


# # # note that this "root-seeker" includes many insignificant roots (even with pre-filtering), and thus needs many points to represent original waveform
# # sorted_dt = sorted(zip(diff, filtfilt_filtered, input_t), key=lambda k: abs(k[0]), reverse=False)
# # for i, (dt, x, t) in enumerate(sorted_dt):
# #     if len(max_diff) < target_number_of_points:
# #         max_diff.append((t, x))


# # # primary sort by abs of derivative, then by negative deviation from mean
# # # note that the "abs deviation from mean" approach takes a long time and often "misses" important features; there is no guarantee that differentiating will successfully find the important features
# # sorted_dt = sorted(zip(diff, filtfilt_filtered, input_t), key=lambda k: (abs(k[0]), -abs(np.mean(filtfilt_filtered) - k[1])))
# # for i, (dt, x, t) in enumerate(sorted_dt):
# #     if len(max_diff) < target_number_of_points:
# #         max_diff.append((t, x))
# #         # print dt, t, x


# max_diff = sorted(max_diff, key=lambda k: k[0])

# plots.append({'x': [a[0] for a in max_diff], 'y': [a[1] for a in max_diff], 'label': 'Differentiated with feature detection', 'hide': True})
# timer.add(plots[-1]['label'])



# from: https://gist.github.com/pv/5504366
# fit a spline (must use order 4, since roots() works only for order 3)
s1 = MyUnivariateSpline(input_t_raw, filtfilt_filtered, s=0, k=3+1)
# Compute the derivative spline of the fitted spline
s2 = s1.derivative_spline()
# Roots (works only with order 3 splines)
r = s2.roots()
# print "minima/maxima:  x =", r/np.pi, len(r)

# get x and y values for roots (limit on number of roots?)
MyUnivariateSpline_t = []
MyUnivariateSpline_y = []
for i in r:
    MyUnivariateSpline_t.append(datetime.datetime.utcfromtimestamp(int(i)))
    MyUnivariateSpline_y.append(np.interp(i, input_t_raw, input_signal))

plots.append({'x': MyUnivariateSpline_t, 'y': MyUnivariateSpline_y, 'label': 'LPF, univariate spline derivative roots', 'hide': True})
timer.add(plots[-1]['label'])



# down_sampled, down_sampled_t_raw = signal.resample(input_signal, target_number_of_points, t=input_t_raw)
# down_sampled_t = [datetime.datetime.utcfromtimestamp(a) for a in down_sampled_t_raw]

# plots.append({'x': down_sampled_t, 'y': down_sampled, 'label': 'signal.resample', 'hide': False})
# timer.add(plots[-1]['label'])



interp1d_f = interpolate.interp1d(input_t_raw, input_signal)
interp1d_t_raw = np.linspace(input_t_raw[0], input_t_raw[-1], target_number_of_points)
interp1d_t = [datetime.datetime.utcfromtimestamp(int(a)) for a in interp1d_t_raw]
interp1d = interp1d_f(interp1d_t_raw)

plots.append({'x': interp1d_t, 'y': interp1d, 'label': 'SciPy "interp1d"', 'hide': True})
timer.add(plots[-1]['label'])

timer.stop()
f.close()



# print len(all_data), len(input_signal), len(down_sampled), len(down_sampled_t_raw), len(decimated_flitflit)



# fig = plt.figure(figsize=(22, 6), facecolor='w')

# print sum(1 for i in plots if i['hide'] == False)



def get_error(x_test, y_test, x_source, y_source):
    # error = []
    # for x, y in zip(x_test, y_test):
    #     error.append(np.interp(time.mktime(x.timetuple()), x_source, y_source) - y)

    # return error
    upscaled_values = []
    error = []
    x_test_raw = [time.mktime(x.timetuple()) for x in x_test]
    for x, y in zip(x_source, y_source):
        upscaled_values.append(np.interp(x, x_test_raw, y_test))
        error.append(upscaled_values[-1] - y)

    print len(y_source), len(upscaled_values)
    print np.nan_to_num(y_source[0]), np.nan_to_num(upscaled_values[0])
    # for a, b in zip(y_source, upscaled_values):
    #     print a, b
    print corr(np.nan_to_num(y_source), np.nan_to_num(upscaled_values))
    # TODO compute correlation too?

    return error


shown_plots = [p for p in plots if p['hide'] == False]
fig, axes = plt.subplots(figsize=(24, 9.2), facecolor='w', nrows=len(shown_plots), ncols=1, sharex=True, sharey=False)

for i, plot in enumerate(shown_plots):
    if plot['hide'] == False:
        axes[i].plot(input_t, input_signal, c='k', marker='None', alpha=0.3, linewidth=1.0, label='Original data (' + str(len(input_signal)) + ' points)')
        plot_colour = 'r'
        if len(plot['y']) < len(input_signal):
            plot_colour = 'k'
        # error = get_error(plot['x'], plot['y'], input_t_raw, input_signal)
        # axes[i].plot(plot['x'], plot['y'], c=plot_colour, marker='None', alpha=1.0, linewidth=1.0, label=plot['label'] + '\n(' + str(len(plot['y'])) + ' points, RMS error: ' + '{:.1f} A'.format(nanrms(error)) + ')')
        axes[i].plot(plot['x'], plot['y'], c=plot_colour, marker='None', alpha=1.0, linewidth=1.0, label=plot['label'] + ' (' + str(len(plot['y'])) + ' points)')
        # plt.plot(input_t, input_signal, c='k', marker='None', alpha=0.3, linewidth=1.0, label='original data, ' + str(len(input_signal)))
        # plt.plot(input_t, input_signal, c='k', marker='None', alpha=0.3, linewidth=1.0, label='original data, ' + str(len(input_signal)))  

        # # axes[i].plot(plot['x'], error, c='purple', marker='None', alpha=0.8, linewidth=1.0, label='error, ' + str(len(plot['y'])))
        # axes[i].plot(input_t, error, c='purple', marker='None', alpha=0.8, linewidth=1.0, label='error (RMS: ' + '{:.1f} A'.format(nanrms(error)) + ')')
        
        axes[i].set_ylim([0, 600])
        leg = axes[i].legend(loc=4)
        leg.get_frame().set_alpha(0.9)

        if i == len(shown_plots) - 1:
            for tick in axes[i].xaxis.get_major_ticks():
                tick.label.set_fontsize(16)

# plt.plot(input_t, input_signal, c='k', marker='None', alpha=0.3, linewidth=1.0, label='original data, ' + str(len(input_signal)))
# plt.plot(input_t, filtfilt_filtered, c='k', marker='None', alpha=0.5, linewidth=1.0, label='filtfilt data, ' + str(len(filtfilt_filtered)))
# # plt.plot(down_sampled_t, down_sampled, c='purple', marker='None', alpha=0.6, linewidth=1.0, label='downsampled data, ' + str(len(down_sampled)))
# # plt.plot(decimated_flitflit_t, decimated_flitflit, c='k', marker='None', alpha=0.8, linewidth=1.0, label='filtfilt, decimated data, ' + str(len(decimated_flitflit)))
# plt.plot(interp1d_t, interp1d, c='orange', marker='None', alpha=0.8, linewidth=1.0, label='interp1d, ' + str(len(interp1d)))
# # plt.plot(moving_avg, c='k', marker='None', alpha=0.8, linewidth=1.0, label='moving_avg, ' + str(len(moving_avg)))

# # plt.plot(df2.index, df2.Current_RMS_10_Cycle_Avg_A, c='r', marker='None', alpha=0.4, linewidth=1.0, label='pandas: resmapled DataFrame, ' + str(len(df2)))
# # plt.plot(df_rolling_mean.index, df_rolling_mean.Current_RMS_10_Cycle_Avg_A, c='g', marker='None', alpha=0.1, linewidth=1.0, label='pandas: rolling mean, ' + str(len(df_rolling_mean)))
# # plt.plot(df_rolling_mean_decimated.index, df_rolling_mean_decimated.Current_RMS_10_Cycle_Avg_A, c='g', marker='None', alpha=0.4, linewidth=1.0, label='pandas: rolling mean and decimated, ' + str(len(df_rolling_mean_decimated)))
# plt.plot([a[0] for a in max_diff], [a[1] for a in max_diff], c='b', marker='None', alpha=0.8, linewidth=1.0, label='feature detection, ' + str(len(max_diff)))

# plt.plot(x2_t, sinc_resample, c='brown', marker='None', alpha=0.8, linewidth=1.0, label='sinc resample, ' + str(len(sinc_resample)))
# plt.plot(x2_t, spline_resample, c='brown', marker='None', alpha=0.8, linewidth=1.0, label='cubic spline resample, ' + str(len(spline_resample)))
# plt.xlabel('samples', fontsize=12)
# plt.legend()
fig.autofmt_xdate(rotation=0, ha='center')
fig.text(0.0075, 0.5, 'Current 10-cycle RMS, 5-minute maximum (A)', ha='center', va='center', rotation='vertical', fontsize=16)
plt.tight_layout()
plt.subplots_adjust(left=0.032, top=0.99, bottom=0.031, right=0.980)#, bottom=0.02, right=0.995, top=0.995, wspace=0.20, hspace=0.80)

# plt.axis([None, None, -500, 500])
plt.savefig('re-sampling-results.png', dpi=170)
# plt.savefig('re-sampling-results.eps')
# plt.show()





# print corr([1,2,3,4,5,6], [6,2,3,4,5,6])