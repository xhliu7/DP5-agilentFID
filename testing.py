#!/usr/bin/env python3
import matplotlib.pyplot as plt
import nmrglue as ng
import numpy as np

def main(file, fidtype):
    if fidtype == 'vfid':  # varian/agilent fid
        dic, total_spectral_ydata = ng.varian.read(file)  # read file

        total_spectral_ydata = ng.proc_base.zf_double(total_spectral_ydata, 4)  # zero filling

        total_spectral_ydata = ng.proc_base.fft(total_spectral_ydata)  # FFT

        # normalization
        m = max(np.max(abs(np.real(total_spectral_ydata))), np.max(abs(np.imag(total_spectral_ydata))))

        total_spectral_ydata = np.real(total_spectral_ydata / m) + 1j * np.imag(total_spectral_ydata / m)

        # getting universal dictionary values

        udic = ng.varian.guess_udic(dic, total_spectral_ydata)

        udic[0]['size'] = len(total_spectral_ydata)  # should be the size of final data rather than np

        udic[0]['sw'] = float(dic['procpar']['sw']['values'][0])

        udic[0]['complex'] = 'True'

        udic[0]['obs'] = float(dic['procpar']['sfrq']['values'][0])

        delta = (udic[0]['obs'] - float(dic['procpar']['H1reffrq']['values'][0])) * 1e6

        udic[0]['car'] = delta  # carrier frequency is the delta between (carrier-TMS/DSS) in Hz

        udic[0]['label'] = dic['procpar']['tn']['values'][0]

        uc = ng.fileiobase.uc_from_udic(udic)  # unit conversion element

        spectral_xdata_ppm = uc.ppm_scale()  # ppmscale creation

        # baseline and phase correction
        p0 = float(dic['procpar']['rp']['values'][0])
        p1 = float(dic['procpar']['lp']['values'][0])
        tydata = ng.proc_autophase.ps(total_spectral_ydata, p0=p0, p1=p1, inv=True)
        tydata = ng.proc_base.di(tydata)

    elif fidtype == 'fid':  # bruker fid
        dic, total_spectral_ydata = ng.bruker.read(file)  # read file

        total_spectral_ydata = ng.bruker.remove_digital_filter(dic, total_spectral_ydata)  # remove the digital filter

        total_spectral_ydata = ng.proc_base.zf_double(total_spectral_ydata, 4)  # zero filling

        total_spectral_ydata = ng.proc_base.fft_positive(total_spectral_ydata)  # FFT

        # normalization
        m = max(np.max(abs(np.real(total_spectral_ydata))), np.max(abs(np.imag(total_spectral_ydata))))

        total_spectral_ydata = np.real(total_spectral_ydata / m) + 1j * np.imag(total_spectral_ydata / m)

        # getting universal dictionary values

        udic = ng.bruker.guess_udic(dic, total_spectral_ydata)  # sorting units

        uc = ng.fileiobase.uc_from_udic(udic)  # unit conversion element

        spectral_xdata_ppm = uc.ppm_scale()  # ppmscale creation

        # baseline and phase correction
        tydata = ng.proc_autophase.autops(total_spectral_ydata,'acme')  # best method acme 20230307

        # tydata = ng.proc_base.di(tydata)

    else:
        print('Not recognized data type. Quitting!')
        exit()

    # plot spectrum

    fig = plt.figure()

    # plt.xlim([16,-2])

    ax = fig.add_subplot(111)
    ax.invert_xaxis()
    ax.plot(spectral_xdata_ppm, tydata, 'k-')

    plt.show()


if __name__ == '__main__':
    file = input("please input you proton spectra name (*.fid): ")
    fidtype = input('please input fid type(\'vfid\' for varian and \'fid\' for bruker): ') or 'vfid'
    main(file, fidtype)