// ================================================
// PECAS_MOVEIS.SCAD
// Carrinho deslizante e suportes de PVC/rolamento
// Depende dos parametros globais definidos em config.scad
// ================================================

include <config.scad>

module Peca_Deslizante() {
    difference() {
        
        // 1. CORPO SÓLIDO DO BLOCO
        union() {
            // Cubo centralizador principal
            translate([-bloco_largura/2, 0, 0])
                cube([bloco_largura, bloco_comprimento, bloco_altura]);
            
            // Aba superior direita
            translate([bloco_largura/2, 0, bloco_altura - 10])
                cube([15, bloco_comprimento, 10]);
                
            // Aba superior esquerda
            translate([-bloco_largura/2 - 15, 0, bloco_altura - 10])
                cube([15, bloco_comprimento, 10]);
                
            // Perna lateral inferior esquerda - FRENTE
            translate([-bloco_largura/2 - 15, 0, 0])
                cube([15, 10, 18]);
                
            // Perna lateral inferior esquerda - TRÁS
            translate([-bloco_largura/2 - 15, bloco_comprimento - 10, 0])
                cube([15, 10, 18]);
        }
        
        // 2. RECORTES E FUROS
        // Furo Central do Cano de PVC
        translate([0, -1, bloco_altura/2])
            rotate([-90, 0, 0])
                cylinder(d = furo_pvc_diametro, h = bloco_comprimento + 2);
                
        // Chanfros
        translate([0, -0.1, bloco_altura/2])
            rotate([-90, 0, 0])
                cylinder(d1 = furo_pvc_diametro + 4, d2 = furo_pvc_diametro, h = 3);
                
        translate([0, bloco_comprimento - 2.9, bloco_altura/2])
            rotate([-90, 0, 0])
                cylinder(d1 = furo_pvc_diametro, d2 = furo_pvc_diametro + 4, h = 3);

        // Furos dos Parafusos M4
        translate([bloco_largura/2 + 7.5, bloco_comprimento/4, bloco_altura - 11])
            cylinder(d = parafuso_m4_diametro, h = 15);
        translate([bloco_largura/2 + 7.5, 3*bloco_comprimento/4, bloco_altura - 11])
            cylinder(d = parafuso_m4_diametro, h = 15);
            
        translate([-bloco_largura/2 - 7.5, bloco_comprimento/4, bloco_altura - 11])
            cylinder(d = parafuso_m4_diametro, h = 15);
        translate([-bloco_largura/2 - 7.5, 3*bloco_comprimento/4, bloco_altura - 11])
            cylinder(d = parafuso_m4_diametro, h = 15);

        // Encaixes Sextavados
        translate([bloco_largura/2 + 7.5, bloco_comprimento/4, bloco_altura - 10 - porca_m4_altura])
            rotate([0, 0, 30]) cylinder(d = porca_m4_largura / cos(30), h = porca_m4_altura + 0.1, $fn=6);
        translate([bloco_largura/2 + 7.5, 3*bloco_comprimento/4, bloco_altura - 10 - porca_m4_altura])
            rotate([0, 0, 30]) cylinder(d = porca_m4_largura / cos(30), h = porca_m4_altura + 0.1, $fn=6);
            
        translate([-bloco_largura/2 - 7.5, bloco_comprimento/4, bloco_altura - 10 - porca_m4_altura])
            rotate([0, 0, 30]) cylinder(d = porca_m4_largura / cos(30), h = porca_m4_altura + 0.1, $fn=6);
        translate([-bloco_largura/2 - 7.5, 3*bloco_comprimento/4, bloco_altura - 10 - porca_m4_altura])
            rotate([0, 0, 30]) cylinder(d = porca_m4_largura / cos(30), h = porca_m4_altura + 0.1, $fn=6);
            
        // Furos retangulares fita
        translate([-bloco_largura/2 - 7.5 - (fita_largura/2), -1, 9 - (fita_altura/2)])
            cube([fita_largura, bloco_comprimento + 2, fita_altura]);
    }
}

module Suporte_Cano_X() {
    pvc_furo_diametro    = 22.3;  
    copo_profundidade    = 25.0;  
    vao_livre_altura     = 35.0;  
    espessura_parede     = 6.0;   
    furo_m4_passante     = 4.5;   
    porca_m4_largura     = 7.4;   
    porca_m4_altura      = 3.5;   

    bloco_largura        = pvc_furo_diametro + (2 * espessura_parede); 
    bloco_comprimento    = copo_profundidade + espessura_parede;       
    bloco_altura_total   = vao_livre_altura + pvc_furo_diametro + espessura_parede; 
    aba_largura          = 15.0;  

    centro_pvc_z         = pvc_furo_diametro/2 + espessura_parede;
    aba_face_inferior_z  = bloco_altura_total - espessura_parede;

