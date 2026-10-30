// ================================================
// MAIN_2.SCAD
// Montagem final da maquete - so posiciona as pecas
// Editar aqui APENAS translate()/rotate() de posicionamento
// ================================================

include <config.scad>
use <pecas_moveis.scad>
use <transmissao.scad>
use <estrutura.scad>
include <suporte_nema.scad>
use <Suporte_Nema_Eixo_Y.scad>

// AQUI ESTAVA O ERRO: Corrigido para o nome exato do seu arquivo
include <Carrinho_eixoY_2.scad>

// ================================================
// 3. RENDERIZAÇÃO E MONTAGEM FINAL
// ================================================

base_maquete();

// Placa de isopor (Fundo Verde) e Terra Seca
color("#4CAF50") translate([-largura_util_x/2, -comprimento_util_y/2, 0]) cube([largura_util_x, comprimento_util_y, 30]);
color("#A0785A") translate([-150, -400, 30]) cube([300, 800, 1]); 

estrutura_portico();
eixo_y(); 

// --- Montagem das Peças Deslizantes ---
posicao_y_carrinho = -bloco_comprimento / 2;
color("White") translate([base_largura_x/2 - pilar_lado/2, posicao_y_carrinho, pilar_altura_z - furo_offset_z - bloco_altura/2]) mirror([1, 0, 0]) Peca_Deslizante();
color("White") translate([-base_largura_x/2 + pilar_lado/2, posicao_y_carrinho, pilar_altura_z - furo_offset_z - bloco_altura/2]) Peca_Deslizante();

// --- Travessa do Eixo X e Pilares Horizontais ---
color("#C68E58") translate([-base_largura_x/2 + pilar_lado/2 - bloco_largura/2 - 15, posicao_y_carrinho, pilar_altura_z - furo_offset_z + bloco_altura/2]) cube([base_largura_x - pilar_lado + bloco_largura + 30, bloco_comprimento, 20]);
color("#C68E58") {
    translate([-base_largura_x/2, base_comprimento_y/2 - pilar_lado, pilar_altura_z]) cube([base_largura_x, pilar_lado, pilar_lado]);
    translate([-base_largura_x/2, -base_comprimento_y/2, pilar_altura_z]) cube([base_largura_x, pilar_lado, pilar_lado]);
}

// --- Suportes e Eixo X (Cano central) ---
pezinho_altura_z = 35.0 + 22.3 + 6.0; 
color("White") translate([base_largura_x/2 - pilar_lado/2 - bloco_largura/2 - 15, 0, pilar_altura_z - furo_offset_z + bloco_altura/2 - pezinho_altura_z]) rotate([0, 0, 90]) Suporte_Cano_X();
color("White") translate([-base_largura_x/2 + pilar_lado/2 + bloco_largura/2 + 15, 0, pilar_altura_z - furo_offset_z + bloco_altura/2 - pezinho_altura_z]) rotate([0, 0, -90]) Suporte_Cano_X();

tubo_x_comprimento = 448;
centro_z_tubo_x = pilar_altura_z - furo_offset_z + bloco_altura/2 - pezinho_altura_z + (22.3/2 + 6.0);
color("#7C5C43") translate([0, 0, centro_z_tubo_x]) rotate([0, 90, 0]) cylinder(h=tubo_x_comprimento, d=tubo_pvc_diam, center=true);


// ========================================================
// --- CÁLCULO DE ALINHAMENTO Z E Y DA CORREIA ---
// ========================================================
z_base_bloco = pilar_altura_z - furo_offset_z - bloco_altura/2;
z_furo_correia = z_base_bloco + 9.0;
raio_polia_correia = 6.4; 
z_eixos_polias = z_furo_correia - raio_polia_correia;

furo_centro_dist_base = 28.0 - (27.0 / 2); 
pos_y_polia_frente = -base_comprimento_y/2 - furo_centro_dist_base;
pos_y_polia_tras   = base_comprimento_y/2 - pilar_lado/2;

pos_x_bloco_centro = base_largura_x/2 - pilar_lado/2; 
distancia_aba = 27.5; 
pos_x_alinhamento = pos_x_bloco_centro + distancia_aba; 

