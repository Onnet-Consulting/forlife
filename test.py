vals = {
    131: [{3: 50000.0}],
    311: [{3: 50000.0}],
    312: [{3: 100000.0}],
    313: [{3: 100000.0}]
}


vals = {
    res.partner(131, 311): [{3: 50000.0}],
    res.partner(314, 315): [{4: 100000.0}]
}

for key in vals:
    for k, v in vals[key][0].items():
        for i in range(k):
            print({
                'partner_id': key,
                'price': v
            })

