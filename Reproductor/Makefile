# Reproductor de audio - DE1-SoC (HPS bare metal + perifericos en la FPGA)
# Fase 1: todo se carga por JTAG.
#
#   make qsys    -> abre reproductor.qsys en Platform Designer
#   make gen     -> solo genera el sistema (qsys-generate); sirve para ver errores del .qsys
#   make hw      -> genera, crea el proyecto, asigna pines DDR3 del HPS y compila
#                   -> output/reproductor.sof
#   make prog    -> programa la FPGA (dispositivo 2 de la cadena JTAG; el 1 es el HPS)
#   make report  -> resumen de recursos del fitter
#
# Software del ARM (sw/, corre en la OCRAM y se carga por JTAG):
#   make sw        -> compila sw/build/reproductor.elf
#   make gdbserver -> arranca el gdb-server del Cortex-A9 (dejarlo corriendo en otra terminal)
#   make load      -> carga el ELF y lo deja corriendo (necesita make gdbserver)
#   make debug     -> carga el ELF y abre gdb detenido en main
#   make consola   -> consola JTAG UART
#
#   make clean     -> borra lo generado (no toca el .qsys ni las fuentes)
SHELL  := /bin/bash
S      := ../scripts
SYS    := reproductor
OUT    := output
DEVICE := 5CSEMA5F31C6
ENV    := source $(S)/general/env.sh >/dev/null &&
# Script que genera Platform Designer con las asignaciones de los pines DDR3 del HPS.
# Hay que correrlo despues de Analysis & Synthesis y antes del fitter.
# Muestra solo errores, warnings criticos y el resultado de cada herramienta
FILTRO := { grep -E "^(Error|Critical Warning)|was (successful|unsuccessful)" || true; }
PIN_TCL := $(CURDIR)/$(SYS)/synthesis/submodules/hps_sdram_p0_pin_assignments.tcl

all: hw

qsys:
	$(ENV) qsys-edit $(SYS).qsys &

gen:
	$(ENV) qsys-generate $(SYS).qsys --synthesis=VERILOG --family="Cyclone V" \
	    --part=$(DEVICE) --output-directory=$(SYS)

hw: $(OUT)/$(SYS).sof
$(OUT)/$(SYS).sof: $(SYS).qsys pines.qsf timing.sdc
	$(S)/general/build.sh -C -p pines.qsf -q $(SYS).qsys -o $(OUT) timing.sdc
	@echo ">> Analysis & Synthesis (varios minutos con el HPS; log completo: $(OUT)/map.log)"
	set -o pipefail; $(ENV) cd $(OUT) && quartus_map $(SYS) 2>&1 | tee map.log | $(FILTRO)
	@echo ">> Asignando pines de la DDR3 del HPS (log: $(OUT)/pin_assign.log)"
	set -o pipefail; $(ENV) cd $(OUT) && quartus_sta -t $(PIN_TCL) $(SYS) 2>&1 | tee pin_assign.log | $(FILTRO)
	$(S)/general/build.sh $(OUT)/$(SYS).qpf
	@SOF=$$(ls $(OUT)/output_files/$(SYS).sof $(OUT)/$(SYS).sof 2>/dev/null | head -1); \
	  [ "$$SOF" = "$(OUT)/$(SYS).sof" ] || cp "$$SOF" $(OUT)/$(SYS).sof

prog: $(OUT)/$(SYS).sof
	$(S)/general/program.sh $(OUT)/$(SYS).sof

report:
	@cat $$(ls $(OUT)/output_files/$(SYS).fit.summary $(OUT)/$(SYS).fit.summary 2>/dev/null | head -1)

# ---------------- Software del ARM ----------------
CC       := arm-none-eabi-gcc
SIZE     := arm-none-eabi-size
GDB      ?= gdb-multiarch
GDB_PORT ?= 3334
SW       := sw
SW_BUILD := $(SW)/build
ELF      := $(SW_BUILD)/reproductor.elf
SW_SRCS  := $(wildcard $(SW)/arranque/*.S $(SW)/*.c $(SW)/drivers/*.c $(SW)/reproductor/*.c)
SW_HDRS  := $(wildcard $(SW)/include/*.h $(SW)/drivers/*.h $(SW)/reproductor/*.h)
CFLAGS   := -mcpu=cortex-a9 -marm -mno-unaligned-access -O2 -g -std=c11 -ffreestanding -nostdlib \
            -ffunction-sections -fdata-sections -Wall -Wextra \
            -I$(SW)/include -I$(SW)/drivers -I$(SW)/reproductor
LDFLAGS  := -T $(SW)/arranque/ocram.ld -Wl,--gc-sections -Wl,-Map=$(SW_BUILD)/reproductor.map
# libgcc: el Cortex-A9 no tiene division por hardware (__aeabi_uidiv y similares)
LDLIBS   := -lgcc

sw: $(ELF)
$(ELF): $(SW_SRCS) $(SW_HDRS) $(SW)/arranque/ocram.ld
	@mkdir -p $(SW_BUILD)
	$(CC) $(CFLAGS) $(LDFLAGS) $(SW_SRCS) $(LDLIBS) -o $@
	@$(SIZE) $@

gdbserver:
	$(S)/hps/gdb-server.sh

load: $(ELF)
	$(GDB) -batch -ex "set architecture armv7" -ex "target remote :$(GDB_PORT)" \
	    -ex "set *(unsigned int *)0xFFD05014 = *(unsigned int *)0xFFD05014 | 0x40" \
	    -ex "load" -ex "detach" $(ELF)

debug: $(ELF)
	$(GDB) -x $(SW)/cargar.gdb $(ELF)

consola:
	$(S)/general/terminal.sh

clean-sw:
	rm -rf $(SW_BUILD)

clean: clean-sw
	rm -rf $(OUT) $(SYS) $(SYS).sopcinfo

.PHONY: all qsys gen hw prog report sw gdbserver load debug consola clean-sw clean