// ========================================================
// 4. Suportes de Rolamento, Eixo Central e Polias Dentadas Frontais
// ========================================================
color("#333333") translate([-base_largura_x/2 + pilar_lado/2, -base_comprimento_y/2, z_eixos_polias]) rotate([0, 90, -90]) Suporte_Rolamento();
color("#333333") translate([base_largura_x/2 - pilar_lado/2, -base_comprimento_y/2, z_eixos_polias]) rotate([0, 90, -90]) Suporte_Rolamento();

// Mantém a ponta direita (lado do motor) exatamente onde estava
ponta_direita_x = ((base_largura_x - pilar_lado) + 113.0) / 2; 

// Define a ponta esquerda deixando apenas 10mm de sobra para fora do pilar
sobra_eixo_esq = 30; 
ponta_esquerda_x = -base_largura_x/2 - sobra_eixo_esq;

// Calcula o novo comprimento assimétrico e o novo centro do cilindro
comprimento_cilindro_eixo = ponta_direita_x - ponta_esquerda_x;
centro_x_cilindro = ponta_esquerda_x + (comprimento_cilindro_eixo / 2);

color("Silver") translate([centro_x_cilindro, pos_y_polia_frente, z_eixos_polias]) rotate([0, 90, 0]) cylinder(h=comprimento_cilindro_eixo, d=8.0, center=true);

offset_polia = 1.2 + (11.0 / 2); 
color("Silver") translate([pos_x_alinhamento - offset_polia, pos_y_polia_frente, z_eixos_polias]) rotate([0, 90, 0]) polia_gt2_20t();
color("Silver") translate([-pos_x_alinhamento + offset_polia, pos_y_polia_frente, z_eixos_polias]) rotate([0, -90, 0]) polia_gt2_20t();

// ========================================================
// 5. Eixos Traseiros Recortados e Polias Lisas (Idler)
// ========================================================
comprimento_pino_traseiro = 40.0; 
color("Silver") translate([base_largura_x/2 - pilar_lado/2, base_comprimento_y/2 - pilar_lado/2, z_eixos_polias]) rotate([0, 90, 0]) cylinder(h=comprimento_pino_traseiro, d=8.0);
color("Silver") translate([-(base_largura_x/2 - pilar_lado/2), base_comprimento_y/2 - pilar_lado/2, z_eixos_polias]) rotate([0, -90, 0]) cylinder(h=comprimento_pino_traseiro, d=8.0);

offset_polia_idler = 1.0 + (11.0 / 2); 
translate([pos_x_alinhamento - offset_polia_idler, pos_y_polia_tras, z_eixos_polias]) rotate([0, 90, 0]) polia_idler_realista();
translate([-pos_x_alinhamento + offset_polia_idler, pos_y_polia_tras, z_eixos_polias]) rotate([0, -90, 0]) polia_idler_realista();

// ========================================================
// 6. MONTAGEM COMPLETA DAS CORREIAS (CURVAS E RETAS)
// ========================================================
translate([pos_x_alinhamento, pos_y_polia_frente, z_eixos_polias]) rotate([0, 90, 0]) translate([0, 0, -5]) rotate([0, 0, 180]) curva_correia_gt2(); 
translate([-pos_x_alinhamento, pos_y_polia_frente, z_eixos_polias]) rotate([0, 90, 0]) translate([0, 0, -5]) rotate([0, 0, 180]) curva_correia_gt2();
translate([pos_x_alinhamento, pos_y_polia_tras, z_eixos_polias]) rotate([0, 90, 0]) translate([0, 0, -5]) curva_correia_gt2();
translate([-pos_x_alinhamento, pos_y_polia_tras, z_eixos_polias]) rotate([0, 90, 0]) translate([0, 0, -5]) curva_correia_gt2();

comp_maior = pos_y_polia_tras - pos_y_polia_frente; 
y_encaixe_bloco_frente = posicao_y_carrinho + 10;                     
y_encaixe_bloco_tras   = posicao_y_carrinho + bloco_comprimento - 10; 
comp_menor_frente = y_encaixe_bloco_frente - pos_y_polia_frente; 
comp_menor_tras   = pos_y_polia_tras - y_encaixe_bloco_tras;     
z_tangente_inf = z_eixos_polias - 6.4;
z_tangente_sup = z_eixos_polias + 6.4;

