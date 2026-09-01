#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ==============================================================================
# FM SCA Subcarrier Decoder (67 kHz / 92 kHz) with GUI -- Version 1.0
# Copyright (C) 2026 Francis M. Columbus
#
# System Architecture, DSP Filter Tuning, GNU Radio 3.10 Binding Integration,
# and DevTest: Francis M. Columbus
# Code structure developed with AI generation assistance.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# ==============================================================================

import sys
import math
import argparse
from gnuradio import gr, filter, analog, audio, fft, qtgui
from gnuradio.filter import firdes
from PyQt5 import Qt
import sip
import osmosdr

class FmScaReceiver(gr.top_block, Qt.QWidget):
    def __init__(self, station_freq=88.5e6, sca_subcarrier=67000.0, gain=40.0):
        gr.top_block.__init__(self, "FM SCA Subcarrier Monitor")
        Qt.QWidget.__init__(self)

        # Basic Layout Setup
        self.layout = Qt.QVBoxLayout()
        self.setLayout(self.layout)

        # --- Sample Rates & Parameters ---
        self.rf_rate = 2400000      # 2.4 MSps from SDR
        self.audio_rate = 48000     # Standard audio rate
        self.quad_rate = 240000     # Intermediate rate after wideband FM RX
        
        self.station_freq = station_freq
        self.sca_subcarrier = sca_subcarrier

        # ----------------------------------------------------------------------
        # 1. Hardware Source (RTL-SDR)
        # ----------------------------------------------------------------------
        self.src = osmosdr.source(args="rtl=0")
        self.src.set_sample_rate(self.rf_rate)
        self.src.set_center_freq(self.station_freq, 0)
        self.src.set_gain_mode(False, 0)
        self.src.set_gain(gain, 0)

        # ----------------------------------------------------------------------
        # 2. Wideband FM Demodulator
        # ----------------------------------------------------------------------
        chan_taps = firdes.low_pass(
            1.0,                    # Gain
            self.rf_rate,           # Input sample rate
            100000,                 # Cutoff frequency
            20000,                  # Transition width
            fft.window.WIN_HAMMING  # GNU Radio 3.10 Window Syntax
        )

        self.rf_filter = filter.freq_xlating_fir_filter_ccc(
            10,                     # Decimation (2.4 MHz -> 240 kHz)
            chan_taps,
            0.0,
            self.rf_rate
        )

        # Quadrature Demodulator for Wideband FM
        fm_demod_gain = self.quad_rate / (2 * math.pi * 75000)
        self.wb_fm_demod = analog.quadrature_demod_cf(fm_demod_gain)

        # ----------------------------------------------------------------------
        # 3. Qt GUI Baseband Spectrum Plotter (Focused on 45 kHz - 105 kHz)
        # ----------------------------------------------------------------------
        # Center display at 75 kHz with 60 kHz bandwidth
        self.qtgui_sink = qtgui.freq_sink_f(
            2048,                           # High resolution FFT
            fft.window.WIN_BLACKMAN_HARRIS,
            75000,                          # Display center frequency offset
            60000,                          # Display bandwidth
            "SCA Subcarrier Spectrum (67 kHz / 92 kHz)",
            1
        )
        self.qtgui_sink.set_update_time(0.05)
        self.qtgui_sink.enable_autoscale(False)
        self.qtgui_sink.set_y_axis(-90, -30)
        
        # Embed Qt GUI widget into window
        self.pyqtwidget = sip.wrapinstance(self.qtgui_sink.qwidget(), Qt.QWidget)
        self.layout.addWidget(self.pyqtwidget)

        # ----------------------------------------------------------------------
        # 4. SCA Subcarrier Extraction
        # ----------------------------------------------------------------------
        sca_taps = firdes.low_pass(
            1.0,
            self.quad_rate,
            5000,                   # 5 kHz cutoff for subcarrier
            1500,                   # Transition width
            fft.window.WIN_HAMMING
        )

        self.sca_xlating_filter = filter.freq_xlating_fir_filter_fcc(
            1,                      # Decimation
            sca_taps,               # Taps
            self.sca_subcarrier,    # Center frequency (67 kHz / 92 kHz)
            self.quad_rate          # Sample rate
        )

        # ----------------------------------------------------------------------
        # 5. Narrowband FM Demodulation & Audio Output
        # ----------------------------------------------------------------------
        nbfm_demod_gain = self.quad_rate / (2 * math.pi * 5000)
        self.nb_fm_demod = analog.quadrature_demod_cf(nbfm_demod_gain)

        audio_taps = firdes.low_pass(
            1.0,
            self.quad_rate,
            5000,                   # Audio cutoff (5 kHz)
            1000,
            fft.window.WIN_HAMMING
        )
        self.audio_decimator = filter.fir_filter_fff(5, audio_taps)

        # 75 µs De-emphasis Filter via IIR
        tau = 75e-6
        w_c = 1.0 / tau
        alpha = 1.0 / (1.0 + (2.0 * self.audio_rate / w_c))
        b0 = alpha
        b1 = alpha
        a1 = (1.0 - (2.0 * self.audio_rate / w_c)) / (1.0 + (2.0 * self.audio_rate / w_c))
        self.deemph = filter.iir_filter_ffd([b0, b1], [1.0, a1])

        # Audio Sink
        self.audio_sink = audio.sink(self.audio_rate, "", True)

        # Connections
        self.connect(self.src, self.rf_filter)
        self.connect(self.rf_filter, self.wb_fm_demod)
        
        # Connect Wideband FM output to BOTH Qt Plotter and SCA Filter
        self.connect(self.wb_fm_demod, self.qtgui_sink)
        self.connect(self.wb_fm_demod, self.sca_xlating_filter)

        # Continue DSP path to Audio Sink
        self.connect(self.sca_xlating_filter, self.nb_fm_demod)
        self.connect(self.nb_fm_demod, self.audio_decimator)
        self.connect(self.audio_decimator, self.deemph)
        self.connect(self.deemph, (self.audio_sink, 0))


def main():
    parser = argparse.ArgumentParser(
        description="GNU Radio FM SCA Receiver with Focused Subcarrier Display"
    )
    parser.add_argument("-f", "--freq", type=float, default=88.5, help="Station frequency in MHz (default: 88.5)")
    parser.add_argument("-s", "--sca", type=float, default=67.0, help="SCA subcarrier frequency in kHz (default: 67.0)")
    parser.add_argument("-g", "--gain", type=float, default=40.0, help="RTL-SDR RF gain in dB (default: 40.0)")

    args = parser.parse_args()

    station_freq = args.freq * 1e6
    sca_subcarrier = args.sca * 1e3

    # Initialize Qt Application Loop
    qapp = Qt.QApplication(sys.argv)

    tb = FmScaReceiver(
        station_freq=station_freq, 
        sca_subcarrier=sca_subcarrier, 
        gain=args.gain
    )

    tb.show()
    tb.start()

    print(f"\n--- SCA Subcarrier Monitor Running ---")
    print(f"Station Frequency:  {args.freq:.1f} MHz")
    print(f"SCA Subcarrier:     {args.sca:.1f} kHz")
    print(f"RF Gain:            {args.gain} dB")
    print("--------------------------------------")
    print("Displaying region: 45 kHz to 105 kHz")
    print("Close GUI window to exit.\n")

    qapp.exec_()

    tb.stop()
    tb.wait()

if __name__ == "__main__":
    main()
