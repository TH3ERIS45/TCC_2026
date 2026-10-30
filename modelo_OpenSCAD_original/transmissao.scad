// ================================================
// TRANSMISSAO.SCAD
// Polias, correias GT2, acoplamento flexivel e motor NEMA17
// Modulos autocontidos (nao dependem de config.scad)
// ================================================

module polia_gt2_20t() {
    $fn = 120;
    diametro_furo = 8.0;
    diametro_flange_a = 15.9;
    espessura_flange_a = 1.2;
    diametro_externo_dentes = 12.3; 
    diametro_raiz_dentes = 11.3;    
    largura_corpo = 11.0;
    numero_dentes = 20;
    largura_base_dente = 1.3;       
    diametro_flange_b = 15.9;
    espessura_flange_b = 1.2;
    diametro_cubo = 15.9;
    espessura_cubo = 6.0;

    altura_total = espessura_flange_a + largura_corpo + espessura_flange_b + espessura_cubo;
    
    difference() {
        union() {
            cylinder(h = espessura_flange_a, d = diametro_flange_a);
            translate([0, 0, espessura_flange_a]) {
                cylinder(h = largura_corpo, d = diametro_raiz_dentes);
                for(i = [0 : numero_dentes - 1]) {
                    rotate([0, 0, i * (360 / numero_dentes)])
                        linear_extrude(height = largura_corpo)
                            polygon(points=[
                                [-largura_base_dente/2, (diametro_raiz_dentes/2) - 0.1], 
                                [largura_base_dente/2, (diametro_raiz_dentes/2) - 0.1],
                                [0, diametro_externo_dentes/2] 
                            ]);
                }
            }
            translate([0, 0, espessura_flange_a + largura_corpo])
                cylinder(h = espessura_flange_b, d = diametro_flange_b);
            translate([0, 0, espessura_flange_a + largura_corpo + espessura_flange_b])
                cylinder(h = espessura_cubo, d = diametro_cubo);
        }
        translate([0, 0, -1])
            cylinder(h = altura_total + 2, d = diametro_furo);
    }
}

module polia_idler_realista() {
    $fn = 120;
    diametro_flange = 15.9; 
    espessura_flange = 1.0; 
    diametro_cintura = 12.3; 
    largura_cintura = 11.0; 
    furo_alojamento = 11.0; 
    furo_eixo = 8.0;        
    rolamento_largura = 7.0;

    altura_total = (espessura_flange * 2) + largura_cintura;
    
    union() {
        color("Silver") {
            difference() {
                union() {
                    cylinder(h = espessura_flange, d = diametro_flange);
                    translate([0, 0, espessura_flange])
                        cylinder(h = largura_cintura, d = diametro_cintura);
                    translate([0, 0, espessura_flange + largura_cintura])
                        cylinder(h = espessura_flange, d = diametro_flange);
                }
                translate([0, 0, (altura_total - rolamento_largura) / 2])
                    cylinder(h = rolamento_largura, d = furo_alojamento);
                translate([0, 0, -1])
                    cylinder(h = altura_total + 2, d = furo_eixo);
            }
        }
        color("DimGray") {
            translate([0, 0, (altura_total - rolamento_largura) / 2]) {
                difference() {
                    cylinder(h = rolamento_largura, d = furo_alojamento);
                    translate([0, 0, -1])
                        cylinder(h = rolamento_largura + 2, d = furo_eixo);
                }
            }
        }
    }
}

// Polia lisa GT2 para correia de 6mm - usada no Suporte_Polia_Lisa
// (medidas extraídas de Modelo_3D_-_Polia_lisa_gt2_para_correia_de_6mm.scad)
module polia_lisa_gt2_6mm() {
    $fn = 120;
    diametro_flange   = 18.0;
    espessura_flange  = 1.05;
    diametro_cintura  = 12.3;
    largura_cintura   = 6.5;
    furo_alojamento   = 10.0;
    furo_eixo         = 5.0;
    rolamento_largura = 8.0;

    altura_total = (espessura_flange * 2) + largura_cintura;

    union() {
        color("Silver") {
            difference() {
                union() {
                    cylinder(h = espessura_flange, d = diametro_flange);
                    translate([0, 0, espessura_flange])
                        cylinder(h = largura_cintura, d = diametro_cintura);
                    translate([0, 0, espessura_flange + largura_cintura])
                        cylinder(h = espessura_flange, d = diametro_flange);
                }
                translate([0, 0, (altura_total - rolamento_largura) / 2])
                    cylinder(h = rolamento_largura, d = furo_alojamento);
                translate([0, 0, -1])
                    cylinder(h = altura_total + 2, d = furo_eixo);
            }
        }
        color("DimGray") {
            translate([0, 0, (altura_total - rolamento_largura) / 2]) {
                difference() {
                    cylinder(h = rolamento_largura, d = furo_alojamento);
                    translate([0, 0, -1])
                        cylinder(h = rolamento_largura + 2, d = furo_eixo);
                }
            }
        }
    }
}

module curva_correia_gt2() {
    largura = 10.0;
    espessura_base = 0.63;
    altura_dente = 0.75;
    base_dente = 1.2;
    
    raio_base = 6.4; 
    raio_dente = base_dente / 2;               
    altura_reta = altura_dente - raio_dente;   
    
    module perfil_curvo_2d() {
        union() {
            difference() {
                circle(r = raio_base + espessura_base, $fn = 120);
                circle(r = raio_base, $fn = 120);
                
                translate([-(raio_base + 5), -(raio_base + 5)])
                    square([(raio_base + 5) * 2, raio_base + 5]);
            }
            
