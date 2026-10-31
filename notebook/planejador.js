'use strict';
/* Geração local de roteiros: somente calcula coordenadas; NÃO transmite movimentos. */
(function(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.AtlasPlanner = api;
})(typeof window !== 'undefined' ? window : null, function() {
  const MODES = Object.freeze({
    snakeRows: 'Zigue-zague por linhas',
    snakeCols: 'Zigue-zague por colunas',
    rows: 'Linhas em sentido único',
    cols: 'Colunas em sentido único',
    spiral: 'Espiral retangular',
    perimeter: 'Perímetro (somente bordas)'
  });
  function integer(n, name) {
    const value = Number(n);
    if (!Number.isSafeInteger(value)) throw new Error(`${name}: use um número inteiro de passos.`);
    return value;
  }
  // Pontos equiespaçados, incluindo ambas as extremidades e sem exceder o salto desejado.
  function positions(start, finish, spacing) {
    if(start===finish) return [start];
    const count=Math.ceil((finish-start)/spacing);
    const result=[];
    for(let i=0;i<=count;i++) result.push(Math.round(start+(finish-start)*i/count));
    return [...new Set(result)];
  }
  function spiralOrder(nx,ny) {
    const cells=[]; let l=0,r=nx-1,t=0,b=ny-1;
    while(l<=r&&t<=b){
      for(let x=l;x<=r;x++)cells.push([x,t]);t++;
      for(let y=t;y<=b;y++)cells.push([r,y]);r--;
      if(t<=b){for(let x=r;x>=l;x--)cells.push([x,b]);b--;}
      if(l<=r){for(let y=b;y>=t;y--)cells.push([l,y]);l++;}
    }
    return cells;
  }
  function build(config) {
    const mode=String(config.mode);
    if(!Object.hasOwn(MODES,mode)) throw new Error('Método de varredura não reconhecido.');
    const limitsX=integer(config.limitX,'Limite X'), limitsY=integer(config.limitY,'Limite Y');
    if(limitsX<=0||limitsY<=0)throw new Error('Limites de X/Y inválidos.');
    const x0=integer(config.x0,'X inicial'), x1=integer(config.x1,'X final');
    const y0=integer(config.y0,'Y inicial'), y1=integer(config.y1,'Y final');
    if(x0<0||x1>limitsX||y0<0||y1>limitsY||x1<x0||y1<y0)throw new Error('A área deve ficar entre 0 e os limites programados, com início menor ou igual ao final.');
    const footprintX=integer(config.footprintX,'Cobertura X'),footprintY=integer(config.footprintY,'Cobertura Y');
    const overlap=Number(config.overlap);
    if(footprintX<1||footprintY<1||!Number.isFinite(overlap)||overlap<0||overlap>70)throw new Error('Informe cobertura positiva e sobreposição de 0% a 70%.');
    const spacingX=Math.max(1,Math.floor(footprintX*(1-overlap/100)));
    const spacingY=Math.max(1,Math.floor(footprintY*(1-overlap/100)));
    let xs=positions(x0,x1,spacingX),ys=positions(y0,y1,spacingY);
    if(config.flipX)xs=xs.slice().reverse();
    if(config.flipY)ys=ys.slice().reverse();
    const nx=xs.length,ny=ys.length;
    const capacity=mode==='perimeter'?(nx===1||ny===1?nx*ny:2*nx+2*ny-4):nx*ny;
    if(capacity>48)throw new Error(`A configuração produziria ${capacity} pontos (máximo: 48). Aumente a cobertura em passos, reduza a área ou diminua a sobreposição.`);
    const cells=[];
    if(mode==='snakeRows'||mode==='rows'){
      for(let y=0;y<ny;y++){
        const xx=[...Array(nx).keys()];if(mode==='snakeRows'&&y%2)xx.reverse();
        for(const x of xx)cells.push([x,y]);
      }
    }else if(mode==='snakeCols'||mode==='cols'){
      for(let x=0;x<nx;x++){
        const yy=[...Array(ny).keys()];if(mode==='snakeCols'&&x%2)yy.reverse();
        for(const y of yy)cells.push([x,y]);
      }
    }else if(mode==='spiral'){
      cells.push(...spiralOrder(nx,ny));
    }else if(mode==='perimeter'){
      if(nx===1||ny===1){for(let y=0;y<ny;y++)for(let x=0;x<nx;x++)cells.push([x,y]);}
      else{
        for(let x=0;x<nx;x++)cells.push([x,0]);
        for(let y=1;y<ny;y++)cells.push([nx-1,y]);
        for(let x=nx-2;x>=0;x--)cells.push([x,ny-1]);
        for(let y=ny-2;y>0;y--)cells.push([0,y]);
      }
    }
    const points=cells.map(([x,y])=>({x:xs[x],y:ys[y],p:true}));
    if(points.length>48)throw new Error('Limite de 48 pontos excedido.');
    if(new Set(points.map(p=>p.x+','+p.y)).size!==points.length)throw new Error('O percurso calculado contém posições duplicadas.');
    return {points, rows:ny, cols:nx, spacingX, spacingY, mode, perimeterOnly: mode==='perimeter'};
  }
  return {MODES, build};
});
