// ====================================================================
// CARRINHO_EIXO_Y.SCAD
// Carrinho slider da ESP32-CAM (Percorre o tubo menor transversal)
// ====================================================================

$fn = 60; // Resolucao das curvas cilindricas

// Variáveis expostas para o main.scad poder calcular o posicionamento.
// Usamos o prefixo "car_esp32_" para evitar conflito com as variáveis do config.scad
car_esp32_comprimento = 70;
car_esp32_altura      = 40;

module carrinho_eixo_y() {
    
    // --- DIMENSOES DO BLOCO PRINCIPAL ---
    bloco_comprimento = car_esp32_comprimento; // Comprimento no sentido do tubo de PVC (eixo Y)
    bloco_largura     = 40; // Largura do bloco
    bloco_altura      = car_esp32_altura; // Altura do bloco central

    // --- PARAMETROS DO CANO DE PVC E FELTRO (Mantidos do Bloco X) ---
    pvc_diametro_nominal = 20;
    feltro_espessura     = 1.0; 
    // Furo com margem de compressao/retracao PLA (22.3mm)
    furo_pvc_diametro    = pvc_diametro_nominal + (2 * feltro_espessura) + 0.3; 

    // --- 2 COLUNAS DE CORREIA NO SENTIDO LONGITUDINAL (EIXO Y) ---
    fita_largura = 11.0; // Largura do canal (10mm + 1mm de folga)
    fita_altura  = 2.2;  // Altura do canal
    coluna_x     = 14.0; // Largura da coluna no eixo X (centralizada)
    coluna_y     = 12.0; // Espessura de cada coluna no eixo Y
    coluna_z     = 10.0; // Altura da coluna acima do bloco

    // --- ALCAS DE SUPORTE DO ESP32-CAM (SISTEMA ABIERTO/LIVRE) ---
    esp32_largura     = 28.0; // Largura interna entre alcas (27mm placa + 1mm folga)
    esp32_comprimento = 41.0; // Distancia entre bordas externas das alcas
    alca_espessura_y  = 8.0;  // Espessura da parede das alcas no eixo Y
    alca_altura_z     = 16.0; // Profundidade da alca abaixo do bloco (espaco p/ fios)
    alca_parede_x     = 3.5;  // Espessura lateral da estrutura da alca

    // ====================================================================
    // CONSTRUCAO DA GEOMETRIA
    // ====================================================================

    difference() {
        
        // 1. ADICAO DE FORMAS (Corpo Solido)
        union() {
            // --- A) CUBO CENTRAL PRINCIPAL ---
            translate([-bloco_largura/2, 0, 0])
                cube([bloco_largura, bloco_comprimento, bloco_altura]);
                
            // --- B) 2 COLUNAS SUPERIORES NAS EXTREMIDADES EM Y (CENTRADAS EM X) ---
            // Coluna Dianteira (Frente: Y = 0)
            translate([-coluna_x/2, 0, bloco_altura])
                cube([coluna_x, coluna_y, coluna_z]);
                
            // Coluna Traseira (Fundo: Y = bloco_comprimento - coluna_y)
            translate([-coluna_x/2, bloco_comprimento - coluna_y, bloco_altura])
                cube([coluna_x, coluna_y, coluna_z]);

            // --- C) ALCAS INFERIORES EM "U" (DIANTEIRA E TRASEIRA) ---
            // Alca Dianteira (Frente do bloco)
            translate([-(esp32_largura + 2*alca_parede_x)/2, 5, -alca_altura_z])
                cube([esp32_largura + 2*alca_parede_x, alca_espessura_y, alca_altura_z]);
                
            // Alca Traseira (Trás do bloco)
            translate([-(esp32_largura + 2*alca_parede_x)/2, bloco_comprimento - 5 - alca_espessura_y, -alca_altura_z])
                cube([esp32_largura + 2*alca_parede_x, alca_espessura_y, alca_altura_z]);
        }
        
        // 2. SUBTRACAO DE FORMAS (Furos e Recortes)
        
        // --- A) FURO CENTRAL DO CANO DE PVC ---
        translate([0, -1, bloco_altura/2])
            rotate([-90, 0, 0])
                cylinder(d = furo_pvc_diametro, h = bloco_comprimento + 2);
                
        // Chanfros de entrada e saida (Alivio para o feltro nao rasgar)
        translate([0, -0.1, bloco_altura/2])
            rotate([-90, 0, 0])
                cylinder(d1 = furo_pvc_diametro + 4, d2 = furo_pvc_diametro, h = 3);
                
        translate([0, bloco_comprimento - 2.9, bloco_altura/2])
            rotate([-90, 0, 0])
                cylinder(d1 = furo_pvc_diametro, d2 = furo_pvc_diametro + 4, h = 3);

        // --- B) RASGO LONGITUDINAL NAS COLUNAS (PASSAGEM DA CORREIA EM Y) ---
        // O rasgo atravessa o bloco no sentido Y de fora a fora
        translate([-(fita_largura)/2, -1, bloco_altura + (coluna_z - fita_altura)/2])
            cube([fita_largura, bloco_comprimento + 2, fita_altura]);

        // --- C) RECORTE EM "U" NAS ALCAS INFERIORES (ESP32-CAM) ---
        // Recorte interno na Alca Dianteira (Apoio do PCB)
        translate([-esp32_largura/2, 4, -alca_altura_z + 3])
            cube([esp32_largura, alca_espessura_y + 2, alca_altura_z]);
            
        // Recorte interno na Alca Traseira (Apoio do PCB)
        translate([-esp32_largura/2, bloco_comprimento - 6 - alca_espessura_y, -alca_altura_z + 3])
            cube([esp32_largura, alca_espessura_y + 2, alca_altura_z]);

        // --- D) RASGO RETANGULAR DE TRAVA (M3 / ZIP-TIE) ---
        translate([-1.75, bloco_comprimento - 5 - alca_espessura_y - 1, -alca_altura_z + 1.5])
            cube([3.5, alca_espessura_y + 2, 3.5]);
    }
}