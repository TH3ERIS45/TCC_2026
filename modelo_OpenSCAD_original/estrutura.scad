// ================================================
// ESTRUTURA.SCAD
// Base da maquete, portico e tubos do eixo Y
// Depende dos parametros globais definidos em config.scad
// ================================================

include <config.scad>

module base_maquete() {
    color("#C68E58") 
        translate([-base_largura_x/2, -base_comprimento_y/2, -base_espessura_z])
        cube([base_largura_x, base_comprimento_y, base_espessura_z]);
}

module estrutura_portico() {
    color("#C68E58") { 
        difference() {
            union() {
                translate([base_largura_x/2 - pilar_lado, base_comprimento_y/2 - pilar_lado, 0]) cube([pilar_lado, pilar_lado, pilar_altura_z]);
                translate([-base_largura_x/2, base_comprimento_y/2 - pilar_lado, 0]) cube([pilar_lado, pilar_lado, pilar_altura_z]);
                translate([base_largura_x/2 - pilar_lado, -base_comprimento_y/2, 0]) cube([pilar_lado, pilar_lado, pilar_altura_z]);
                translate([-base_largura_x/2, -base_comprimento_y/2, 0]) cube([pilar_lado, pilar_lado, pilar_altura_z]);
            }
            union() {
                translate([base_largura_x/2 - pilar_lado/2, base_comprimento_y/2 - pilar_lado - 1, pilar_altura_z - furo_offset_z]) rotate([-90, 0, 0]) cylinder(h=furo_profundidade + 1, d=tubo_pvc_diam);
                translate([-base_largura_x/2 + pilar_lado/2, base_comprimento_y/2 - pilar_lado - 1, pilar_altura_z - furo_offset_z]) rotate([-90, 0, 0]) cylinder(h=furo_profundidade + 1, d=tubo_pvc_diam);
                translate([base_largura_x/2 - pilar_lado/2, -base_comprimento_y/2 + pilar_lado + 1, pilar_altura_z - furo_offset_z]) rotate([90, 0, 0]) cylinder(h=furo_profundidade + 1, d=tubo_pvc_diam);
                translate([-base_largura_x/2 + pilar_lado/2, -base_comprimento_y/2 + pilar_lado + 1, pilar_altura_z - furo_offset_z]) rotate([90, 0, 0]) cylinder(h=furo_profundidade + 1, d=tubo_pvc_diam);
            }
        }
    }
}

module eixo_y() {
    color("#7C5C43") {
        translate([base_largura_x/2 - pilar_lado/2, -base_comprimento_y/2 + pilar_lado - furo_profundidade, pilar_altura_z - furo_offset_z])
            rotate([-90, 0, 0]) cylinder(h=tubo_pvc_comprimento_y, d=tubo_pvc_diam);
        translate([-base_largura_x/2 + pilar_lado/2, -base_comprimento_y/2 + pilar_lado - furo_profundidade, pilar_altura_z - furo_offset_z])
            rotate([-90, 0, 0]) cylinder(h=tubo_pvc_comprimento_y, d=tubo_pvc_diam);
    }
}
