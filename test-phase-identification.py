import numpy as np

def add_angle(a, b):
    total = a + b
    if (total >= 360.0):
        total = total - 360.0
    return total

def sub_angle(a, b):
    total = a - b
    if (total < 0.0):
        total = 360.0 - total
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

def neg_seq_mag_same_mags(a, b, c):
    b_ang_new = add_angle(b[1], 240.0)
    c_ang_new = add_angle(c[1], 120.0)

    re = np.cos(a[1] * np.pi / 180.0) + np.cos(b_ang_new * np.pi / 180.0) + np.cos(c_ang_new * np.pi / 180.0)
    im = np.sin(a[1] * np.pi / 180.0) + np.sin(b_ang_new * np.pi / 180.0) + np.sin(c_ang_new * np.pi / 180.0)

    return np.sqrt(re*re + im*im)

def pos_seq_mag(a, b, c):
    b_ang_new = add_angle(b[1], 120.0)
    c_ang_new = add_angle(c[1], 240.0)

    re = a[0] * np.cos(a[1] * np.pi / 180.0) + b[0] * np.cos(b_ang_new * np.pi / 180.0) + c[0] * np.cos(c_ang_new * np.pi / 180.0)
    im = a[0] * np.sin(a[1] * np.pi / 180.0) + b[0] * np.sin(b_ang_new * np.pi / 180.0) + c[0] * np.sin(c_ang_new * np.pi / 180.0)

    return np.sqrt(re*re + im*im)

def approx_equal(a, b, tol):
    return abs(a - b) < tol

tests = [
    {'phasors': [(1.0, 0.0), (1.0, 240.0), (1.0, 120.0)], 'pf': 1.00, 'correct_phase_order': (0, 1, 2), 'correct_polarity': (1, 1, 1)},
    {'phasors': [(1.0, 0.0), (0.01, 240.0), (0.01, 120.0)], 'pf': 0.9, 'correct_phase_order': (0, 1, 2), 'correct_polarity': (1, 1, 1)},
    {'phasors': [(1.0, 0.0), (1.0, 240.0), (1.0, 120.0)], 'pf': 0.95, 'correct_phase_order': (0, 1, 2), 'correct_polarity': (1, 1, 1)},
    {'phasors': [(1.0, 0.0), (1.0, 240.0), (1.0, 120.0)], 'pf': 0.90, 'correct_phase_order': (0, 1, 2), 'correct_polarity': (1, 1, 1)},
    {'phasors': [(1.0, 0.0), (1.0, 240.0), (1.0, 120.0)], 'pf': 0.866, 'correct_phase_order': (0, 1, 2), 'correct_polarity': (1, 1, 1)},
    {'phasors': [(1.0, 0.0), (1.0, 240.0), (1.0, 120.0)], 'pf': 0.80, 'correct_phase_order': (0, 1, 2), 'correct_polarity': (1, 1, 1)},
    {'phasors': [(1.0, 0.0), (1.0, 240.0), (1.0, 120.0)], 'pf': 0.75, 'correct_phase_order': (0, 1, 2), 'correct_polarity': (1, 1, 1)},
    {'phasors': [(1.0, 0.0), (1.0, 240.0), (1.0, 120.0)], 'pf': 0.70, 'correct_phase_order': (0, 1, 2), 'correct_polarity': (1, 1, 1)},
    {'phasors': [(0.9, 25.0), (0.8, 236.0), (0.7, 110.0)], 'pf': 0.95, 'correct_phase_order': (0, 1, 2), 'correct_polarity': (1, 1, 1)},
    {'phasors': [(1.0, 180.0), (1.0, 60.0), (1.0, 300.0)], 'pf': 1.0, 'correct_phase_order': (0, 1, 2), 'correct_polarity': (-1, -1, -1)},
    {'phasors': [(1.0, 180.0), (1.0, 60.0), (1.0, 300.0)], 'pf': 0.86, 'correct_phase_order': (0, 1, 2), 'correct_polarity': (-1, -1, -1)},
]

phase_orders = [(0,1,2), (0,2,1), (1,0,2), (1,2,0), (2,0,1), (2,1,0)]
polarities = [(1,1,1), (-1,1,1), (1,-1,1), (1,1,-1), (-1,-1,1), (-1,1,-1), (1,-1,-1), (-1,-1,-1)]

for i, test in enumerate(tests):
    print '\n\ntest', str(i) +':'
    test['best_neg_seq'] = 999999.9
    test['best_pf'] = [0.0, 0.0, 0.0]
    test['best_phase_order'] = None
    test['best_polarity'] = None

    for phase_order in phase_orders:
        for polarity in polarities:
            if phase_order == (2, 0, 1) and polarity == (-1, -1, -1):
                continue
            pf_angle = np.degrees(np.arccos(test['pf']))
            polarity_offsets = []
            for p in polarity:
                if p == 1:
                    polarity_offsets.append(0.0)
                else:
                    polarity_offsets.append(180.0)

            a = (test['phasors'][phase_order[0]][0], add_angle(add_angle(test['phasors'][phase_order[0]][1], pf_angle), polarity_offsets[0]))
            b = (test['phasors'][phase_order[1]][0], add_angle(add_angle(test['phasors'][phase_order[1]][1], pf_angle), polarity_offsets[1]))
            c = (test['phasors'][phase_order[2]][0], add_angle(add_angle(test['phasors'][phase_order[2]][1], pf_angle), polarity_offsets[2]))

            pf_rel = [np.cos(np.radians(a[1])), np.cos(np.radians(sub_angle(b[1], 240.0))), np.cos(np.radians(sub_angle(c[1], 120.0)))]

            if all(pf > 0.0 for pf in pf_rel):
                if neg_seq_mag(a, b, c) <= test['best_neg_seq'] or approx_equal(neg_seq_mag(a, b, c), test['best_neg_seq'], 0.1):
                    if pf_rel[0] > test['best_pf'][0] and pf_rel[1] > test['best_pf'][1] and pf_rel[2] > test['best_pf'][2]:
                        # print 'setting new best'
                        test['best_neg_seq'] = neg_seq_mag(a, b, c)
                        test['best_phase_order'] = phase_order
                        test['best_polarity'] = polarity
                        test['best_pf'] = pf_rel

            # print 'phase_order       ', phase_order
            # print 'polarity          ', polarity
            # print 'phasors           ', a, b, c
            # print 'pos seq           ', '{:.2f}'.format(pos_seq_mag(a, b, c))
            # print 'neg seq           ', '{:.2f}'.format(neg_seq_mag(a, b, c))
            # print 'neg seq (same mag)', '{:.2f}'.format(neg_seq_mag_same_mags(a, b, c))
            # # print 'pf                ', '{:.2f}'.format(np.cos(a[1])), '{:.2f}'.format(np.cos(b[1])), '{:.2f}'.format(np.cos(c[1]))
            # print 'pf (relative)     ', '{:.2f}'.format(pf_rel[0]), '{:.2f}'.format(pf_rel[1]), '{:.2f}'.format(pf_rel[2])
            # print 'real power'        , 
            # print ''

    print '  best phase order', test['best_phase_order']
    print '  best polarity   ', test['best_polarity']

    if test['best_phase_order'] == test['correct_phase_order'] and test['best_polarity'] == test['correct_polarity']:
        print '  correct detection'