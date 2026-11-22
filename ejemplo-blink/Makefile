# make        -> sintesis + fitter + assembler (output/blink.sof)
# make prog   -> ademas programa la FPGA
S := ../scripts/general

all: output/blink.sof
output/blink.sof: blink.v pines.qsf timing.sdc
	$(S)/build.sh -t blink -p pines.qsf -o output blink.v timing.sdc
prog: output/blink.sof
	$(S)/program.sh output/blink.sof
clean:
	rm -rf output
.PHONY: all prog clean