    difference() {
        union() {
            translate([-bloco_largura/2, 0, 0])
                cube([bloco_largura, bloco_comprimento, aba_face_inferior_z]);
            translate([-(bloco_largura/2 + aba_largura), 0, aba_face_inferior_z])
                cube([bloco_largura + (2 * aba_largura), bloco_comprimento, espessura_parede]);
        }
        
        translate([0, espessura_parede, centro_pvc_z])
            rotate([-90, 0, 0])
                cylinder(d = pvc_furo_diametro, h = copo_profundidade + 0.1);
        translate([0, bloco_comprimento - 2, centro_pvc_z])
            rotate([-90, 0, 0])
                cylinder(d1 = pvc_furo_diametro, d2 = pvc_furo_diametro + 3, h = 2.1);

        translate([-(bloco_largura/2 + aba_largura/2), bloco_comprimento/2, -1])
            cylinder(d = furo_m4_passante, h = bloco_altura_total + 2);
        translate([-(bloco_largura/2 + aba_largura/2), bloco_comprimento/2, aba_face_inferior_z - 0.1])
            rotate([0, 0, 30])
                cylinder(d = porca_m4_largura / cos(30), h = porca_m4_altura + 0.1, $fn = 6);

        translate([(bloco_largura/2 + aba_largura/2), bloco_comprimento/2, -1])
            cylinder(d = furo_m4_passante, h = bloco_altura_total + 2);
        translate([(bloco_largura/2 + aba_largura/2), bloco_comprimento/2, aba_face_inferior_z - 0.1])
            rotate([0, 0, 30])
                cylinder(d = porca_m4_largura / cos(30), h = porca_m4_altura + 0.1, $fn = 6);

        translate([-bloco_largura/2 - 1, bloco_comprimento/2, centro_pvc_z])
            rotate([0, 90, 0])
                cylinder(d = furo_m4_passante, h = bloco_largura + 2);
        translate([-bloco_largura/2 - 0.1, bloco_comprimento/2, centro_pvc_z])
            rotate([0, 90, 0])
                rotate([0, 0, 30])
                    cylinder(d = porca_m4_largura / cos(30), h = porca_m4_altura + 0.1, $fn = 6);
    }
}

module Suporte_Rolamento() {
    base_comprimento = 55.0; 
    base_largura     = 13.0; 
    base_espessura   = 5.0;  
    furos_distancia  = 42.0; 
    furo_fixacao_d   = 4.5;  
    roda_diametro    = 27.0; 
    roda_altura_max  = 28.0; 
    eixo_d           = 8.0;  
    
    centro_x         = base_comprimento / 2;
    furo_centro_z    = roda_altura_max - (roda_diametro / 2);
    furo_esq_x       = (base_comprimento - furos_distancia) / 2;
    furo_dir_x       = furo_esq_x + furos_distancia;
    centro_y_base    = base_largura / 2;

    translate([-centro_x, -centro_y_base, 0]) {
        difference() {
            union() {
                cube([base_comprimento, base_largura, base_espessura]);
                translate([centro_x - (roda_diametro/2), 0, 0]) 
                    cube([roda_diametro, base_largura, furo_centro_z]);
                translate([centro_x, 0, furo_centro_z]) 
                    rotate([-90, 0, 0]) 
                    cylinder(h=base_largura, d=roda_diametro);
            }
            translate([centro_x, -1, furo_centro_z]) 
                rotate([-90, 0, 0]) 
                cylinder(h=base_largura + 2, d=eixo_d);
            translate([furo_esq_x, centro_y_base, -1]) 
                cylinder(h=base_espessura + 2, d=furo_fixacao_d);
            translate([furo_dir_x, centro_y_base, -1]) 
                cylinder(h=base_espessura + 2, d=furo_fixacao_d);
        }
    }
}

module Suporte_Polia_Lisa() {
    esp        = 10;    // espessura da barra e das pernas (eixo X)
    comp_barra = 41;    // comprimento da barra superior (eixo Y)
    alt_barra  = 4.0;   // altura da barra superior (eixo Z)

    esp_perna    = esp; // mesma espessura da barra (sem degrau lateral)
    leg_x_offset = 0;   // perna alinhada com a barra (mesma largura)

    larg_perna = 6;     // profundidade de cada perna (eixo Y)
    alt_perna  = 15;    // altura de cada perna (eixo Z, abaixo da barra)

    // Pino de metal usinado (Ø5mm, colado nas pernas e na polia)
    eixo_pino_d   = 5.0;
    folga_colagem = 0.2;
    furo_perna_d  = eixo_pino_d + folga_colagem;

    // Polia lisa GT2 (correia de 6mm) - largura ao longo do eixo = 8.6mm
    polia_largura_eixo = 8.6;
    folga_vao_polia    = 2.5; // folga de cada lado da polia entre as pernas
    vao_livre_polia    = polia_largura_eixo + (2 * folga_vao_polia);

    bloco_pernas_largura = (larg_perna * 2) + vao_livre_polia;
    perna1_y = (comp_barra / 2) - (bloco_pernas_largura / 2);
    perna2_y = perna1_y + larg_perna + vao_livre_polia;

    furo_barra_d  = 3.0;
    furo_barra_x  = esp / 2;
    furo_barra_y1 = 4.5;
    furo_barra_y2 = 37.0;

    furo_perna_z = 5.0;
    furo_perna_x = leg_x_offset + (esp_perna / 2);

    difference() {
        union() {
            translate([0, 0, alt_perna])
                cube([esp, comp_barra, alt_barra]);
            translate([leg_x_offset, perna1_y, 0])
                cube([esp_perna, larg_perna, alt_perna]);
            translate([leg_x_offset, perna2_y, 0])
                cube([esp_perna, larg_perna, alt_perna]);
        }
        translate([furo_barra_x, furo_barra_y1, alt_perna - 1])
            cylinder(d = furo_barra_d, h = alt_barra + 2);
        translate([furo_barra_x, furo_barra_y2, alt_perna - 1])
            cylinder(d = furo_barra_d, h = alt_barra + 2);
        translate([furo_perna_x, perna1_y - 1, furo_perna_z])
            rotate([-90, 0, 0])
                cylinder(d = furo_perna_d, h = larg_perna + 2);
        translate([furo_perna_x, perna2_y - 1, furo_perna_z])
            rotate([-90, 0, 0])
                cylinder(d = furo_perna_d, h = larg_perna + 2);
    }
}
