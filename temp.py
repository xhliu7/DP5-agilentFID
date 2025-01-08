def main():
    sortedCCalc = [1,2,3,4]
    sortedClabels = ['A','B','C','D']
    tempCCalcs = [4,3,2,1]
    assignedCExp = [''] * len(sortedCCalc)
    print(assignedCExp)
    sortedCExp = [1.5,2.5,3.5,4.5]
    omits = []

    exp_ind = 0

    for shift , label in zip( sortedCCalc , sortedClabels):

        if label not in omits:
            
            ind = tempCCalcs.index(shift)
            print(shift, ind, label)
            assignedCExp[ind] = sortedCExp[exp_ind]
            print(assignedCExp[ind], sortedCExp[exp_ind])
            tempCCalcs[ind] = ''

            exp_ind += 1


if __name__ == '__main__':
    main()