#!/usr/bin/env python

# -*- coding: utf-8 -*-
"""
Created on Wed Apr 19 15:56:54 2019

@author: ke291

Contains all of the specific code for running Gaussian jobs on Ziggy.
A lot of code is reused from Gaussian.py. Called by PyDP4.py.
"""

import subprocess
import socket
import os
import time
import math

import Gaussian

SetupNMRCalcs = Gaussian.SetupNMRCalcs

SetupECalcs = Gaussian.SetupECalcs

SetupOptCalcs = Gaussian.SetupOptCalcs

ReadShieldings = Gaussian.ReadShieldings

ReadEnergies = Gaussian.ReadEnergies

ReadGeometries = Gaussian.ReadGeometries

IsGausCompleted = Gaussian.IsGausCompleted

Converged = Gaussian.Converged

def RunNMRCalcs(Isomers, settings):
    print('\nRunning Gaussian NMR calculations on Ziggy...')

    # Run Gaussian jobs on Ziggy cluster in folder named after date and time
    # Split in batches, if needed

    jobdir = os.getcwd()
    os.chdir('nmr')

    GausJobs = []

    for iso in Isomers:
        GausJobs.extend([x for x in iso.NMRInputFiles if (x[:-4] + '.out') not in iso.NMROutputFiles])

    Completed = RunCalcs(GausJobs, settings)

    for iso in Isomers:
        iso.NMROutputFiles.extend([x[:-4] + '.out' for x in iso.NMRInputFiles if (x[:-4] + '.out') in Completed])

    os.chdir(jobdir)

    return Isomers


def RunECalcs(Isomers, settings):
    print('\nRunning Gaussian DFT energy calculations on Ziggy...')

    jobdir = os.getcwd()
    os.chdir('e')

    GausJobs = []

    for iso in Isomers:
        GausJobs.extend([x for x in iso.EInputFiles if (x[:-4] + '.out') not in iso.EOutputFiles])

    Completed = RunCalcs(GausJobs, settings)

    for iso in Isomers:
        iso.EOutputFiles.extend([x[:-4] + '.out' for x in iso.EInputFiles if (x[:-4] + '.out') in Completed])

    os.chdir(jobdir)

    return Isomers


def RunOptCalcs(Isomers, settings):
    print('\nRunning Gaussian DFT geometry optimizations on Ziggy...')

    jobdir = os.getcwd()
    os.chdir('opt')

    GausJobs = []

    for iso in Isomers:
        GausJobs.extend([x for x in iso.OptInputFiles if (x[:-4] + '.out') not in iso.OptOutputFiles])

    Completed = RunCalcs(GausJobs, settings)

    for iso in Isomers:
        iso.OptOutputFiles.extend([x[:-4] + '.out' for x in iso.OptInputFiles if (x[:-4] + '.out') in Completed])

    os.chdir(jobdir)

    return Isomers


def RunCalcs(GausJobs, settings):

    MaxCon = settings.MaxConcurrentJobsZiggy

    if len(GausJobs) < MaxCon:
        if len(GausJobs) > 0:
            RunBatchOnZiggy(0, settings.queue, GausJobs, settings)
    else:
        if len(GausJobs) > 0:
            print("The DFT calculations will be done in " + \
                  str(math.ceil(len(GausJobs) / MaxCon)) + " batches")
            i = 0
            while (i + 1) * MaxCon < len(GausJobs):
                print("Starting batch nr " + str(i + 1))
                RunBatchOnZiggy(str(i + 1), settings.queue, GausJobs[(i * MaxCon):((i + 1) * MaxCon)], settings)
                i += 1
            print("Starting batch nr " + str(i + 1))
            RunBatchOnZiggy(str(i + 1), settings.queue, GausJobs[(i * MaxCon):], settings)

    NCompleted = 0
    Completed = []

    for f in GausJobs:
        if IsGausCompleted(f[:-4] + '.out'):
            Completed.append(f[:-4] + '.out')
            NCompleted += 1

    if NCompleted > 0:
        print(str(NCompleted) + " Gaussian jobs of " + str(len(GausJobs)) + \
            " completed successfully.")
    elif len(GausJobs) == 0:
        print("There were no jobs to run.")

    return Completed