translate([pos_x_alinhamento, pos_y_polia_frente, z_tangente_inf]) rotate([90, 0, 90]) fita_reta_gt2(comp_maior);
translate([pos_x_alinhamento, pos_y_polia_frente, z_tangente_sup]) rotate([-90, 0, 90]) fita_reta_gt2(comp_menor_frente);
translate([pos_x_alinhamento, y_encaixe_bloco_tras, z_tangente_sup]) rotate([-90, 0, 90]) fita_reta_gt2(comp_menor_tras);
translate([-pos_x_alinhamento, pos_y_polia_frente, z_tangente_inf]) rotate([90, 0, 90]) fita_reta_gt2(comp_maior);
translate([-pos_x_alinhamento, pos_y_polia_frente, z_tangente_sup]) rotate([-90, 0, 90]) fita_reta_gt2(comp_menor_frente);
translate([-pos_x_alinhamento, y_encaixe_bloco_tras, z_tangente_sup]) rotate([-90, 0, 90]) fita_reta_gt2(comp_menor_tras);

// ========================================================
// 7. MOTOR NEMA 17 E ACOPLAMENTO FLEXÍVEL (EIXO X)
// ========================================================

ponta_cilindro_x = ponta_direita_x; // Usa a coordenada fixa calculada na Seção 4
pos_x_acoplamento = ponta_cilindro_x + 13.0; 

translate([pos_x_acoplamento, pos_y_polia_frente, z_eixos_polias])
    rotate([0, -90, 0])
        acoplamento_flexivel();

pos_x_motor = pos_x_acoplamento + 45.0; // 44mm do corpo + 1mm de folga

translate([pos_x_motor, pos_y_polia_frente, z_eixos_polias])
    rotate([0, -90, 0])
        nema17();

// ========================================================
// 8. SUPORTE DE MADEIRA DO NEMA 17
// ========================================================
pos_x_suporte_nema = base_largura_x/2;
pos_y_suporte_nema = -base_comprimento_y/2;
pos_z_suporte_nema = z_eixos_polias - suporte_nema_altura/2;

color("#C68E58")
    translate([pos_x_suporte_nema, pos_y_suporte_nema, pos_z_suporte_nema])
        suporte_nema();

// ========================================================
// 9. CARRINHO DA CÂMERA (ESP32-CAM)
// ========================================================
// Instanciando o módulo que está salvo dentro de Carrinho_eixoY_2.scad
color("White")
    translate([0, 0, centro_z_tubo_x]) 
        rotate([0, 0, -90]) 
            translate([0, -car_esp32_comprimento/2, -car_esp32_altura/2])
                carrinho_eixo_y();

// ========================================================
// 10. SUPORTE POLIA LISA
// Fixado por baixo na travessa pequena do Eixo X (mesma travessa que
// segura o Suporte_Cano_X e o tubo_x), encostado na face de TRÁS do
// Suporte_Cano_X direito (lado voltado para o centro da maquete).
//
// CORREÇÃO: a face da FRENTE (X=230) não pode ser usada porque o
// Peca_Deslizante direito é espelhado (mirror([1,0,0]) na linha 31) e,
// por causa disso, sua aba se estende até X=230 - colocar a peça ali
// a cravava dentro do Peca_Deslizante. A face de trás (X=199) está livre.
// ========================================================
altura_suporte_polia_lisa     = 19.0; // alt_perna(15) + alt_barra(4.0) da peça
esp_suporte_polia_lisa        = 10.0; // esp (espessura em X) da peça
comp_barra_suporte_polia_lisa = 41.0; // comp_barra da peça (para centralizar em Y)

// Face da frente do Suporte_Cano_X direito (mesma fórmula da linha 43)
face_frente_suporte_cano_x_dir = base_largura_x/2 - pilar_lado/2 - bloco_largura/2 - 15;
// Profundidade interna do Suporte_Cano_X (copo_profundidade=25 + espessura_parede=6,
// medidas internas do módulo em pecas_moveis.scad) - dá a posição da face de trás
profundidade_suporte_cano_x = 31.0;
face_tras_suporte_cano_x_dir = face_frente_suporte_cano_x_dir - profundidade_suporte_cano_x;

