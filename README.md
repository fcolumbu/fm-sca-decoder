# FM SCA Decoder

An open-source digital signal processing (DSP) tool written in Python for demodulating and decoding **Subsidiary Communications Authorization (SCA)** subcarriers from raw FM broadcast I/Q or baseband (MPX) samples.

SCA subcarriers are analog subcarriers (typically centered at 67 kHz or 92 kHz) modulated onto standard FM radio broadcasts, historically used for specialized services such as reading services for the blind, background music, or data transmissions.

---

## Features

- **Multi-Frequency Support:** Decodes standard 67 kHz and 92 kHz SCA subcarrier frequencies.
- **Flexible Input:** Accepts standard I/Q recording formats (`.wav`, `.raw`, or Software Defined Radio streams) or baseband MPX signals.
- **DSP Pipeline:**
  - Bandpass filtering for subcarrier isolation.
  - Phase-locked loop (PLL) / quadrature FM demodulation.
  - De-emphasis filtering (75 µs / 50 µs configurable) and audio conditioning.
- **Audio Output:** Outputs mono WAV files or streams real-time audio via PortAudio.

---

## Prerequisites & Installation

Ensure you have Python 3.8 or higher installed.

```bash
# Clone the repository
git clone [https://github.com/your-username/fm-sca-decoder.git](https://github.com/your-username/fm-sca-decoder.git)
cd fm-sca-decoder

# Install required dependencies
pip install -r requirements.txt