def RunBatchOnZiggy(findex, queue, GausFiles, settings):

    # Run Gaussian jobs on Ziggy cluster in folder named after date and time
    # Split in batches, if needed

    if findex == 0:  # findex是什么？20240903
        folder = settings.StartTime + settings.Title
    else:
        folder = settings.StartTime + findex + settings.Title

    print("Setting up jobs for running on ziggy...\n")

    #Check that folder does not exist, create job folder on ziggy
    outp = subprocess.check_output('ssh -p 553 xhliu73@ziggy ls', shell=True)  #LXH 20240904 to use cluster
    if folder in outp.decode():
        print("Folder exists on ziggy, choose another folder name.")
        return

    outp = subprocess.check_output('ssh -p 553 xhliu73@ziggy mkdir ' + folder, shell=True) #LXH 20240904 to use cluster

    print("Results folder: " + folder)

    #Write the qsub scripts
    for f in GausFiles:
        WriteSubScript(f, queue, folder, settings)
    print(str(len(GausFiles)) + ' slurm scripts generated')

    #Upload .com files and .qsub files to directory
    print("Uploading files to ziggy...")
    for f in GausFiles:
        outp = subprocess.check_output('scp -P 553 ' + f +' xhliu73@ziggy:~/' + folder,
                                           shell=True)  # LXH 20240904
        outp = subprocess.check_output('scp -P 553 ' + f[:-4] +'slurm xhliu73@ziggy:~/' +
                                       folder, shell=True)  # LXH 20240904

    print(str(len(GausFiles)) + ' .com and slurm files uploaded to ziggy')

    JobIDs = []
    #Launch the calculations
    for f in GausFiles:
        job = '/home/' + settings.user + "/" + folder + '/' + f[:-4]
        outp = subprocess.check_output('ssh -p 553 xhliu73@ziggy sbatch ' + job + 'slurm', shell=True)  # LXH 20240904
        status = outp.decode()[:-1]
        print(status)
        JobIDs.append(status.split('job ')[1])

    print(str(len(GausFiles)) + ' jobs submitted to the queue on ziggy')

    outp = subprocess.check_output('ssh -p 553 xhliu73@ziggy qstat', shell=True)  # LXH 20240904
    if settings.user in outp.decode():
        print("Jobs are running on ziggy")

    time.sleep(5)
    OldQRes = CheckZiggyQueue(JobIDs, settings)
    print('Pending: ' + str(OldQRes[0]) + ', Running: ' + str(OldQRes[1]) + ', Not in queue: ' + str(OldQRes[2]))

    Jobs2Complete = list(GausFiles)
    n2complete = len(Jobs2Complete)

    #Check and report on the progress of calculations
    while len(Jobs2Complete) > 0:
        JustCompleted = [job for job in Jobs2Complete if
            IsZiggyGComplete(job[:-3] + 'out', folder, settings)]
        Jobs2Complete[:] = [job for job in Jobs2Complete if
             not IsZiggyGComplete(job[:-3] + 'out', folder, settings)]
        if n2complete != len(Jobs2Complete):
            n2complete = len(Jobs2Complete)
            print(str(n2complete) + " remaining.")

        QRes = CheckZiggyQueue(JobIDs, settings)
        if QRes != OldQRes:
            OldQRes = QRes
            print('Pending: ' + str(OldQRes[0]) + ', Running: ' + str(OldQRes[1]) + ', Not in queue: ' + str(OldQRes[2]))

        if QRes[2] == len(JobIDs):
            #check each gaussian file to ascertain the status of individual gaus jobs
            print('No jobs left in Ziggy queue')
            break

        time.sleep(10)

    #When done, copy the results back
    print("\nCopying the output files back to localhost...")
    print('ssh -p 553 xhliu73@ziggy scp /home/' + settings.user + '/' + folder + '/*.out ' +\
        socket.getfqdn() + ':' + os.getcwd())
    outp = subprocess.check_output('scp -P 553 xhliu73@ziggy:/home/' + settings.user +
                                   '/' + folder + '/*.out ' + os.getcwd(), shell=True)  # LXH 20240904


