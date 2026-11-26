# Power grid of sram_64x32: vertical metal 4 straps only, so that metal 5 stays free for the chip
# that uses the macro (its horizontal metal 5 straps connect to these straps from above).
#
# The power pins of the array macro are horizontal metal 3 rails. The metal 4 straps run across
# the array and connect to those rails with vias, the same way they connect to the metal 1 rails
# of the standard-cell rows.
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
source $::env(SCRIPTS_DIR)/openroad/common/set_global_connections.tcl
set_global_connections

set_voltage_domain -name CORE -power $::env(VDD_NET) -ground $::env(GND_NET)

define_pdn_grid -name stdcell_grid -starts_with POWER -voltage_domain CORE -pins "$::env(PDN_VERTICAL_LAYER)"

add_pdn_stripe -grid stdcell_grid -layer $::env(PDN_VERTICAL_LAYER) \
    -width $::env(PDN_VWIDTH) -pitch $::env(PDN_VPITCH) -offset $::env(PDN_VOFFSET) -spacing $::env(PDN_VSPACING) \
    -starts_with POWER -extend_to_core_ring

add_pdn_stripe -grid stdcell_grid -layer $::env(PDN_RAIL_LAYER) -width $::env(PDN_RAIL_WIDTH) -followpins
add_pdn_connect -grid stdcell_grid -layers "$::env(PDN_RAIL_LAYER) $::env(PDN_VERTICAL_LAYER)"

define_pdn_grid -macro -default -name macro -starts_with POWER -halo "$::env(PDN_HORIZONTAL_HALO) $::env(PDN_VERTICAL_HALO)"
add_pdn_connect -grid macro -layers "met3 $::env(PDN_VERTICAL_LAYER)"
