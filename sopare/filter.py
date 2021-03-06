#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright (C) 2015 - 2018 Martin Kauss (yo@bishoph.org)

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at

 http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.
"""

import multiprocessing
import logging
import numpy
import sopare.worker
import sopare.characteristics
from math import ceil, floor

class filtering():

    def __init__(self, cfg):
        self.cfg = cfg
        self.first = True
        self.first_shift = True
        self.queue = multiprocessing.Queue()
        self.characteristic = sopare.characteristics.characteristic(self.cfg.getfloatoption('characteristic', 'PEAK_FACTOR'))
        self.worker = sopare.worker.worker(self.cfg, self.queue)
        self.data_shift = [ ]
        self.last_data = None
        self.data_shift_counter = 0
        self.logger = self.cfg.getlogger().getlog()
        self.logger = logging.getLogger(__name__)

    def stop(self):
        self.queue.put({ 'action': 'stop' })
        self.queue.close()
        self.queue.join_thread()

    def reset(self):
        self.queue.put({ 'action': 'reset' })

    @staticmethod
    def check_for_windowing(meta):
        for m in meta:
            if (m['token'] == 'start analysis' or m['token'] == 'silence'):
                return True
        return False

    def get_chunked_norm(self, nfft):
        chunked_norm = [ ]
        progessive = 1
        i = self.cfg.getintoption('characteristic', 'MIN_PROGRESSIVE_STEP')
        for x in range(0, nfft.size, i):
            if (self.cfg.hasoption('characteristic', 'START_PROGRESSIVE_FACTOR') and x >= self.cfg.getfloatoption('characteristic', 'START_PROGRESSIVE_FACTOR')):
                progessive += progessive * pf
                i += int(progessive)
                if (i > self.cfg.getintoption('characteristic', 'MAX_PROGRESSIVE_STEP')):
                    i = self.cfg.getintoption('characteristic', 'MAX_PROGRESSIVE_STEP')
            chunked_norm.append( nfft[x:x+i].sum() )
        return numpy.array(chunked_norm)

    @staticmethod
    def normalize(fft):
        norm = numpy.linalg.norm(fft)
        if (norm > 0):
            return (fft/norm).tolist()
        return []

    
    def populate_subwindow(self, data):
        length = self.cfg.getfloatoption('cmdlopt', 'length')  # length of subwindow (ratio to chunk length)
        delta = self.cfg.getfloatoption('cmdlopt', 'delta')  # offset from end of regular window (in terms of chunk length)
        prv_chk_mlt = 2 - length - delta  # portion of previous chunk
        cur_chk_mlt = 1 - delta  # portion of current chunk
        chk_len = self.cfg.getintoption('stream', 'CHUNKS')
        if (self.first_shift == True):
            self.data_shift = [ ]
            self.data_shift = [ v for v in range(0, int(ceil(cur_chk_mlt * chk_len))) ]
        else:
            self.data_shift = self.last_data[int(ceil(prv_chk_mlt * chk_len)):]
        
        self.data_shift.extend(data[0:int(ceil(cur_chk_mlt * chk_len))])

        self.last_data = data


    def n_shift(self, data):
        if (self.first == True):
            self.data_shift = [ ]
            self.data_shift_counter = 0
        if (self.data_shift_counter == 0):
            self.data_shift = [ v for v in range(0, self.cfg.getintoption('stream', 'CHUNKS')/2) ]
            self.data_shift.extend(data[len(data)/2:])
        elif (self.data_shift_counter == 1):
            self.data_shift = self.data_shift[len(self.data_shift)/2:]
            self.data_shift.extend(data[0:len(data)/2])
        else:
            self.data_shift = self.last_data[len(self.last_data)/2:]
            self.data_shift.extend(data[0:len(data)/2])

        self.last_data = data
        self.data_shift_counter += 1


    def n_shift_n(self, data):
        windows = self.cfg.getintoption('experimental', 'WINDOW_COUNT')
        if (self.first == True):
            self.data_shift = [ ]
            for _ in range(0, windows):
                self.data_shift.append([])  # one array for each split window
        
            for w in range(0, windows):
                self.data_shift[w] = [ v for v in range(0, (((windows-w)*self.cfg.getintoption('stream', 'CHUNKS'))/(windows+1))) ]
                self.data_shift[w].extend(data[0:(((w+1)*len(data))/(windows+1))])

        else:
            for w in range(0, windows):
                self.data_shift[w] = self.last_data[(((windows-w)*len(self.last_data))/(windows+1)):]
                self.data_shift[w].extend(data[0:(((w+1)*len(data))/(windows+1))])

        self.last_data = data


    def filter(self, data, meta):
        #if self.cfg.getfloatoption('cmdlopt', 'length') != 0.0:
         #   self.populate_subwindow(data)
        shift_fft = None
        if (self.first == False or self.cfg.getbool('characteristic', 'HANNING') == False or len(data) < self.cfg.getintoption('stream', 'CHUNKS')):
            fft = numpy.fft.rfft(data)
            if (len(self.data_shift) >= self.cfg.getintoption('stream', 'CHUNKS')):
                shift_fft = numpy.fft.rfft(self.data_shift)
            self.first = self.check_for_windowing(meta)
        elif (self.first == True):
            self.logger.debug('New window!')
            hl = len(data)
            if (hl % 2 != 0):
                hl += 1
            hw = numpy.hanning(hl)
            fft = numpy.fft.rfft(data * hw)
            if (len(self.data_shift) >= self.cfg.getintoption('stream', 'CHUNKS')):
                hl = len(self.data_shift)
                if (hl % 2 != 0):
                    hl += 1
                hw = numpy.hanning(hl)
                try:
                    shift_fft = numpy.fft.rfft(self.data_shift * hw)
                except ValueError:
                    hl -= 1
                    hw = numpy.hanning(hl)
                    shift_fft = numpy.fft.rfft(self.data_shift * hw)
                #self.first = False
            
        fft[self.cfg.getintoption('characteristic', 'HIGH_FREQ'):] = 0
        fft[:self.cfg.getintoption('characteristic', 'LOW_FREQ')] = 0
        data = numpy.fft.irfft(fft)
        nfft = fft[self.cfg.getintoption('characteristic', 'LOW_FREQ'):self.cfg.getintoption('characteristic', 'HIGH_FREQ')]
        nfft = numpy.abs(nfft)
        nfft[nfft == 0] = numpy.NaN
        nfft = numpy.log10(nfft)**2
        nfft[numpy.isnan(nfft)] = 0
        nam = numpy.amax(nfft)
        normalized = [0]
        if (nam > 0):
            nfft = numpy.tanh(nfft/nam)
            chunked_norm = self.get_chunked_norm(nfft)
            normalized = self.normalize(chunked_norm)
        characteristic = self.characteristic.getcharacteristic(fft, normalized, meta)

        if ((shift_fft is not None) and self.cfg.hasoption('experimental', 'FFT_SHIFT') and self.cfg.getbool('experimental', 'FFT_SHIFT') == True and self.first_shift == False):
            shift_fft[self.cfg.getintoption('characteristic', 'HIGH_FREQ'):] = 0
            shift_fft[:self.cfg.getintoption('characteristic', 'LOW_FREQ')] = 0
            shift_data = numpy.fft.irfft(shift_fft)
            shift_nfft = fft[self.cfg.getintoption('characteristic', 'LOW_FREQ'):self.cfg.getintoption('characteristic', 'HIGH_FREQ')]
            shift_nfft = numpy.abs(nfft)
            shift_nfft[nfft == 0] = numpy.NaN
            shift_nfft = numpy.log10(nfft)**2
            shift_nfft[numpy.isnan(shift_nfft)] = 0
            shift_nam = numpy.amax(shift_nfft)
            shift_normalized = [0]
            if (shift_nam > 0):
                shift_nfft = numpy.tanh(shift_nfft/shift_nam)
                shift_chunked_norm = self.get_chunked_norm(shift_nfft)
                shift_normalized = self.normalize(shift_chunked_norm)
            shift_characteristic = self.characteristic.getcharacteristic(shift_fft, shift_normalized, meta)
            characteristic['shift'] = shift_characteristic

        self.first_shift = False

        obj = { 'action': 'data', 'token': data, 'fft': fft, 'norm': normalized, 'meta': meta, 'characteristic': characteristic }
        self.queue.put(obj)
