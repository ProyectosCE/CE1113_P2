# Flujo por defecto (descarga por JTAG):
#   make hw     -> qsys -> qip -> proyecto -> output/hello.sof (RAM sin firmware)
#   make sw     -> BSP + software (crea sw/ y un hola mundo si no existen)
#   make prog   -> programa la FPGA con output/hello.sof
#   make dl     -> resetea el CPU, descarga el ELF por JTAG y lo ejecuta
#   make run    -> abre la consola JTAG UART
# Alternativa (firmware dentro del bitstream, sin depurador):
#   make bake     -> output/hello_fw.sof (scripts/nios/bake.sh; no re-sintetiza)
#   make prog-fw  -> programa hello_fw.sof (el CPU arranca solo; luego make run)
# Variante sin modulo de debug (solo bake): make SYS=hello_nodebug all bake prog-fw
S   := ../scripts
SYS ?= hello
ifeq ($(SYS),hello)
OUT := output
SW  := sw
SRC := src
else
OUT := output-$(SYS)
SW  := sw-$(SYS)
SRC := ../sw/src
endif

all: hw sw
hw: $(OUT)/$(SYS).sof
$(OUT)/$(SYS).sof: $(SYS).qsys pines.qsf timing.sdc
	$(S)/general/build.sh -t $(SYS) -p pines.qsf -q $(SYS).qsys -m zero -o $(OUT) timing.sdc
$(SYS).sopcinfo: $(OUT)/$(SYS).sof
sw: $(SYS).sopcinfo
	$(S)/nios/build-sw.sh $(SYS).sopcinfo $(SW) -s $(SRC)
prog: $(OUT)/$(SYS).sof
	$(S)/general/program.sh $(OUT)/$(SYS).sof
dl: sw
	$(S)/nios/download.sh $(SW)/build/app/build/app.elf
run:
	$(S)/general/terminal.sh
bake: sw
	$(S)/nios/bake.sh $(OUT)/$(SYS).qpf $(SW)/build/app/build/onchip_memory2_0.hex
prog-fw: $(OUT)/$(SYS)_fw.sof
	$(S)/general/program.sh $(OUT)/$(SYS)_fw.sof
clean:
	rm -rf output output-* hello hello_nodebug hello.sopcinfo hello_nodebug.sopcinfo .qsys_edit
	rm -rf sw/bsp sw/build sw-*
.PHONY: all hw sw prog dl run bake prog-fw clean
