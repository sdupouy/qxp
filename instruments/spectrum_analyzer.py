from abc import ABC, abstractmethod
import pyvisa as visa

TIMEOUT = 100_000


class VisaSpectrumAnalyzer:
    def __init__(self, address):
        self.sa = self.connect(address=address)

    # def __del__(self):
    #     self.sa.clear()
    #     self.sa.close()

    def connect(self, address: str):
        rm = visa.ResourceManager()
        sa = rm.open_resource(address)
        sa.timeout = TIMEOUT
        return sa

    @abstractmethod
    def get_amp(self):
        pass

    @abstractmethod
    def set_automatic_video_bandwidth(self, state: int):
        # State should be 1 or 0
        pass

    @abstractmethod
    def set_automatic_bandwidth(self, state: int):
        # State should be 1 or 0
        pass

    @abstractmethod
    def set_bandwidth(self, bw: int):
        # Sets the bandwidth
        pass

    @abstractmethod
    def set_sweep_points(self, n_points: int):
        # Sets the number of points for a sweep
        pass

    @abstractmethod
    def set_center_freq(self, freq: int):
        # Sets the central frequency
        pass

    @abstractmethod
    def set_span(self, span: int):
        # Sets the span
        pass

    @abstractmethod
    def set_continuous_mode_off(self):
        # Sets continuous mode off
        pass

    @abstractmethod
    def set_continuous_mode_on(self):
        # Sets continuous mode on
        pass

    @abstractmethod
    def get_single_trigger(self):
        # Performs a single sweep
        pass

    @abstractmethod
    def active_marker(self, marker: int):
        # Active the given marker
        pass

    @abstractmethod
    def set_marker_freq(self, marker: int, freq: int):
        # Sets the marker's frequency
        pass

    @abstractmethod
    def query_marker(self, marker: int):
        # Query the marker
        pass

    @abstractmethod
    def get_full_trace(self):
        # Returns the full trace
        pass

    @abstractmethod
    def enable_measurement(self):
        # Sets the measurement to channel power
        pass

    @abstractmethod
    def disables_measurement(self):
        # Sets the measurement to none
        pass

    @abstractmethod
    def sets_measurement_integration_bw(self, ibw: int):
        # Sets the measurement integration bandwidth
        pass

    @abstractmethod
    def disables_measurement_averaging(self):
        # Disables averaging in the measurement
        pass

    @abstractmethod
    def get_measurement_data(self):
        # Returns the result of the measurement
        pass


class RohdeSchwarzFSV(VisaSpectrumAnalyzer):

    def __init__(self, address):
        super().__init__(address)

    def get_amp(self):

        self.get_single_trigger()

        if self.method == 1:  # Channel power
            sig = self.get_measurement_data()

        elif self.method == 2:  # Marker
            sig = self.query_marker(1)
        else:
            sig = float("NaN")
        return sig

    def set_automatic_video_bandwidth(self, state: int):
        # State should be 1 or 0
        self.sa.write(f"SENS:BAND:VID:AUTO {int(state)}")

    def set_video_bandwidth(self, bandwidth: int):
        # Sets the video bandwidth, default unit is
        self.sa.write(f"SENS:BAND:VID:AUTO OFF")
        self.sa.write(f"SENS:BAND:VID {int(bandwidth)}")

    def set_automatic_bandwidth(self, state: int):
        # State should be 1 or 0. Resolution (or measurement) bandwidth
        self.sa.write(f"SENS:BAND:AUTO {int(state)}")

    def set_bandwidth(self, bw: int):
        # Sets the resolution (or measurement) bandwidth, 1 Hz to 3 MHz, default unit is Hz
        # Example SENS:BAND 100000
        self.sa.write(f"SENS:BAND {int(bw)}")

    def set_sweep_points(self, n_points: int):
        # Sets the number of points for a sweep, allowed range 101 to 2501, default is 201
        self.sa.write(f"SENS:SWE:POIN {int(n_points)}")

    def set_center_freq(self, freq: int):
        # Sets the central frequency, default unit is Hz
        self.sa.write(f"SENS:FREQ:CENT {int(freq)}")

    def set_span(self, span: int):
        # Sets the span, default unit is Hz
        self.sa.write(f"SENS:FREQ:SPAN {int(span)}")

    def set_cont_off(self):
        # This command selects the sweep mode (but does not start the measurement!)
        # OFF or 0 is a single sweep mode
        # *OPC? is to make sure there is no overlapping execution
        return self.sa.query("INIT:CONT OFF;*OPC?")

    def set_cont_on(self):
        # This command selects the sweep mode (but does not start the measurement!)
        # ON or 1 is a continuous sweep mode
        # *OPC? is to make sure there is no overlapping execution
        return self.sa.query("INIT:CONT ON;*OPC?")

    def get_single_trigger(self):
        # Initiates a new measurement sequence (starts the sweep)
        return self.sa.query("INIT:IMM;*OPC?")

    def active_marker(self, marker: int):
        # Activate the given marker
        self.sa.write(f"CALC:MARK{int(marker)} ON")

    def set_marker_freq(self, marker: int, freq: int):
        # Sets the marker's frequency. Default unit is Hz
        self.get_single_trigger()
        self.sa.write(f"CALC:MARK{int(marker)}:X {int(freq)}")

    def query_marker(self, marker: int):
        # Query the amplitude (default unit is dBm) of the marker
        return float(self.sa.query(f"CALC:MARK{int(marker)}:Y?"))

    def get_full_trace(self):
        # Returns the full trace. Implicit assumption that this is trace1 (there could be 1-4)
        self.sa.write("FORM ASC")  # data format needs to be in ASCII
        ff_SA_Trace_Data = self.sa.query("TRAC:DATA? TRACE1")
        # Data from the FPC comes out as a string of 1183 values separated by ',':
        # '-1.97854112E+01,-3.97854112E+01,-2.97454112E+01,-4.92543112E+01,-5.17254112E+01,-1.91254112E+01...\n'
        # The code below turns it into an a python list of floats
        # Use split to turn long string to an array of values
        ff_SA_Trace_Data_Array = ff_SA_Trace_Data.split(",")
        amp = [float(i) for i in ff_SA_Trace_Data_Array]
        return amp

    def enable_measurement(self):
        # Sets the measurement to channel power
        self.sa.write(
            "CALC:MARK:FUNC:BPOW:STAT ON;CALC:MARK:FUNC:REF"
            # DISP:TRAC:Y:SPAC LOG;
        )

    def disables_measurement(self):
        # Sets the channel power measurement to none
        self.sa.write("CALC:MARK:FUNC:BPOW:STAT OFF")

    def sets_measurement_integration_bw(self, ibw: int):
        # Sets the measurement integration bandwidth for channel power measurements in Hz
        self.sa.write(f"CALC:MARK:FUNC:BPOW:SPAN {int(ibw)}")

    def disables_measurement_averaging(self):
        # disables averaging in the measurement
        pass

    def get_measurement_data(self):
        # Returns the result of the measurement
        # self.get_single_trigger()
        res = float(self.sa.query(f"CALC:MARK:FUNC:BPOW:RES?")[:-1])
        return res
