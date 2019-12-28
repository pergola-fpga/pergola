import os
import subprocess

from nmigen.build import *
from nmigen.vendor.lattice_ecp5 import *
from nmigen_boards.resources import *


class PergolaPlatform(LatticeECP5Platform):
    device      = "LFE5U-12F"
    package     = "BG256"
    speed       = 8

    default_clk = "clk16"
    resources   = [
        Resource("clk16", 0, Pins("P11", dir="i"),
                 Clock(16e6), Attrs(GLOBAL=True, IO_STANDARD="LVCMOS33")),

        *LEDResources(pins="F15 E16 E15 D16 C16 C15 B16 B15", invert=False, attrs=Attrs(IO_STANDARD="LVCMOS33")),

        *ButtonResources(pins="F14", invert=True, attrs=Attrs(IO_STANDARD="LVCMOS33")),

        UARTResource(0,
            rx="T2", tx="R1",
            attrs=Attrs(IO_STANDARD="LVCMOS33", PULLUP=1)
        ),

        # PSRAM #1
        *SPIFlashResources(0,
            cs="A9", clk="B9", mosi="B10", miso="A10", wp="A11", hold="B8",
            attrs=Attrs(IO_STANDARD="LVCMOS33")
        ),

        # PSRAM #2
        *SPIFlashResources(1,
            cs="A2", clk="A4", mosi="A5", miso="B3", wp="B4", hold="A3",
            attrs=Attrs(IO_STANDARD="LVCMOS33")
        ),
    ]
    connectors = [
        Connector("pmod", 0, "P2  L1  J2  H2  - - N1  L2  J1  G1  - -"), # PMOD1
        Connector("pmod", 1, "G2  E2  C1  B1  - - F1  D1  C2  B2  - -"), # PMOD2
        Connector("pmod", 2, "D4  C6  B7  C7  - - C4  B6  A7  A8  - -"), # PMOD3
        Connector("pmod", 3, "B11 B12 B13 B14 - - A12 A13 A14 A15 - -"), # PMOD4
        Connector("pmod", 4, "F16 G16 J16 L16 - - G15 H15 J15 L15 - -"), # PMOD5
    ]

    @property
    def file_templates(self):
        idcodes = {
            "LFE5U-12F": "0x21111043",
            "LFE5U-25F": "0x41111043",
            "LFE5U-45F": "0x41112043",
            "LFE5U-85F": "0x41113043",
        }
        return {
            **super().file_templates,
            "{{name}}-openocd.cfg": """
            jtag newtap ecp5 tap -irlen 8 -expected-id {} ;
            """.format(idcodes[self.device])
        }

    def toolchain_program(self, products, name):
        openocd = os.environ.get("OPENOCD", "openocd")
        interface = os.environ.get("INTERFACE", "/dev/ttyACM0")
        if interface == "SiPEED" or interface == "busblaster":
          if interface == "SiPEED":
              args = ["-c", """
                      interface ftdi
                      ftdi_vid_pid 0x0403 0x6010
                      ftdi_layout_init 0x0018 0x05fb
                      ftdi_layout_signal nSRST -data 0x0010
                  """]
          elif interface == "busblaster":
              args = ["-f", "interface/ftdi/dp_busblaster.cfg"]

          with products.extract("{}-openocd.cfg".format(name), "{}.svf".format(name)) \
                  as (config_filename, vector_filename):
              subprocess.check_call([openocd,
                  *args,
                  "-f", config_filename,
                  "-c", "transport select jtag; adapter_khz 10000; init; svf -quiet {}; exit".format(vector_filename)
              ])
        else:
          with products.extract("{}.bit".format(name)) as (bitstream):
            print(subprocess.check_call(["bash", "-c", """
              stty -F {} 300 raw -clocal -echo icrnl &&
              sleep 0.01 &&
              echo -n "$(stat -c%s {})\n" > {} &&
              cp {} {}
            """.format(interface, bitstream, interface, bitstream, interface)]))

    def build(self, *args, **kwargs):
        if self.device == "LFE5U-12F":
            ecppack_opts = "--idcode 0x21111043"
        else:
            ecppack_opts = None
        LatticeECP5Platform.build(self, *args, ecppack_opts=ecppack_opts, **kwargs)

if __name__ == "__main__":
    from nmigen_boards.test.blinky import *
    p = PergolaPlatform()
    p.build(Blinky(), do_program=True)
