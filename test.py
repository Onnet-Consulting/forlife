tes = {
    '1': 2,
    '2': 3
}
check = False
for k, v in tes.items():
    if k in ['1','2']:
        check =True
    else:
        check = False
print(check)