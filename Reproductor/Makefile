# Reproductor de audio - DE1-SoC (HPS bare metal + perifericos en la FPGA)
# Fase 1: todo se carga por JTAG.
#
#   make qsys    -> abre reproductor.qsys en Platform Designer
#   make gen     -> solo genera el sistema (qsys-generate); sirve para ver errores del .qsys
#   make hw      -> genera, crea el proyecto, asigna pines DDR3 del HPS y compila
#                   -> output/reproductor.sof
#   make prog    -> programa la FPGA (dispositivo 2 de la cadena JTAG; el 1 es el HPS)
#   make report  -> resumen de recursos del fitter
#   make clean   -> borra lo generado (no toca el .qsys ni las fuentes)
#
# El software del ARM (compilar y cargar por JTAG) se agrega en el siguiente incremento,
# segun el resultado del incremento 0 (ver ../docs/hardware/guia-platform-designer.md).
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

clean:
	rm -rf $(OUT) $(SYS) $(SYS).sopcinfo

.PHONY: all qsys gen hw prog report clean