afastamento_suporte_polia_lisa = 10.0; // 1cm de folga entre a peça nova e o Suporte_Cano_X

pos_x_suporte_polia_lisa = face_tras_suporte_cano_x_dir - afastamento_suporte_polia_lisa - esp_suporte_polia_lisa;
pos_y_suporte_polia_lisa = -comp_barra_suporte_polia_lisa / 2; // centralizada em Y=0
// Mesma face Z inferior da travessa pequena do Eixo X (antes do pezinho_altura_z
// usado pelo Suporte_Cano_X) - encosta o topo da barra na madeira
pos_z_suporte_polia_lisa = (pilar_altura_z - furo_offset_z + bloco_altura/2) - altura_suporte_polia_lisa;

color("White")
    translate([pos_x_suporte_polia_lisa, pos_y_suporte_polia_lisa, pos_z_suporte_polia_lisa])
        Suporte_Polia_Lisa();

// --- Pino usinado + Polia lisa GT2, encaixados nas pernas do Suporte_Polia_Lisa ---
// Medidas locais replicadas do módulo Suporte_Polia_Lisa (pecas_moveis.scad) para
// posicionar o pino e a polia exatamente no vão entre as pernas
larg_perna_spl       = 6.0;
alt_perna_spl        = 15.0;
eixo_pino_d_spl      = 5.0;
polia_largura_eixo_spl = 8.6;
folga_vao_polia_spl  = 2.5;
vao_livre_polia_spl  = polia_largura_eixo_spl + (2 * folga_vao_polia_spl);
bloco_pernas_largura_spl = (larg_perna_spl * 2) + vao_livre_polia_spl;
perna1_y_spl = (comp_barra_suporte_polia_lisa / 2) - (bloco_pernas_largura_spl / 2);
perna2_y_spl = perna1_y_spl + larg_perna_spl + vao_livre_polia_spl;
furo_perna_z_spl = 5.0;
furo_perna_x_spl = esp_suporte_polia_lisa / 2;

// pino: atravessa as duas pernas de ponta a ponta (embutido, colado)
pino_spl_y_inicio    = perna1_y_spl;
pino_spl_comprimento = (perna2_y_spl + larg_perna_spl) - perna1_y_spl;

// polia: centralizada no vão livre entre as pernas
gap_spl_inicio_y   = perna1_y_spl + larg_perna_spl;
polia_spl_y_inicio = gap_spl_inicio_y + folga_vao_polia_spl;

color("Silver")
    translate([pos_x_suporte_polia_lisa + furo_perna_x_spl, pos_y_suporte_polia_lisa + pino_spl_y_inicio, pos_z_suporte_polia_lisa + furo_perna_z_spl])
        rotate([-90, 0, 0])
            cylinder(d = eixo_pino_d_spl, h = pino_spl_comprimento);

translate([pos_x_suporte_polia_lisa + furo_perna_x_spl, pos_y_suporte_polia_lisa + polia_spl_y_inicio, pos_z_suporte_polia_lisa + furo_perna_z_spl])
    rotate([-90, 0, 0])
        polia_lisa_gt2_6mm();
// ========================================================
// 11. SUPORTE NEMA17 DO EIXO Y (correia direta no eixo do motor)
// Espelhado em X em relacao ao Suporte_Polia_Lisa (Secao 10); mesma
// altura (Z) e profundidade (Y=0) do eixo da polia lisa.
// ========================================================
pos_x_nema_eixo_y = -(pos_x_suporte_polia_lisa + furo_perna_x_spl);
pos_y_nema_eixo_y = 0;
pos_z_nema_eixo_y = pos_z_suporte_polia_lisa + furo_perna_z_spl;

color("White")
    translate([pos_x_nema_eixo_y, pos_y_nema_eixo_y, pos_z_nema_eixo_y])
        Suporte_Nema_Eixo_Y();
