// ================================================
// MAQUETE AUTOMATIZADA DE MONITORAMENTO AGRÍCOLA
// TCC Engenharia Mecatrônica - Modelo OpenSCAD
// ================================================

// Resolução de renderização de curvas
$fn = 60;

// ================================================
// 1. PARÂMETROS E CONFIGURAÇÕES GERAIS
// ================================================

// --- Dimensões da Maquete (Base e Estrutura) ---
largura_util_x         = 500;  // Área útil X (50 cm)
comprimento_util_y     = 1000; // Área útil Y (100 cm)
base_largura_x         = 560;  // Largura total da base (56 cm)
base_comprimento_y     = 1060; // Comprimento total da base (106 cm)
base_espessura_z       = 30;   // Grossura/Espessura da base (3 cm)
pilar_lado             = 30;   // Seção do pilar (3 cm)
pilar_altura_z         = 300;  // Altura do pilar (30 cm)
tubo_pvc_diam          = 20.0; // Diâmetro externo de 1/2 polegada (20 mm)
furo_profundidade      = 15;   // Profundidade do encaixe do PVC (1.5 cm)
furo_offset_z          = 25;   // Distância do centro do furo para o topo (2.5 cm)
tubo_pvc_comprimento_y = 1030; // Comprimento total do tubo (100 + 1.5 + 1.5 = 103 cm)

// --- Dimensões do Bloco Deslizante ---
bloco_comprimento      = 90;   // Longo (9cm) para evitar tombamento
bloco_largura          = 40; 
bloco_altura           = 45;
pvc_diametro_nominal   = 20;
feltro_espessura       = 1.0;  // Espessura do feltro/veludo adesivo
furo_pvc_diametro      = pvc_diametro_nominal + (2 * feltro_espessura) + 0.3; // Furo total + folga (22.3)
parafuso_m4_diametro   = 4.5;  // Furo passante com folga
porca_m4_largura       = 7.4;  // Medida entre faces planas da porca sextavada
porca_m4_altura        = 4.0;  // Profundidade do encaixe da porca
fita_largura           = 11.0; // Largura do furo horizontal para a fita (fita de 10mm + folga)
fita_altura            = 2.2;  // Altura/espessura do furo para a fita