            for (i = [0 : 9]) {
                angulo = (i * 18) + 9; 
                
                rotate([0, 0, angulo])
                translate([raio_base, 0])
                rotate([0, 0, 90]) 
                union() {
                    translate([-base_dente/2, 0])
                        square([base_dente, altura_reta]);
                    
                    translate([0, altura_reta])
                        circle(r = raio_dente, $fn = 30);
                }
            }
        }
    }
    
    color("Black") {
        linear_extrude(height = largura, convexity = 10)
            perfil_curvo_2d();
    }
}

module fita_reta_gt2(comprimento = 100.0) {
    largura = 10.0;
    passo = 2.0;
    espessura_base = 0.63;
    altura_dente = 0.75;
    base_dente = 1.2;
    
    raio_dente = base_dente / 2;               
    y_centro_arco = altura_dente - raio_dente; 
    
    module perfil_lateral_2d() {
        translate([0, -espessura_base])
            square([comprimento, espessura_base]);
            
        qtd_dentes = floor(comprimento / passo);
        for (i = [0 : qtd_dentes - 1]) {
            translate([i * passo + passo/2, 0]) {
                union() {
                    translate([-base_dente/2, 0])
                        square([base_dente, y_centro_arco]);
                    translate([0, y_centro_arco])
                        circle(r = raio_dente, $fn = 20);
                }
            }
        }
    }
    
    color("Black") {
        translate([0, 0, -largura/2])
            linear_extrude(height = largura, convexity = 10)
                perfil_lateral_2d();
    }
}

module cubo_arredondado_centro(largura, profundidade, altura, raio) {
    translate([0, 0, altura/2])
    linear_extrude(height = altura, center = true)
    hull() {
        translate([ largura/2 - raio,  profundidade/2 - raio, 0]) circle(r = raio);
        translate([-largura/2 + raio,  profundidade/2 - raio, 0]) circle(r = raio);
        translate([-largura/2 + raio, -profundidade/2 + raio, 0]) circle(r = raio);
        translate([ largura/2 - raio, -profundidade/2 + raio, 0]) circle(r = raio);
    }
}

module nema17() {
    corpo_lado = 42.3;
    corpo_comprimento = 40.0;
    corpo_raio_canto = 1.0;
    placa_lado = 42.3;
    placa_espessura = 2.5;
    placa_raio_canto = 3.5;
    ressalto_diametro = 22.0;
    ressalto_altura = 1.5;
    eixo_diametro = 5.0;     
    eixo_comprimento = 24.0; 
    conector_largura = 10.0;
    conector_altura = 6.0;   
    conector_profund = 8.0;  

    // Corpo Principal
    color("Black") cubo_arredondado_centro(corpo_lado, corpo_lado, corpo_comprimento, corpo_raio_canto);
    // Placa Frontal
    color("Silver") translate([0, 0, corpo_comprimento]) cubo_arredondado_centro(placa_lado, placa_lado, placa_espessura, placa_raio_canto);
    // Ressalto Circular
    color("Silver") translate([0, 0, corpo_comprimento + placa_espessura]) cylinder(h = ressalto_altura, d = ressalto_diametro);
    // Eixo
    color("LightGray") translate([0, 0, corpo_comprimento + placa_espessura + ressalto_altura]) cylinder(h = eixo_comprimento, d = eixo_diametro);
    // Conector de Pinos
    color("Ivory") translate([corpo_lado/2 + conector_profund/2, 0, conector_altura/2 + 2]) cube([conector_profund, conector_largura, conector_altura], center = true);
}

// NOVO MÓDULO: ACOPLAMENTO FLEXÍVEL 5mm para 8mm
module acoplamento_flexivel() {
    D_externo = 19.0;
    L_total = 25.0;
    furo_A = 5.0; 
    furo_B = 8.0; 
    prof_furo = 12.0; 
    d_parafuso = 3.0;
    z_parafuso_A = 4.0;  
    z_parafuso_B = 21.0; 

    union() {
        color("Silver") {
            difference() {
                cylinder(d = D_externo, h = L_total, $fn = 120);
                
                translate([0, 0, -1])
                    cylinder(d = furo_A, h = prof_furo + 1, $fn = 60);
                    
                translate([0, 0, L_total - prof_furo])
                    cylinder(d = furo_B, h = prof_furo + 1, $fn = 60);
                    
                translate([0, 0, z_parafuso_A]) {
                    rotate([0, 90, 0]) cylinder(d = d_parafuso, h = D_externo/2 + 2, $fn = 30);
                    rotate([-90, 0, 0]) cylinder(d = d_parafuso, h = D_externo/2 + 2, $fn = 30);
                }
                
                translate([0, 0, z_parafuso_B]) {
                    rotate([0, 90, 0]) cylinder(d = d_parafuso, h = D_externo/2 + 2, $fn = 30);
                    rotate([-90, 0, 0]) cylinder(d = d_parafuso, h = D_externo/2 + 2, $fn = 30);
                }
            }
        }
        
        color("DimGray") {
            for (z = [9 : 1.5 : 16]) {
                translate([0, 0, z])
                difference() {
                    cylinder(d = D_externo + 0.1, h = 0.5, $fn = 120);
                    translate([0, 0, -1]) cylinder(d = D_externo - 1.0, h = 2.0, $fn = 60);
                }
            }
        }
    }
}