def WriteSubScript(GausJob, queue, ZiggyJobFolder, settings):

    if not (os.path.exists(GausJob)):
        print("The input file " + GausJob + " does not exist. Exiting...")
        return

    #Create the submission script
    QSub = open(GausJob[:-4] + "slurm", 'w')

    #Choose the queue
    QSub.write('#!/bin/bash\n\n')
    QSub.write('#SBATCH -p ' + settings.queue + '\n')
    if settings.nProc >1:
        QSub.write('#SBATCH --nodes=1\n#SBATCH --cpus-per-task=' + str(settings.nProc) + '\n')
    else:
        QSub.write('#SBATCH --nodes=1\n#SBATCH --cpus-per-task=1\n')
    QSub.write('#SBATCH --time=' + format(settings.TimeLimit,"02") +':00:00\n\n')

    #define input files and output files
    QSub.write('file=' + GausJob[:-4] + '\n\n')
    QSub.write('inpfile=${file}.com\noutfile=${file}.out\n')

    #define cwd and scratch folder and ask the machine
    #to make it before running the job
    QSub.write('HERE=/home/' + settings.user +'/' + ZiggyJobFolder + '\n')
    QSub.write('SCRATCH=/data1/liuxuehui/scratch/' + settings.user + '/' +
               GausJob[:-4] + '\n')  # LXH 20240904
    QSub.write('mkdir ${SCRATCH}\n')

    #Setup GAUSSIAN environment variables
    QSub.write('set OMP_NUM_THREADS=32\n')  # LXH 20240904
    
    QSub.write('export GAUSS_EXEDIR=/data1/liuxuehui/apps/g16\n')  # LXH 20240904
    QSub.write('export g09root=/data1/liuxuehui/apps/g16\n')  # LXH 20240904
    QSub.write('export PATH=/data1/liuxuehui/apps/g16:$PATH\n')  # LXH 20240904
    QSub.write('export GAUSS_SCRDIR=$SCRATCH\n')
    QSub.write('exe=$GAUSS_EXEDIR/g16\n')  # LXH 20240904
    #copy the input file to scratch
    QSub.write('cp ${HERE}/${inpfile}  $SCRATCH\ncd $SCRATCH\n')

    #write useful info to the job output file (not the gaussian)
    QSub.write('echo "Starting job $SLURM_JOBID"\necho\n')
    QSub.write('echo "SLURM assigned me this node:"\nsrun hostname\necho\n')
    QSub.write('date') # LXH 20240904
    QSub.write('ln -s $HERE/$outfile $SCRATCH/$outfile\n')
    QSub.write('srun $exe < $inpfile > $outfile\n')  # LXH 20240904

    #Cleanup
    QSub.write('rm -rf ${SCRATCH}/\n')
    
    QSub.close()


def IsZiggyGComplete(f, folder, settings):

    path = '/home/' + settings.user + '/' + folder + '/'
    try:
        outp1 = subprocess.check_output('ssh -p 553 xhliu73@ziggy ls ' + path, shell=True)  # LXH 20240904
    except subprocess.CalledProcessError as e:
        print("ssh -p 553 xhliu73@ziggy ls failed: " + str(e.output))  # LXH 20240904
        return False
    if f in outp1.decode():
        try:
            outp2 = subprocess.check_output('ssh -p 553 xhliu73@ziggy cat ' + path + f,
                                            shell=True)  # LXH 20240904
        except subprocess.CalledProcessError as e:
            print("ssh -p 553 xhliu73@ziggy cat failed: " + str(e.output).decode())  # LXH 20240904
            return False
        if ("Normal termination" in outp2[-90:].decode()) or \
                (('termination' in outp2[-270:].decode()) and ('l9999.exe' in outp2[-270:].decode())):
            return True
    return False


def CheckZiggyQueue(JobIDs, settings):

    outp = subprocess.Popen(['ssh','-p 553', 'xhliu73@ziggy', 'qstat', '-u ' + settings.user], \
                            stderr=subprocess.STDOUT, stdout=subprocess.PIPE).communicate()[0]  # LXH 20240904
    outp = outp.decode().split('\n')

    QStart = 0
    for i, line in enumerate(outp):
        if '------' in line:
            QStart = i+1
            break
    QueueReport = outp[QStart:-1]

    JobStats = []

    for job in JobIDs:
        status = ''
        for i, line in enumerate(QueueReport):
            if job in line:
                status = list(filter(None, line.split(' ')))[9]
        JobStats.append(status)

    Pending = JobStats.count('Q')
    Running = JobStats.count('R')
    NotInQueue = JobStats.count('')

    return Pending, Running, NotInQueue
