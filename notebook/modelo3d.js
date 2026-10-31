/*
 * Modelo do TCC: ATLAS CNC · Modelo 3D independente (sem bibliotecas ou chamadas externas).
 * Modelo parametrico atualizado com medidas observadas nas fotos da montagem (22/10/2026)
 * e referencia de componentes a partir do OpenSCAD original:
 * config.scad, estrutura.scad, main_2.scad, pecas_moveis.scad e carrinho.
 * Representa madeira, area cultivada, tubos PVC, correias, travessa
 * deslizante e suporte da ESP32-CAM. Nao e malha CAD exata nem sensor.
 * Projecao local Canvas 2D sem dependencias externas; nunca controla motores.
 */
'use strict';
window.Atlas3D = (() => {
  const canvas = document.getElementById('model3dCanvas');
  if (!canvas) return {render(){}, control(){}};
  const ctx = canvas.getContext('2d');
  if (!ctx) return {render(){}, control(){}};
  const V = (x,y,z) => [x,y,z];
  const add = (a,b) => [a[0]+b[0],a[1]+b[1],a[2]+b[2]];
  const sub = (a,b) => [a[0]-b[0],a[1]-b[1],a[2]-b[2]];
  const mul = (a,k) => [a[0]*k,a[1]*k,a[2]*k];
  const dot = (a,b) => a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
  const cross = (a,b) => [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
  const norm = (a) => {const l=Math.hypot(...a)||1;return mul(a,1/l);};
  const clamp = (x,a,b) => Math.min(b,Math.max(a,x));

  // Camera padrao olhando da FRENTE (Y menor) para o FUNDO (Y maior).
  // A orientacao dos motores e a telemetria nao sao alteradas.
  const DEFAULT_ORBIT = Object.freeze({az: 0.70, elev:0.63, zoom:1.0});
  let orbit = {...DEFAULT_ORBIT};
  let state=null, points=[], preview=null;
  let pointer=null, resizeObserver=null;

  const camera = (width,height) => {
    const target=V(0,0,.61);
    const radius=7.7/orbit.zoom;
    const eye=add(target,V(radius*Math.cos(orbit.elev)*Math.sin(orbit.az),
                     -radius*Math.cos(orbit.elev)*Math.cos(orbit.az),
                     radius*Math.sin(orbit.elev)));
    const forward=norm(sub(target,eye)), right=norm(cross(forward,V(0,0,1)));
    const up=norm(cross(right,forward));
    const f=Math.min(width*1.15,height*2.25);
    return {width,height,eye,forward,right,up,f};
  };
  function project(cam,p){
    const rel=sub(p,cam.eye),depth=dot(rel,cam.forward);
    if(depth<=.2)return null;
    return {x:cam.width*.50+dot(rel,cam.right)*cam.f/depth,
            y:cam.height*.49-dot(rel,cam.up)*cam.f/depth,
            depth};
  }
  function boxFaces(center,dims,base,edge='#41647a') {
    const [cx,cy,cz]=center, [dx,dy,dz]=dims;
    const x=dx/2,y=dy/2,z=dz/2;
    const corners=[V(cx-x,cy-y,cz-z),V(cx+x,cy-y,cz-z),V(cx+x,cy+y,cz-z),V(cx-x,cy+y,cz-z),
                   V(cx-x,cy-y,cz+z),V(cx+x,cy-y,cz+z),V(cx+x,cy+y,cz+z),V(cx-x,cy+y,cz+z)];
    const faces=[[[0,3,2,1],.47],[[4,5,6,7],1],[[0,1,5,4],.77],[[1,2,6,5],.66],[[2,3,7,6],.54],[[3,0,4,7],.80]];
    return faces.map(([idx,light])=>({kind:'face',v:idx.map(i=>corners[i]),color:base,light,edge}));
  }
  function line(a,b,color='#3b667d',width=1,dash=null){return {kind:'line',v:[a,b],color,width,dash};}
  function circle(p,color,radius=5,number=''){return {kind:'circle',v:[p],color,radius,number};}
  function text(p,value,color='#93b3cd'){return {kind:'label',v:[p],color,value};}
  function shade(rgb,f){
    const v=rgb.match(/^#([0-9a-fA-F]{6})$/);if(!v)return rgb;
    const n=parseInt(v[1],16);
    const components=[(n>>16)&255,(n>>8)&255,n&255].map(c=>Math.round(clamp(c*f,0,255)));
    return `rgb(${components.join(',')})`;
  }
  // Medidas da montagem observadas nas fotos: canteiro 300x830, travessa ~390,
  // guia longitudinal ~1000 e carro ~80 mm. As outras cotas sao ESQUEMATICAS.
  // cursoX/cursoY sao apenas faixa visual estimada e NAO limites reais de firmware.
  // 1 unidade visual = 250 mm.
  const CAD = Object.freeze({
    baseX:440,baseY:1060,baseZ:30,areaX:410,areaY:1000,
    canteiroX:300,canteiroY:830,
    pilar:30,pilarH:300,pvcD:20,pvcY:1000,pvcX:390,
    trilhoYx:185,trilhoYz:275,trilhoXz:251.35,
    carroYcomp:90,carroYlarg:40,carroYaltura:45,
    carroCamComp:80,carroCamAlt:40,cursoX:310,cursoY:900
  });
  const mm = n => n / 250;
  const M = (x,y,z) => V(mm(x),mm(y),mm(z));
  function cylinderFaces(start,end,radius,color,edge='#52677e',sides=12){
    // Cilindro faceteado acompanhando o eixo entre duas coordenadas CAD.
    const axis=norm(sub(end,start));
    const basis=norm(cross(axis,Math.abs(axis[2])>.91?V(0,1,0):V(0,0,1)));
    const second=norm(cross(axis,basis));
    const ring=(o,i)=>add(o,add(mul(basis,Math.cos(i*2*Math.PI/sides)*radius),
                                  mul(second,Math.sin(i*2*Math.PI/sides)*radius)));
    const result=[];
    for(let i=0;i<sides;i++){
      const a=ring(start,i),b=ring(start,i+1),c=ring(end,i+1),d=ring(end,i);
      result.push({kind:'face',v:[a,b,c,d],color,light:.70+.26*Math.sin(i*2*Math.PI/sides),edge});
    }
    result.push({kind:'face',v:Array.from({length:sides},(_,i)=>ring(start,sides-i)),color,light:.73,edge});
    result.push({kind:'face',v:Array.from({length:sides},(_,i)=>ring(end,i)),color,light:1.07,edge});
    return result;
  }
  function emitScene(s,route){
    const solids=[], overlays=[];
    const B=(center,size,col,edge)=>solids.push(...boxFaces(M(...center),M(...size),col,edge));
    const C=(start,end,r,col,edge,n)=>solids.push(...cylinderFaces(M(...start),M(...end),mm(r),col,edge,n));
    const L=(a,b,col,width,dash)=>overlays.push(line(M(...a),M(...b),col,width,dash));
    const P=(p,col,r=6,label='')=>overlays.push(circle(M(...p),col,r,label));
    const T=(p,label,col)=>overlays.push(text(M(...p),label,col));
    const timber='#c68e58', timberEdge='#855e3d', pvc='#927b60', steel='#b2bbbf', white='#e1e5e6';

    // Base de madeira, leito verde e faixa de terra (main_2.scad).
    B([0,0,-15],[CAD.baseX,CAD.baseY,CAD.baseZ],timber,timberEdge);
    B([0,0,15],[CAD.areaX,CAD.areaY,30],'#4caf50','#28744a');
    B([0,0,30.7],[CAD.canteiroX,CAD.canteiroY,1.4],'#a0785a','#7d5a46');
    // Fileiras ilustrativas do cultivo (nao constam no arquivo CAD).
    for (const xx of [-120,-60,0,60,120]){
      for(let yy=-370;yy<=370;yy+=74){
        C([xx,yy,31],[xx,yy,38],3.4,'#78ca6e','#439352',6);
      }
    }
    // Quatro pilares 30x30x300 e travessas fixas superiores.
    for(const x of [-205,205]){
      for(const y of [-515,515]) B([x,y,150],[30,30,300],timber,timberEdge);
    }
    for(const y of [-515,515]) B([0,y,315],[440,30,30],timber,timberEdge);
    // Guias longitudinais de PVC diametro 20, origem -515 a 515 em Y.
    for(const x of [-185,185]){
      C([x,-500,CAD.trilhoYz],[x,500,CAD.trilhoYz],10,pvc,'#675442',12);
    }

    // A corrida real precisa ser calibrada em hardware; o modelo usa
    // coordenadas logicas 0..xmax/ymax e area fisica interna do CAD.
    const maxX=Math.max(1,Number(s?.xmax)||1640),maxY=Math.max(1,Number(s?.ymax)||4550);
    const hasPos=!!s?.arduino && Number.isFinite(Number(s?.x)) && Number.isFinite(Number(s?.y));
    // X segue o tubo transversal. Y desliza ao longo dos tubos laterais.
    const X=v=>-CAD.cursoX/2+clamp(Number(v)/maxX,0,1)*CAD.cursoX;
    // Orientacao visual da montagem: HOME/Y=0 na frente (-Y), MAX/Y=maxY atras (+Y).
    // Aplica-se ao carrinho real, previa MAX e TODOS os pontos do percurso.
    const Y=v=>-CAD.cursoY/2+clamp(Number(v)/maxY,0,1)*CAD.cursoY;
    const visualMax=preview==='max';
    // Os dois limites do desenho permanecem fixos mesmo com o Arduino offline.
    const homeVisualY=Y(0),maxVisualY=Y(maxY);
    const px=visualMax?X(maxX):(hasPos?X(s.x):0),py=visualMax?Y(maxY):(hasPos?Y(s.y):0);

    // Eixo X no CAD e o movimento transversal da ESP32-CAM.
    // O conjunto movel do eixo Y carrega travessa X e suportes.
    for(const x of [-185,185]){
      // Peca_Deslizante: bloco 40x90x45 e abas laterais impressas.
      B([x,py,275],[40,90,45],white,'#92a8b4');
      B([x,py,294],[70,90,10],'#d0d9db','#8195a8');
      // Passagem da correia sobre a peca.
      B([x,py,305],[11,85,3],'#313a44','#485461');
    }
    // Travessa de madeira transportada pelos carros laterais.
    B([0,py,319],[400,42,45],timber,timberEdge);
    // Cano transversal de PVC do X a z=251.35 mm.
    C([-195,py,CAD.trilhoXz],[195,py,CAD.trilhoXz],10,pvc,'#675442',14);
    // Suportes de ambas as extremidades do tubo.
    for(const x of [-182,182]){
      B([x,py,281],[35,31,50],white,'#9aabb9');
    }
    // Conjunto motor/polia simplificado; motores no CAD usam NEMA 17.
    B([245,-530,258],[43,43,43],'#343a42','#697884');
    C([222,-530,258],[202,-530,258],3,steel,'#77868d',10);
    B([-145,py,272],[42,42,42],'#333b49','#80909d');
    C([-125,py,272],[-110,py,272],3,steel,'#77868d',10);
    // Correias dos dois lados, nas guias longitudinais.
    for(const x of [-214,214]){
      C([x,-505,255],[x,-490,255],7,'#a1b2bc','#677984',12);
      C([x,490,255],[x,505,255],7,'#a1b2bc','#677984',12);
      L([x,-500,260],[x,500,260],'#151b23',3);
      L([x,-500,252],[x,py-35,252],'#111721',2);
      L([x,py+35,252],[x,500,252],'#111721',2);
    }
    // Carrinho do eixo X para a ESP32-CAM: 40x70x40,
    // com abracadeiras inferiores de 16mm (Carrinho_eixoY_2.scad).
    B([px,py,251],[CAD.carroCamComp,40,40],'#f2f6f6','#8f9fac');
    for(const dx of [-25,25]) B([px+dx,py,229],[8,35,16],'#e5eaef','#9fadb9');
    // ESP32-CAM montada abaixo do carrinho (simplificacao visual).
    B([px,py,216],[27,27,2],'#187b68','#114a44');
    B([px,py,209],[18,18,9],'#172c39','#3a91a1');
    C([px,py,203],[px,py,197],6,'#34799a','#76cad6',10);

    // Referencias da orientacao real: fundo da maquina e o MAX do eixo Y.
    // Estas marcas sao APENAS VISUAIS, nao enviam comandos nem recalibram eixos.
    L([-CAD.cursoX/2,maxVisualY,340],[CAD.cursoX/2,maxVisualY,340],'#ffd27c',3);
    T([0,maxVisualY+52,380],'FUNDO · MAX X','#ffe1a3');
    T([0,homeVisualY-52,380],'FRENTE · HOME X=0','#a9d8ff');
    // Localizador do canto MAX X/Y (fundo, extremidade transversal).
    P([X(maxX),maxVisualY,365],'#ffbf5c',7);
    T([X(maxX),maxVisualY,413],'MAX X/Y','#ffdb93');

    // Roteiro e pontos projetados na superficie fotografada.
    if(Array.isArray(route) && route.length){
      route.forEach((p,i)=>{
        const loc=[X(p.x),Y(p.y),34];
        if(i){const prev=route[i-1];L([X(prev.x),Y(prev.y),34],loc,'#46d9cd',2.7,[5,5]);}
        P(loc,p.p?'#65e1b8':'#ffca7f',i<16?6:4,i<16?String(i+1):'');
      });
    }
    if(hasPos || visualMax){
      P([px,py,35],'#91c5ff',8);
      L([px,py,195],[px,py,36],'#85b9ff',1.5,[3,4]);
      T([px,py,380],visualMax?`PRÉVIA MAX NO FUNDO · Y ${maxX} · X ${maxY}`:`Y ${Math.trunc(s.x)} · X ${Math.trunc(s.y)}`,visualMax?'#ffd783':'#e5f8ff');
    }
    T([210,-550,0],'Y +','#82bafe');
    T([-230,550,0],'X + (FUNDO)','#80d7c1');
    T([-235,-540,355],'Z ↑','#b9c8dc');
    return {solids,overlays,hasPos,pointCount:route.length};
  }
  function render(newState=state,newRoute=points,newPreview=preview){
    state=newState;points=Array.isArray(newRoute)?newRoute:[];preview=newPreview;
    if(canvas.hidden || !canvas.isConnected)return;
    const rect=canvas.getBoundingClientRect();const w=rect.width,h=rect.height;
    if(w<5||h<5)return;
    const dpr=Math.min(window.devicePixelRatio||1,2),W=Math.round(w*dpr),H=Math.round(h*dpr);
    if(canvas.width!==W||canvas.height!==H){canvas.width=W;canvas.height=H;}
    ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
    const cam=camera(w,h);
    // Luz de fundo para ajudar a leitura do volume.
    const grad=ctx.createRadialGradient(w*.50,h*.42,6,w*.5,h*.48,Math.max(w,h)*.70);
    grad.addColorStop(0,'#173950');grad.addColorStop(1,'#0b1425');
    ctx.fillStyle=grad;ctx.fillRect(0,0,w,h);
    const scene=emitScene(state,points);
    const prepared=[];
    for(const primitive of scene.solids){
      const ps=primitive.v.map(p=>project(cam,p));if(ps.some(p=>!p))continue;
      const depth=ps.reduce((a,p)=>a+p.depth,0)/ps.length;
      prepared.push({...primitive,ps,depth});
    }
    // Ordenacao distante -> proximo para nao deixar travessas do fundo na frente.
    prepared.sort((a,b)=>b.depth-a.depth);
    ctx.lineJoin='round';
    for(const p of prepared){
      ctx.beginPath();p.ps.forEach((v,i)=>i?ctx.lineTo(v.x,v.y):ctx.moveTo(v.x,v.y));ctx.closePath();
      ctx.fillStyle=shade(p.color,p.light);ctx.fill();ctx.lineWidth=.65;ctx.strokeStyle=p.edge;ctx.stroke();
    }
    // Guias e marcadores sao desenhados com prioridade visual para ensinar trajetos.
    for(const obj of scene.overlays){
      const ps=obj.v.map(p=>project(cam,p));if(ps.some(p=>!p))continue;
      if(obj.kind==='line'){
        ctx.beginPath();ctx.moveTo(ps[0].x,ps[0].y);ctx.lineTo(ps[1].x,ps[1].y);
        ctx.strokeStyle=obj.color;ctx.lineWidth=obj.width;ctx.setLineDash(obj.dash||[]);ctx.stroke();ctx.setLineDash([]);
      }else if(obj.kind==='circle'){
        const p=ps[0];ctx.beginPath();ctx.arc(p.x,p.y,obj.radius,0,Math.PI*2);
        ctx.fillStyle=obj.color;ctx.fill();ctx.lineWidth=1.5;ctx.strokeStyle='#102235';ctx.stroke();
        if(obj.number){ctx.font='bold 10px system-ui';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillStyle='#0b2130';ctx.fillText(obj.number,p.x,p.y+.2);}
      }else if(obj.kind==='label'){
        const p=ps[0];ctx.fillStyle=obj.color;ctx.font='bold 11px system-ui';ctx.textAlign='center';ctx.textBaseline='bottom';
        ctx.shadowColor='#07111e';ctx.shadowBlur=5;ctx.fillText(obj.value,p.x,p.y-3);ctx.shadowBlur=0;
      }
    }
    if(preview==='max'){
      ctx.fillStyle='#ffd783';ctx.font='bold 13px system-ui';ctx.textAlign='left';
      ctx.fillText('PRÉVIA MAX: FUNDO DA MAQUETE · SOMENTE 3D',14,h-64);
      ctx.font='11px system-ui';ctx.fillText('A máquina física não se moveu',14,h-46);
    }
    if(!scene.hasPos && preview!=='max'){
      ctx.fillStyle='#d3dce7';ctx.font='600 12px system-ui';ctx.textAlign='left';
      ctx.fillText('Sem telemetria do Arduino · posição ilustrativa',14,h-60);
    }
    ctx.fillStyle='#9bb8ce';ctx.font='11px system-ui';ctx.textAlign='left';
    ctx.fillText('Canteiro: 300 × 830 mm · travessa: ~390 mm',14,24);
    ctx.fillText('Posição virtual estimada · não mede centro físico',14,40);
  }
  function control(action){
    if(action==='reset')orbit={...DEFAULT_ORBIT};
    else if(action==='zoom-in')orbit.zoom=clamp(orbit.zoom*1.18,.55,2.3);
    else if(action==='zoom-out')orbit.zoom=clamp(orbit.zoom/1.18,.55,2.3);
    render();
  }
  canvas.addEventListener('pointerdown',e=>{
    if(e.button!==0)return;
    pointer={id:e.pointerId,x:e.clientX,y:e.clientY};
    canvas.setPointerCapture(e.pointerId);
  });
  canvas.addEventListener('pointermove',e=>{
    if(!pointer || pointer.id!==e.pointerId)return;
    const dx=e.clientX-pointer.x,dy=e.clientY-pointer.y;
    pointer.x=e.clientX;pointer.y=e.clientY;
    orbit.az+=dx*.008;
    orbit.elev=clamp(orbit.elev+dy*.006,.12,1.37);
    render();
  });
  function endDrag(e){if(pointer?.id===e.pointerId)pointer=null;}
  canvas.addEventListener('pointerup',endDrag);
  canvas.addEventListener('pointercancel',endDrag);
  canvas.addEventListener('lostpointercapture',()=>{pointer=null;});
  canvas.addEventListener('wheel',e=>{
    if(canvas.hidden)return;
    e.preventDefault();orbit.zoom=clamp(orbit.zoom*Math.exp(-e.deltaY*.0013),.55,2.3);render();
  },{passive:false});
  canvas.addEventListener('dblclick',()=>control('reset'));
  if(typeof ResizeObserver!=='undefined'){
    resizeObserver=new ResizeObserver(()=>render());resizeObserver.observe(canvas);
  }
  return {render,control};
})();
