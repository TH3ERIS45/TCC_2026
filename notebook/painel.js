'use strict';
(() => {
  const $ = (id) => document.getElementById(id);
  const $$ = (query) => Array.from(document.querySelectorAll(query));
  const pages = {dashboard:'Início',movement:'Controle',route:'Mapeamento',camera:'Resultados',diagnostics:'Diagnóstico'};
  const uiModeKey='atlas-cnc-ui-mode-v4';
  let uiMode='simple';
  let state = null, route = [], dirty = false, statusBusy = false, commandBusy = false;
  let lastOk = null, lastError = '', lastEvent = '', mapMode = '2d';
  let lastGallery = [], loadedRoute = false, currentView = 'dashboard';
  let liveOn = false, liveGotFrame = false;
  let flashBusy=false;
  let maxPreview = false; // Apenas desenho; nunca enviar comando de movimento neste modo.
  let geoCenter=null; // Passos calibrados no notebook; nao sao limites mecanicos.

  let teachMotionPending = false, teachMarkPending = false;
  let holdJog = null, holdStopPending = false, holdPingBusy = false;
  const MAX_MANUAL_STEPS=5000;

  let plannerDraft = null, plannerConfigHash = null, plannerLimitsLoaded = false;
  const logRows = [];
  const now = () => new Date().toLocaleTimeString('pt-BR', {hour12:false});
  const int = (n) => Number.isSafeInteger(Number(n)) ? Number(n) : NaN;
  const mmX = (x) => x * 328 / (state?.xmax || 1640);
  const mmY = (y) => y * 910 / (state?.ymax || 4550);
  const mmFmt = (n) => Number.isFinite(n) ? n.toFixed(2) + ' mm' : '— mm';

  function log(text, kind='info') {
    const line = {time:now(), text:String(text), kind};
    logRows.unshift(line); if (logRows.length>140) logRows.pop();
    const consoleEl = $('logOutput'); consoleEl.replaceChildren();
    for (const item of logRows) {
      const d=document.createElement('div');d.className='log-'+item.kind;
      const clock=document.createElement('span');clock.className='log-time';clock.textContent='['+item.time+'] ';
      d.append(clock,document.createTextNode(item.text));consoleEl.append(d);
    }
  }
  function toast(text, type='info') {
    const n=document.createElement('div');n.className='toast '+type;n.textContent=String(text);$('toastWrap').prepend(n);
    setTimeout(() => n.remove(),5500);
  }
  function fail(err, prefix='Falha') { const msg=prefix+': '+(err?.message||String(err));log(msg,'error');toast(msg,'error'); }
  function liveLabel(label) {setText('liveStatus',label);}
  function stopLive(reason='Desligado') {
    liveOn=false;liveGotFrame=false;
    const img=$('liveImage'); img.removeAttribute('src'); img.hidden=true; $('liveStage').hidden=true;
    $('livePlaceholder').hidden=false;
    $('liveStart').disabled=false;$('liveStop').disabled=true;
    $('liveGridOverlay').hidden=true;
    liveLabel(reason);
  }
  function startLive() {
    if (liveOn) return;
    if (!state || state.camera_ok===false) {toast('ESP32-CAM ou câmera offline. Confira Diagnóstico.','error');return;}
    if (state.active || state.stage!=='PARADO' || state.photo_lock) {
      toast('Aguarde a conclusão do roteiro ou da foto pendente para iniciar o vídeo.','error');return;
    }
    liveOn=true;liveGotFrame=false;
    $('liveStart').disabled=true;$('liveStop').disabled=false;
    $('livePlaceholder').hidden=false;
    liveLabel('Conectando...');
    const img=$('liveImage');img.hidden=false;$('liveStage').hidden=false;$('livePlaceholder').hidden=true;
    // Mesmo dominio do painel. O Flask injeta a chave no proxy, nao no navegador.
    img.src='/api/camera/stream?t='+Date.now();
    refreshLiveGrid();
  }
  function refreshLiveGrid() {
    $('liveGridOverlay').hidden=!(liveOn && $('liveGrid').checked);
  }
  function liveFrameReceived() {
    if(!liveOn)return;
    liveGotFrame=true;
    $('liveImage').hidden=false;$('livePlaceholder').hidden=true;
    liveLabel('Ao vivo');refreshLiveGrid();
  }
  function liveFrameError() {
    if(!liveOn)return;
    stopLive('Falha na transmissão');
    toast('Não foi possível abrir o stream. Confira firmware atualizado, rede e porta 81.','error');
  }
  async function loadGeometry(){
    try{
      const r=await fetch('/api/geometria',{cache:'no-store'});
      if(!r.ok)throw new Error('HTTP '+r.status);
      const cfg=await r.json();
      geoCenter=cfg?.centro ?? null;
      updateGeometryPanel();
    }catch(err){
      geoCenter=null;
      setText('geomCenterStatus','Sem acesso à calibração do centro: '+err.message);
      $('geomGoCenter').disabled=true;
    }
  }
  function updateGeometryPanel(){
    const valid=geoCenter && Number.isSafeInteger(geoCenter.x_steps) && Number.isSafeInteger(geoCenter.y_steps)
      && geoCenter.x_steps>=0 && geoCenter.y_steps>=0;
    const inside=valid && state?.arduino && geoCenter.x_steps<=state.xmax && geoCenter.y_steps<=state.ymax;
    const checked=$('geomReferenceCheck').checked;
    setText('geomCenterStatus',valid
      ?`Centro ensinado: X=${geoCenter.x_steps}, Y=${geoCenter.y_steps} passos. ${inside?'Dentro dos limites atuais.':'Aguardando ou fora dos limites do Arduino.'}`
      :'Centro físico ainda não ensinado. Posicione a lente e guarde a coordenada.');
    $('geomMarkCenter').disabled=!canTeach();
    $('geomGoCenter').disabled=!(inside && checked && isIdle() && state?.enabled && state.home_x && state.home_y && !commandBusy);
  }
  async function teachPlotCenter(){
    if(!canTeach()){
      toast('Para ensinar o centro, confirme HOME, ative drivers e aguarde a parada.','error');return;
    }
    if(!confirm('A lente está FISICAMENTE sobre o centro do canteiro de 30 × 83 cm?\n\nGuardar a posição X/Y atual SEM mover a máquina?'))return;
    try{
      const v=await settledPosition();
      const body={x_steps:v.x,y_steps:v.y};
      const r=await fetch('/api/geometria',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      const response=await r.json();
      if(!r.ok)throw new Error(response.error||'Não salvou');
      geoCenter=response.centro;
      $('geomReferenceCheck').checked=true;
      updateGeometryPanel();
      toast(`Centro da plantação salvo em X=${v.x}, Y=${v.y}. Sem movimento.`, 'success');
    }catch(err){fail(err,'Falha ao salvar centro da plantação');}
  }
  async function goPlotCenter(){
    if(!requireReady(true))return;
    let fresh;
    try{fresh=await freshPosition();}
    catch(err){fail(err,'Não foi possível confirmar a posição antes da centralização');return;}
    if(!geoCenter || !Number.isSafeInteger(geoCenter.x_steps) || !Number.isSafeInteger(geoCenter.y_steps)){
      toast('Ensine o centro do canteiro antes de mover.','error');return;
    }
    if(!$('geomReferenceCheck').checked){toast('Confirme o HOME físico atual antes de mover.','error');return;}
    const {x_steps:x,y_steps:y}=geoCenter;
    if(x<0||y<0||x>fresh.xmax||y>fresh.ymax || !fresh.home_x || !fresh.home_y || !fresh.enabled || fresh.moving || fresh.active || fresh.photo_lock || fresh.stage!=='PARADO'){
      toast('Centro salvo fora dos limites ou máquina não está pronta.','error');return;
    }
    await command(`MOVE X ${x} Y ${y}`,{confirmText:`CENTRO REAL DO CANTEIRO (ENSINADO)

Destino X=${x}, Y=${y} passos.

O HOME físico é o mesmo de quando a posição foi ensinada? O curso está livre e a escala foi verificada? Sem sensores, referência errada pode causar colisão.`});
  }
  function invalidateCenterCheck(){
    $('geomReferenceCheck').checked=false;
    updateGeometryPanel();
  }

  function setUiMode(mode) {
    uiMode=mode==='advanced'?'advanced':'simple';
    document.body.dataset.uiMode=uiMode;
    $$('[data-ui-switch]').forEach(btn=>{
      const on=btn.dataset.uiSwitch===uiMode;
      btn.classList.toggle('active',on);btn.setAttribute('aria-pressed',String(on));
    });
    $('modeDescription').textContent=uiMode==='simple'
      ?'Operação diária, sem ajustes técnicos à vista.'
      :'Calibração, configuração e diagnóstico completos.';
    try{window.localStorage.setItem(uiModeKey,uiMode);}catch(_){}
    if(uiMode==='simple' && currentView==='diagnostics')navigate('dashboard');
    setPlannerExpanded(uiMode==='advanced');
    if(currentView==='dashboard')requestAnimationFrame(drawMap);
  }
  function setPlannerExpanded(expanded) {
    const details=$('plannerDetails');
    const btn=$('plannerExpand');
    details.hidden=!expanded;
    btn.setAttribute('aria-expanded',String(expanded));
    $('autoPlanner').classList.toggle('expanded',expanded);
    if(expanded)requestAnimationFrame(()=>drawPlanner(plannerDraft));
  }
  function navigate(view) {
    if (!pages[view]) return;
    if(view==='diagnostics' && uiMode==='simple')setUiMode('advanced');
    if(view!==currentView && holdJog) releaseHold('Mudanca de tela');
    if(view!==currentView && currentView==='movement' && liveOn)stopLive();
    currentView=view;$('pageTitle').textContent=pages[view];
    $$('.view').forEach(el=>el.classList.toggle('active',el.id==='view-'+view));
    $$('.nav-link').forEach(el=>el.classList.toggle('active',el.dataset.view===view));
    $('sidebar').classList.remove('open');
    if(view==='dashboard')requestAnimationFrame(drawMap);
    if(view==='camera'){refreshGallery();mosaicRefresh();}
  }
  async function esp(path,method='GET',data='',timeout=6500) {
    const ctl=new AbortController();const timer=setTimeout(()=>ctl.abort(),timeout);
    try {
      const opts={method,signal:ctl.signal,cache:'no-store'};
      if(method!=='GET') {opts.headers={'Content-Type':'text/plain'};opts.body=data;}
      const response=await fetch('/api/esp'+path,opts);
      const body=await response.text();
      if(!response.ok) throw new Error(body.trim()||('HTTP '+response.status));
      const type=response.headers.get('content-type')||'';
      if(type.includes('application/json')) return JSON.parse(body);
      return body;
    } finally { clearTimeout(timer); }
  }
  function isIdle() {return !!state && state.arduino && !state.moving && !state.active && !state.photo_lock && state.stage==='PARADO';}
  const pause = (ms) => new Promise(resolve=>setTimeout(resolve,ms));
  function canTeach() {return isIdle() && !!state?.home_x && !!state?.home_y && !!state?.enabled && !teachMotionPending && !teachMarkPending && !commandBusy;}
  async function freshPosition() {
    const next=await esp('/api/status','GET','',5000);
    if(!next || typeof next!=='object')throw new Error('Telemetria inválida.');
    state=next;lastOk=now();lastError='';updateScreen();
    return next;
  }
  async function waitForState(predicate,label,timeoutMs=5000){
    const until=Date.now()+timeoutMs;
    do{
      const observed=await freshPosition();
      if(predicate(observed))return observed;
      await pause(220);
    }while(Date.now()<until);
    throw new Error(label+' não foi confirmada pelo Arduino dentro do prazo.');
  }
  function safePosition(s) {return !!s && s.arduino && !s.moving && !s.active && !s.photo_lock && s.stage==='PARADO' && s.home_x && s.home_y && s.enabled && Number.isSafeInteger(s.x) && Number.isSafeInteger(s.y);}
  async function settledPosition() {
    // Dois estados iguais com intervalo: nunca registrar coordenadas de uma leitura isolada.
    let previous=null;
    for(let attempt=0;attempt<10;attempt++) {
      const v=await freshPosition();
      if(!safePosition(v))throw new Error('Arduino sem HOME, desconectado ou movimento/foto pendente.');
      if(previous && v.x===previous.x && v.y===previous.y)return v;
      previous=v;await pause(350);
    }
    throw new Error('Posição ainda instável. Aguarde a máquina parar.');
  }
  async function waitJogTarget(x,y,timeoutMs) {
    const end=Date.now()+timeoutMs;let confirmed=0;
    while(Date.now()<end) {
      await pause(350);
      const v=await freshPosition();
      if(!v.arduino || !v.home_x || !v.home_y || v.active || v.photo_lock || v.stage!=='PARADO')throw new Error('Perda de referência, conexão ou máquina ocupada durante o movimento.');
      if(!v.moving && v.x===x && v.y===y) {if(++confirmed>=2)return;} else confirmed=0;
    }
    throw new Error('Não foi possível confirmar a chegada ao destino. Confira a máquina antes de marcar ponto.');
  }
  async function jogTeach(axis,direction,delta) {
    if(teachMotionPending || teachMarkPending || commandBusy) {toast('Aguarde o movimento ou o registro do ponto atual.','error');return;}
    if(!requireReady(true))return;
    teachMotionPending=true;updateScreen();
    try {
      const before=await freshPosition();
      if(!safePosition(before))throw new Error('Confirme HOME, drivers e a máquina parada antes de mover.');
      const x=axis==='X'?Math.max(0,Math.min(before.xmax,before.x+direction*delta)):before.x;
      const y=axis==='Y'?Math.max(0,Math.min(before.ymax,before.y+direction*delta)):before.y;
      const result=await command(`JOG ${axis} ${direction*delta}`);
      if(result===false)return;
      const pps=Math.max(10,Number($('speedPps').value)||60);
      const realDistance=Math.abs(x-before.x)+Math.abs(y-before.y);
      await waitJogTarget(x,y,Math.min(600000,Math.max(10000,Math.ceil(realDistance/pps*1000)+10000)));
      log(`Movimento concluído em X=${x}, Y=${y}. Pode marcar este ponto.`,'ok');
    }catch(err){fail(err,'Movimento não confirmado');}
    finally {teachMotionPending=false;updateScreen();}
  }
  // JOG por pressao: comandos separados do JOG discreto. O Arduino impõe
  // watchdog proprio, mesmo se o navegador ou a ESP32 desaparecerem.
  function showHoldStatus(msg) {
    const el=$('holdJogStatus'); if(el)el.textContent=msg;
  }
  function releaseHold(reason='Botao solto') {
    const hold=holdJog;
    if(!hold || hold.released)return;
    hold.released=true;
    holdJog=null;
    if(hold.timer)clearInterval(hold.timer);
    hold.button.classList.remove('pressed-hold');
    holdStopPending=true;
    showHoldStatus('Parando... aguardando confirmacao do Arduino.');
    // Mesmo se o START ainda estiver em transito, envia STOP agora; a rotina
    // do START envia um segundo STOP se receber a resposta depois da soltura.
    (async()=>{
      try {
        // Rota de parada geral existe nas versões antigas da ESP32-CAM.
        // Não usar JOGSTOP em /api/command para evitar HTTP 409 se houver
        // incompatibilidade entre painel e firmware.
        await esp('/api/stop','POST','',2400);
        await waitForState(s=>s.arduino && !s.moving && !s.photo_lock,
                           'Parada do JOG',4200);
        showHoldStatus('Parado e confirmado. '+reason+'.');
      } catch(err) {
        fail(err,'Parada nao confirmada: confira a maquina');
        await esp('/api/stop','POST','',1800).catch(()=>{});
        showHoldStatus('ATENCAO: parada sem confirmacao. Verifique a posicao e a conexao antes de prosseguir.');
      } finally {
        teachMotionPending=false;
        holdStopPending=false;
        updateScreen();
      }
    })();
  }
  async function keepHoldAlive(hold) {
    if(hold!==holdJog || hold.released || !hold.started || holdPingBusy)return;
    holdPingBusy=true;
    try {await esp('/api/jog-ping','POST','',1400);}
    catch(err){if(hold===holdJog){fail(err,'Perda de sinal do JOG');releaseHold('Sinal interrompido');}}
    finally {holdPingBusy=false;}
  }
  async function beginHold(button,pointerId) {
    if(holdJog || holdStopPending || teachMotionPending || teachMarkPending || commandBusy)return;
    if(!requireReady(true))return;
    const [axis,dir]=button.dataset.jog.split(':');
    if(!['X','Y'].includes(axis) || !['1','-1'].includes(dir))return;
    const hold={button,pointerId,started:false,released:false,timer:null};
    holdJog=hold;
    teachMotionPending=true;
    button.classList.add('pressed-hold');
    showHoldStatus('Segurando '+axis+(dir==='1'?'+':'-')+' ...');
    updateScreen();
    try {
      // O texto fw_version da série GC2145 era igual antes/depois do JOG.
      // Verificar a capacidade explícita para impedir START em firmware antigo.
      const check=await freshPosition();
      if(check.jog_hold_supported!==true) {
        throw new Error('ESP32-CAM sem suporte a JOG contínuo. Atualize o firmware ESP32 do pacote e reinicie o painel.');
      }
      if(!safePosition(check)) throw new Error('Arduino sem HOME/drivers, ocupado ou desconectado.');
      if(hold.released) return;
      await esp('/api/command','POST',`JOGSTART ${axis} ${dir}`,2500);
      if(hold.released) {
        // Pode haver START em trânsito quando o botão foi solto.
        await esp('/api/stop','POST','',1800).catch(()=>{});
        return;
      }
      hold.started=true;
      // Primeiro heartbeat imediato, e depois a cada 250 ms.
      await keepHoldAlive(hold);
      if(!hold.released)hold.timer=setInterval(()=>keepHoldAlive(hold),250);
    } catch(err) {
      if(!hold.released){fail(err,'Nao foi possivel iniciar JOG continuo');releaseHold('Falha ao iniciar');}
    }
  }

  async function markCurrentPosition(photo) {
    if(teachMotionPending || teachMarkPending || commandBusy) {toast('Aguarde o movimento terminar antes de marcar.','error');return;}
    if(!canTeach()) {toast('Ative os drivers, confirme HOME X/Y e aguarde a máquina parar.','error');return;}
    teachMarkPending=true;updateScreen();
    try {
      const v=await settledPosition();
      if(!route.some(p=>p.x===v.x && p.y===v.y)) {
        addPoint(v.x,v.y,photo);
        log(`Ponto ensinado: X=${v.x}, Y=${v.y}, foto=${photo?'SIM':'NÃO'}`,'ok');
      } else toast(`Já existe um ponto em X=${v.x}, Y=${v.y}. Desloque a câmera para marcar outro.`, 'error');
    }catch(err){fail(err,'Não foi possível marcar o ponto');}
    finally {teachMarkPending=false;updateScreen();}
  }
  function requireReady(motion=false) {
    if(holdJog || holdStopPending) {toast('Aguarde a parada confirmada do JOG continuo.','error');return false;}
    if(!state){toast('ESP32-CAM sem resposta: confira Wi-Fi e IP no Diagnóstico.','error');return false;}
    if(!state.arduino){toast('Arduino sem telemetria UART: confira a ligação ESP32 ↔ Arduino.','error');return false;}
    if(state.photo_lock){toast('Movimento bloqueado por PHOTOACK pendente. Confira o ID da foto no Diagnóstico.','error');return false;}
    if(state.moving || state.active || state.stage!=='PARADO'){
      toast('A máquina não está parada. Estado atual: '+state.stage+'.','error');return false;
    }
    if(motion && (!state.home_x || !state.home_y)){
      toast('HOME não confirmado pelo Arduino: X='+!!state.home_x+', Y='+!!state.home_y+'. Confira a referência física.','error');return false;
    }
    if(motion && !state.enabled){toast('Drivers desligados segundo o Arduino. Clique em Ativar drivers e aguarde a confirmação.','error');return false;}
    return true;
  }
  function confirmacaoNecessaria(cmd){
    if(cmd==='HOME')return s=>s.arduino&&s.home_x&&s.home_y;
    if(cmd==='HOME X')return s=>s.arduino&&s.home_x;
    if(cmd==='HOME Y')return s=>s.arduino&&s.home_y;
    if(cmd==='UNHOME')return s=>s.arduino&&!s.home_x&&!s.home_y;
    if(cmd==='ENABLE 1')return s=>s.arduino&&s.enabled;
    if(cmd==='ENABLE 0')return s=>s.arduino&&!s.enabled&&!s.home_x&&!s.home_y;
    const match=/^SETPOS X (\d+) Y (\d+)$/.exec(cmd);
    if(match){const x=Number(match[1]),y=Number(match[2]);
      return s=>s.arduino&&s.x===x&&s.y===y&&!s.home_x&&!s.home_y;}
    return null;
  }
  async function send(path, data='', opts={}) {
    const {confirmText='',timeout=6500}=opts;
    if(commandBusy && path!=='/api/stop') {toast('Há outro comando pendente. Aguarde.','error');return false;}
    if(confirmText && !confirm(confirmText)) return false;
    if(path!=='/api/stop') commandBusy=true;
    try {
      log('→ '+path+(data?' · '+data:''));
      const result=await esp(path,'POST',data,timeout);
      log('✓ '+(typeof result==='string'?result:JSON.stringify(result)),'ok');
      if(path==='/api/command') {
        const confirmar=confirmacaoNecessaria(data);
        if(confirmar){
          await waitForState(confirmar,'Confirmacao de '+data,5000);
          toast('Arduino confirmou: '+data,'success');
        } else toast('Comando enviado; acompanhe a posicao real do Arduino.','info');
      } else if(path==='/api/stop'){
        await waitForState(s=>s.arduino&&!s.moving&&!s.active,'PARADA',5000);
        toast('Arduino reportou movimento parado. Confirme tambem visualmente.','success');
      } else toast(path==='/api/manual-photo'?'Foto salva no notebook.':'Solicitacao aceita.','success');
      await updateStatus(true);return result;
    } catch(err) {fail(err,'Comando não concluído');return false;}
    finally {if(path!=='/api/stop')commandBusy=false;}
  }
  async function command(text,options={}) {return send('/api/command',text,options);}
  function setText(id,text) {$(id).textContent=String(text);}
  function badge(el,good,text) {el.className='ref-badge '+(good?'good':'bad');el.textContent=text;}
  function connectionBadge(id,online,yes,no) {const el=$(id);el.className='mini-pill '+(online?'good':'bad');el.lastChild.textContent=' '+(online?yes:no);}
  function updateFlashPanel() {
    const supported=!!state?.flash_supported;
    for(const label of $$('[data-flash-status]')) {
      label.textContent=!state?'ESP32 offline':!supported?'Firmware antigo':state.flash_on?'LED ligado':'LED apagado';
    }
    for(const check of $$('[data-flash-auto]')) {
      check.checked=supported && !!state.flash_auto;
      check.disabled=flashBusy || !supported;
    }
    for(const btn of $$('[data-action="flash-on"],[data-action="flash-off"]')) {
      btn.disabled=flashBusy || !supported;
    }
    for(const label of $$('[data-flash-feedback]')) {
      if (!supported) {label.textContent='Flash indisponível: confira conexão e firmware FLASH-AUTO-MANUAL.';continue;}
      const bright=state.flash_last_brightness;
      label.textContent=(state.flash_auto?'Automático ativo. ':'Automático desligado. ')+
        (state.flash_manual?'Manual ligado (limite 60 s). ':'Manual desligado. ')+
        (bright>=0?'Brilho da última foto: '+bright+'/255. ':'')+
        'Última foto com LED: '+(state.flash_last_photo_used?'sim':'não')+'.';
    }
  }
  async function setFlash(option) {
    if(flashBusy || !state?.flash_supported) {toast('ESP32 indisponível ou firmware sem suporte ao flash.','error');return;}
    flashBusy=true;updateFlashPanel();
    try {
      const result=await esp('/api/flash','POST',option,5000);
      if(!result?.ok)throw new Error('Comando de flash não confirmado');
      await updateStatus(true);
      toast(option==='ON'?'Flash ligado por até 60 segundos.':option==='OFF'?'Flash desligado.':option==='AUTO ON'?'Flash automático ativado.':'Flash automático desativado.','success');
    } catch(err) {fail(err,'Não foi possível alterar o flash');await updateStatus(true);}
    finally {flashBusy=false;updateFlashPanel();}
  }
  function updateScreen(){
    updateFlashPanel();
    const espConnected=!!state;
    if(liveOn && (!state || state.active || state.stage!=='PARADO' || state.photo_lock))stopLive(state?'Pausado para o roteiro/foto':'ESP32-CAM desconectada');
    const arduino=espConnected && !!state.arduino;
    connectionBadge('topWifi',espConnected,'ESP32 online','ESP32 offline');
    connectionBadge('topArduino',arduino,'Arduino conectado','Arduino sem resposta');
    $('offlineNotice').hidden=espConnected;$('offlineDetail').textContent=espConnected?'':lastError;
    $('lockNotice').hidden=!state?.photo_lock;
    setText('dashX',arduino?state.x:'—');setText('dashY',arduino?state.y:'—');
    setText('dashXmm',arduino?mmFmt(mmX(state.x)):'— mm');setText('dashYmm',arduino?mmFmt(mmY(state.y)):'— mm');
    badge($('dashHX'),!!state?.home_x,state?.home_x?'HOME OK':'SEM HOME');
    badge($('dashHY'),!!state?.home_y,state?.home_y?'HOME OK':'SEM HOME');
    setText('dashStage',state?.stage || 'OFFLINE');setText('dashDrivers','Drivers: '+(arduino?(state.enabled?'ativos':'desativados'):'—'));
    badge($('dashLock'),arduino && !state.photo_lock,arduino?(state.photo_lock?'Foto: bloqueada':'Foto: livre'):'Foto: desconhecida');
    const point=state?.point||0,total=state?.total||0,percent=total?Math.min(100,100*point/total):0;
    setText('dashPoint',point);setText('dashTotal',total);setText('dashProgress',state?.active?'Executando percurso':point===total&&total?'Última execução / concluído':'Aguardando / parada');
    $('progressBar').style.width=percent+'%';$('routeProgressBar').style.width=percent+'%';
    setText('routeProgress',point+' / '+total);setText('dashLastPhoto','Foto #'+(state?.last_photo_id||'—'));
    setText('currentEvent',state?.event||'Aguardando telemetria da ESP32-CAM...');
    $('currentError').hidden=!state?.error;$('currentError').textContent=state?.error||'';
    setText('cameraLock',!arduino?'SEM TELEMETRIA DO ARDUINO':(state.photo_lock?'TRAVA ATIVA · PHOTO ID '+state.photo_id:'SEM FOTO PENDENTE'));
    $('cameraLock').classList.toggle('locked',!arduino || !!state.photo_lock);
    setText('diagHttp',espConnected?'Respondendo':'Sem conexão');setText('diagIp',state?.ip||'—');
    setText('diagPanel',window.location.host);setText('diagTime',lastOk||'—');
    setText('diagWifi',state?.wifi?'Conectado':'Desconectado / desconhecido');
    setText('diagArduino',arduino?'Conectado pela UART':'Sem telemetria');
    setText('diagHome',state?('X '+(state.home_x?'OK':'NÃO')+' / Y '+(state.home_y?'OK':'NÃO')):'—');
    const centerReady=isIdle() && !!state?.enabled && !!state?.home_x && !!state?.home_y;
    setText('homeCenterStatus',!state?.arduino?'Arduino desconectado: centralização bloqueada.':!state.home_x||!state.home_y?'HOME ainda não confirmado em X/Y.':!state.enabled?'HOME confirmado: ative os drivers para centralizar.':!isIdle()?'Máquina ocupada: aguarde parada, sem foto pendente.':`Centro MECÂNICO do curso: X=${Math.floor(state.xmax/2)}, Y=${Math.floor(state.ymax/2)} passos; pode não coincidir com o meio do canteiro.`);
    setText('centerLimitsInfo', state?.arduino && Number.isFinite(state.xmax) && Number.isFinite(state.ymax) ? `Centro mecânico calculado com os limites informados pelo Arduino: X=${Math.floor(state.xmax/2)}, Y=${Math.floor(state.ymax/2)} passos. Não é o centro do canteiro.` : 'Centro mecânico: aguardando limites do Arduino. Não é o centro do canteiro.');
    setText('controlStatusX',arduino?`${state.x} passos`:'—');
    setText('controlStatusY',arduino?`${state.y} passos`:'—');
    setText('controlStatusStage',state?.stage||'OFFLINE');
    for(const btn of $$('[data-action="auto-center"]')) btn.disabled=!centerReady;
    updateGeometryPanel();
    setText('diagEnable',state?(state.enabled?'Ativados':'Desativados'):'—');
    setText('diagMotion',state?(state.moving?'Sim':'Não'):'—');
    setText('diagPending',!arduino?'Desconhecido':(state.photo_lock?state.photo_id:'Nenhuma'));
    setText('diagLimits',state?`X: 0–${state.xmax} · Y: 0–${state.ymax}`:'—');
    setText('maxPhysicalCoords',state?.arduino?`MAX lógico: X = ${state.xmax} passos · Y = ${state.ymax} passos`:'MAX programado: aguardando limites do Arduino');
    $('confirmPhysicalMax').disabled=!isIdle() || commandBusy || teachMotionPending || teachMarkPending;
    $('maxPreviewLabel').textContent=maxPreview?`PRÉVIA VIRTUAL — FUNDO: X=${state?.xmax??1640}, Y=${state?.ymax??4550} (não é posição física)`:'Visualização baseada na posição informada pelo Arduino';
    $('maxPreviewLabel').classList.toggle('preview-on',maxPreview);
    $('previewRealBtn').hidden=!maxPreview;
    setText('mapCoords',arduino?`X ${state.x} · Y ${state.y}`:'X — · Y —');
    const xReal=state?.xmax?`${(state.x*328/state.xmax).toFixed(1)} mm`:'—';
    const yReal=state?.ymax?`${(state.y*910/state.ymax).toFixed(1)} mm`:'—';
    const teachingStatus=state?.arduino?`X ${state.x} passos (${xReal}) · Y ${state.y} passos (${yReal})`:'Posição: aguardando Arduino';
    setText('teachPosition',teachingStatus);setText('cameraTeachPosition',teachingStatus);
    setText('teachNextPoint',String(Math.min(49,route.length+1)).padStart(2,'0'));
    setText('teachReady',teachMotionPending?'MOVIMENTANDO...':teachMarkPending?'REGISTRANDO...':!canTeach()?'AGUARDANDO HOME / DRIVERS':'PRONTO PARA MARCAR');
    for(const btn of $$('[data-action="add-current"]'))btn.disabled=!canTeach() || route.length>=48;
    for (const btn of $$('[data-jog]')) btn.disabled=(holdJog?.button!==btn) &&
      (!isIdle() || !state?.enabled || teachMotionPending || holdStopPending || teachMarkPending || commandBusy);
    for (const btn of $$('[data-action="start"]'))btn.disabled=!isIdle()||!state?.enabled||!state?.home_x||!state?.home_y||dirty||route.length===0;
    drawMap();
  }
  async function updateStatus(force=false) {
    if(commandBusy && !force)return;
    if(statusBusy || (commandBusy && !force)) return;
    statusBusy=true;
    try {
      const response=await esp('/api/status','GET','',5500);
      if(typeof response!=='object'||response===null)throw new Error('Resposta inválida da ESP32');
      const wasOffline=!state;
      if(!plannerLimitsLoaded && response?.arduino && response.xmax>0 && response.ymax>0){$('plannerX1').value=response.xmax;$('plannerY1').value=response.ymax;plannerLimitsLoaded=true;drawPlanner(null);}
      state=response;lastOk=now();lastError='';
      if(wasOffline)log('✓ ESP32-CAM conectada ('+response.ip+').','ok');
      if(response.event && response.event!==lastEvent){lastEvent=response.event;log('Evento: '+lastEvent);}
      updateScreen();
      if(!loadedRoute && !dirty)await loadRoute(true);
    } catch(err) {
      const msg=String(err.message||err);
      if(msg!==lastError) log('Sem resposta da ESP32-CAM: '+msg,'error');
      lastError=msg;state=null;loadedRoute=false;updateScreen();
    } finally {statusBusy=false;}
  }
  function changeDirty(v) {dirty=v;$('routeDirty').hidden=!dirty;updateScreen();}
  function validatePoint(x,y){return Number.isSafeInteger(x)&&Number.isSafeInteger(y)&&x>=0&&y>=0&&x<=(state?.xmax||1640)&&y<=(state?.ymax||4550);}
  function redrawRoute() {
    const t=$('routeRows');t.replaceChildren();
    $('emptyRoute').hidden=route.length>0;
    setText('routeBadge',route.length+' / 48 pontos');setText('navRouteCount',route.length);
    setText('routePhotos',route.filter(x=>x.p).length);setText('routeTransit',route.filter(x=>!x.p).length);
    route.forEach((p,i)=>{
      const tr=document.createElement('tr');
      function cell(content){const td=document.createElement('td');if(content instanceof Node)td.append(content);else td.textContent=String(content);tr.append(td);return td;}
      cell(i+1);
      for(const k of ['x','y']){
        const num=document.createElement('input');num.type='number';num.min='0';num.max=k==='x'?(state?.xmax||1640):(state?.ymax||4550);num.value=p[k];num.setAttribute('aria-label',`Ponto ${i+1} ${k.toUpperCase()}`);
        num.addEventListener('change',()=>{const n=int(num.value);if(!validatePoint(k==='x'?n:p.x,k==='y'?n:p.y)){toast('Coordenada fora dos limites','error');num.value=p[k];return;}p[k]=n;changeDirty(true);drawMap();});
        cell(num);
      }
      const check=document.createElement('input');check.type='checkbox';check.checked=p.p;check.setAttribute('aria-label',`Fotografar no ponto ${i+1}`);check.onchange=()=>{p.p=check.checked;changeDirty(true);redrawRoute();};cell(check);
      const controls=document.createElement('div');
      for(const [name,action] of [['↑',()=>swapPoint(i,i-1)],['↓',()=>swapPoint(i,i+1)]]){
        const b=document.createElement('button');b.className='table-btn';b.textContent=name;b.title='Mover ponto '+name;b.onclick=action;controls.append(b);
      }
      cell(controls);
      const rem=document.createElement('button');rem.className='table-btn delete';rem.textContent='Excluir';rem.onclick=()=>{route.splice(i,1);changeDirty(true);redrawRoute();};cell(rem);
      t.append(tr);
    });
    drawMap();
  }
  function swapPoint(a,b){if(b<0||b>=route.length)return;[route[a],route[b]]=[route[b],route[a]];changeDirty(true);redrawRoute();}
  function addPoint(x,y,p){
    if(state?.active){toast('Não edite o roteiro durante execução.','error');return;}
    if(route.length>=48){toast('Limite de 48 pontos.','error');return;}
    if(!validatePoint(x,y)){toast('Coordenadas inválidas ou fora dos limites do firmware.','error');return;}
    route.push({x,y,p});changeDirty(true);redrawRoute();toast('Ponto '+route.length+' adicionado. Salve para gravar na ESP32.','success');
  }
  function routeCSV(){return route.map(p=>`${p.x},${p.y},${p.p?1:0}`).join('\n')+'\n';}
  function parseRoute(s){
    const lines=String(s).split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
    if(lines.length>48)throw new Error('Limite de 48 pontos excedido.');
    return lines.map((line,i)=>{
      if(!/^\d+,\d+,[01]$/.test(line))throw new Error('Linha '+(i+1)+' inválida. Esperado: X,Y,0|1');
      const [x,y,p]=line.split(',').map(Number);
      if(!validatePoint(x,y))throw new Error('Linha '+(i+1)+' fora dos limites da maquete.');
      return {x,y,p:p===1};
    });
  }
  async function loadRoute(silent=false){
    if(dirty && !silent && !confirm('Descartar as alterações locais e carregar o roteiro salvo na ESP32-CAM?'))return;
    try{const txt=await esp('/api/route');route=parseRoute(txt);dirty=false;loadedRoute=true;$('routeDirty').hidden=true;redrawRoute();if(!silent){log('Roteiro carregado da ESP32.','ok');toast('Roteiro carregado.','success');}}
    catch(err){if(!silent)fail(err,'Falha ao carregar roteiro');else log('Ainda não foi possível carregar o roteiro: '+err.message,'error');}
  }
  async function saveRoute(){
    if(!state){toast('ESP32 desconectada.','error');return false;}
    if(!route.length){toast('Adicione pelo menos um ponto.','error');return false;}
    const result=await send('/api/route',routeCSV());
    if(result!==false){changeDirty(false);loadedRoute=true;return true;}
    return false;
  }
  function downloadCSV(){
    if(!route.length){toast('Não há pontos para exportar.','error');return;}
    const blob=new Blob([routeCSV()],{type:'text/csv;charset=utf-8'});const url=URL.createObjectURL(blob);
    const link=document.createElement('a');link.href=url;link.download='roteiro_maquete.csv';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
    log('Roteiro exportado em CSV.');
  }
  async function importCSV(file){
    if(!file)return;
    try{const content=await file.text();const next=parseRoute(content);
      if(!next.length)throw new Error('Arquivo vazio.');
      if(!confirm('Importar '+next.length+' pontos? Isso substitui o roteiro exibido (não o salvo na ESP32).'))return;
      route=next;changeDirty(true);redrawRoute();toast('Roteiro importado. Clique Salvar na ESP32-CAM.','success');
    }catch(err){fail(err,'Falha ao importar CSV');}
    finally{$('routeFile').value='';}
  }

  // Gerador v2.9: calcula SOMENTE pontos, nunca executa movimentos.
  function plannerInputs(){
    const data={mode:$('plannerMode').value,x0:$('plannerX0').value,x1:$('plannerX1').value,
      y0:$('plannerY0').value,y1:$('plannerY1').value,footprintX:$('plannerFootX').value,
      footprintY:$('plannerFootY').value,overlap:$('plannerOverlap').value,
      flipX:$('plannerFlipX').checked,flipY:$('plannerFlipY').checked,
      limitX:state?.xmax, limitY:state?.ymax};
    return data;
  }
  function plannerInvalidate() {
    plannerDraft=null;plannerConfigHash=null;$('plannerApply').disabled=true;
    const feedback=$('plannerFeedback');feedback.classList.remove('error');
    feedback.textContent='Parâmetros alterados. Clique em Pré-visualizar para recalcular antes de aplicar.';
    drawPlanner(null);
  }
  function plannerMessage(message, error=false){
    const el=$('plannerFeedback');el.textContent=message;el.classList.toggle('error',error);
  }
  function plannerPreview(){
    if(!state?.arduino){plannerMessage('Conecte a ESP32-CAM e o Arduino para obter os limites reais antes de gerar o roteiro.',true);return;}
    if(state.active || state.moving || state.photo_lock){plannerMessage('Aguarde a máquina ficar parada antes de editar o roteiro.',true);return;}
    try{
      const input=plannerInputs();
      const draft=window.AtlasPlanner.build(input);
      plannerDraft=draft;plannerConfigHash=JSON.stringify(input);
      $('plannerApply').disabled=false;
      plannerMessage(`${draft.points.length} pontos · ${draft.cols} colunas × ${draft.rows} linhas · espaçamento máximo de ${draft.spacingX} passos X / ${draft.spacingY} passos Y. ${draft.perimeterOnly?'ATENÇÃO: apenas bordas, sem cobrir a área interna.':'Confirme na prévia a cobertura real antes de usar.'}`);
      drawPlanner(draft);
      log(`Prévia ${draft.mode}: ${draft.points.length} pontos; nenhum comando enviado à máquina.`,'ok');
    }catch(err){plannerDraft=null;plannerConfigHash=null;$('plannerApply').disabled=true;plannerMessage(err.message,true);drawPlanner(null);}
  }
  function plannerApply(){
    if(!plannerDraft || plannerConfigHash!==JSON.stringify(plannerInputs())){plannerInvalidate();toast('Gere a prévia com os parâmetros atuais.','error');return;}
    if(!state?.arduino || state.active || state.moving || state.photo_lock || commandBusy){toast('Máquina ocupada/desconectada; não é seguro substituir o roteiro.','error');return;}
    if(!confirm(`Substituir os ${route.length} pontos exibidos pelos ${plannerDraft.points.length} pontos da prévia? Isso NÃO movimenta motores nem salva na ESP32-CAM.`))return;
    route=plannerDraft.points.map(p=>({...p}));
    changeDirty(true);redrawRoute();
    plannerMessage(`${route.length} pontos copiados para a lista local. Confira a ordem, depois clique em Salvar na ESP32-CAM. A máquina ainda NÃO se moveu.`);
    log(`${route.length} pontos gerados inseridos na lista local; aguardando salvamento.`,'ok');
    toast('Roteiro gerado. Confira e clique Salvar na ESP32-CAM.','success');
  }
  function drawPlanner(draft){
    const canvas=$('plannerCanvas');if(!canvas)return;
    const w=canvas.getBoundingClientRect().width||720,h=260,d=Math.min(window.devicePixelRatio||1,2);
    canvas.width=Math.round(w*d);canvas.height=Math.round(h*d);
    const ctx=canvas.getContext('2d');ctx.setTransform(d,0,0,d,0,0);ctx.clearRect(0,0,w,h);
    const pad=33,bw=w-pad*2,bh=h-pad*2;
    ctx.fillStyle='#102b3e';ctx.fillRect(pad,pad,bw,bh);
    ctx.strokeStyle='#4d7991';ctx.lineWidth=2;ctx.strokeRect(pad,pad,bw,bh);
    if(!draft){ctx.fillStyle='#a4bed1';ctx.font='13px system-ui';ctx.textAlign='center';ctx.fillText('Clique em Pré-visualizar para mostrar o trajeto',w/2,h/2);return;}
    const xmax=state?.xmax||1640,ymax=state?.ymax||4550;
    const xy=p=>[pad+(p.x/xmax)*bw, h-pad-(p.y/ymax)*bh];
    const pts=draft.points;
    ctx.beginPath();ctx.strokeStyle='#62bed5';ctx.lineWidth=2;ctx.setLineDash([6,5]);
    pts.forEach((p,i)=>{const [x,y]=xy(p);i?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.stroke();ctx.setLineDash([]);
    pts.forEach((p,i)=>{const [x,y]=xy(p);ctx.beginPath();ctx.arc(x,y,pts.length>30?5:7,0,Math.PI*2);ctx.fillStyle=i===0?'#fbd17f':i===pts.length-1?'#7eaaff':'#59dbad';ctx.fill();ctx.fillStyle='#061624';ctx.font='bold 9px system-ui';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(String(i+1),x,y);});
    ctx.fillStyle='#b5cfdd';ctx.font='11px system-ui';ctx.textAlign='left';ctx.textBaseline='alphabetic';ctx.fillText('X 0 / Y 0',pad, h-7);ctx.fillText(`Limites X ${xmax}, Y ${ymax}`,pad,16);
  }

  // A visualizacao isometrica usa geometria projetada em canvas 2D: nao depende
  // de servidores externos, placas de video ou WebGL, e nao pretende ser CAD.
  function drawMap(){
    if(mapMode==='3d') {
      if (currentView==='dashboard' && window.Atlas3D) window.Atlas3D.render(state, route, maxPreview?'max':null);
      return;
    }
    const canvas=$('mapCanvas'); if(!canvas || currentView!=='dashboard')return;
    const rect=canvas.getBoundingClientRect();if(rect.width<3||rect.height<3)return;
    const density=Math.min(window.devicePixelRatio||1,2),w=rect.width,h=rect.height;
    if(canvas.width!==Math.round(w*density)||canvas.height!==Math.round(h*density)){canvas.width=Math.round(w*density);canvas.height=Math.round(h*density);}
    const c=canvas.getContext('2d');c.setTransform(density,0,0,density,0,0);c.clearRect(0,0,w,h);
    const maxX=Math.max(1,state?.xmax||1640),maxY=Math.max(1,state?.ymax||4550);
    const minSize=Math.min(w*.75,h*.72),width=Math.min(w*.7,minSize*1.08),height=Math.min(h*.69,minSize*.8);
    const map2d=(x,y)=>[w/2-width/2+(x/maxX)*width,h/2+height/2-(y/maxY)*height+4];
    const isoScale=Math.min(w*.82/1.48,h*.70/.94);
    const iso=(x,y)=>{const a=x/maxX-.5,b=y/maxY-.5;return [w/2+(a-b)*isoScale*.75,h*.47+(a+b)*isoScale*.41];};
    const coord=mapMode==='iso'?iso:map2d;
    c.lineJoin='round';
    const poly=[[0,0],[maxX,0],[maxX,maxY],[0,maxY]].map(([x,y])=>coord(x,y));
    c.beginPath();poly.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.closePath();c.fillStyle='#0e2638';c.fill();c.lineWidth=2;c.strokeStyle='#52738e';c.stroke();
    if(mapMode==='iso'){c.beginPath();c.moveTo(...poly[1]);c.lineTo(poly[1][0],poly[1][1]+22);c.lineTo(poly[2][0],poly[2][1]+22);c.lineTo(...poly[2]);c.fillStyle='#0b1d30';c.fill();c.strokeStyle='#2a5166';c.stroke();}
    c.strokeStyle='#25445a';c.lineWidth=1;
    for(let i=1;i<10;i++){const f=i/10;for(const line of [[[maxX*f,0],[maxX*f,maxY]],[[0,maxY*f],[maxX,maxY*f]]]){const a=coord(...line[0]),b=coord(...line[1]);c.beginPath();c.moveTo(...a);c.lineTo(...b);c.stroke();}}
    if(route.length){c.strokeStyle='#4db4c2';c.lineWidth=2.4;c.setLineDash([7,6]);c.beginPath();route.forEach((p,i)=>{const [x,y]=coord(p.x,p.y);i?c.lineTo(x,y):c.moveTo(x,y);});c.stroke();c.setLineDash([]);}
    route.forEach((p,i)=>{
      const [x,y]=coord(p.x,p.y);c.beginPath();c.arc(x,y,9,0,Math.PI*2);c.fillStyle=p.p?'#48d9b3':'#ffd089';c.fill();c.lineWidth=2;c.strokeStyle='#102b39';c.stroke();
      c.fillStyle='#0b1c25';c.font='bold 11px system-ui';c.textAlign='center';c.textBaseline='middle';c.fillText(String(i+1),x,y+.25);
    });
    if(state?.arduino && Number.isFinite(state.x) && Number.isFinite(state.y)){
      const [x,y]=coord(state.x,state.y);c.beginPath();c.arc(x,y,15,0,Math.PI*2);c.strokeStyle='#77b8ff66';c.lineWidth=7;c.stroke();c.beginPath();c.arc(x,y,7,0,Math.PI*2);c.fillStyle='#89bbff';c.fill();c.strokeStyle='#e8fbff';c.lineWidth=2;c.stroke();
    }
    c.textAlign='left';c.textBaseline='alphabetic';c.font='bold 11px system-ui';c.fillStyle='#94b1c9';
    const x0=coord(0,0),x1=coord(maxX,0),y1=coord(0,maxY);
    c.fillText('0,0',x0[0]-16,x0[1]+17);c.fillText('X '+maxX,x1[0]-22,x1[1]+17);c.fillText('Y '+maxY,y1[0]-12,y1[1]-12);
  }

  async function loadConfig(){
    try{const resp=await fetch('/api/config',{cache:'no-store'});if(resp.ok){const cfg=await resp.json();setText('diagTarget',cfg.esp_target||'—');}}catch(err){log('Falha ao consultar configuração local: '+err.message,'error');}
  }
  // v3.0: o mosaico roda APENAS no notebook. Não envia comandos à CNC.
  let mosaicBusy=false;
  let mosaicLatest='';
  const mosaicFieldIds=['mosaicFootX','mosaicFootY','mosaicRotate','mosaicFlipX','mosaicFlipY','mosaicAutomatic','mosaicFine'];
  function mosaicParams(){
    return {footprint_x:Number($('mosaicFootX').value),footprint_y:Number($('mosaicFootY').value),
      rotate:Number($('mosaicRotate').value),flip_x:$('mosaicFlipX').checked,
      flip_y:$('mosaicFlipY').checked,automatico:$('mosaicAutomatic').checked,encaixe_fino:$('mosaicFine').checked};
  }
  function mosaicMessage(text,problem=false){
    const el=$('mosaicFeedback');if(!el)return;
    el.textContent=text;el.style.color=problem?'#ffafb8':'';
  }
  async function mosaicSave(silent=false){
    const cfg=mosaicParams();
    if(!Number.isInteger(cfg.footprint_x)||cfg.footprint_x<1||cfg.footprint_x>50000||
       !Number.isInteger(cfg.footprint_y)||cfg.footprint_y<1||cfg.footprint_y>50000)throw new Error('Cobertura da câmera deve ser inteira e positiva (1 a 50000 passos).');
    const r=await fetch('/api/mosaico/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(cfg)});
    const data=await r.json();if(!r.ok)throw new Error(data.error||'Falha ao salvar a calibração');
    if(!silent){mosaicMessage('Calibração salva no notebook. A montagem utiliza estas medidas.');toast('Configuração do mosaico salva.','success');}
    return data;
  }
  async function mosaicRefresh(){
    try{
      const res=await fetch('/api/mosaico/status',{cache:'no-store'});
      if(!res.ok)throw new Error('HTTP '+res.status);
      const obj=await res.json();const ses=obj.session;
      const label=ses ? ({running:'Percurso em execução; aguardando fotos.',processing:'Montando mosaico...',completed:'Percurso concluído.',stopped:'Percurso interrompido; fotos preservadas.',error:'Falha na montagem automática: '+(ses.error||'verifique a calibração')}[ses.state]||'') : 'Nenhum percurso novo registrado nesta versão.';
      const latest=obj.mosaics&&obj.mosaics[0];
      if(latest){
        const url='/mosaicos/'+encodeURIComponent(latest.filename);
        if(mosaicLatest!==latest.filename){
          mosaicLatest=latest.filename;const preview=$('mosaicPreview');preview.replaceChildren();
          const img=document.createElement('img');img.src=url;img.alt='Mosaico aproximado da plantação gerado por coordenadas';preview.append(img);
          const target=$('mosaicResult');target.replaceChildren();
          const a=document.createElement('a');a.href=url;a.download=latest.filename;a.textContent='↓ Baixar mosaico JPEG';
          const details=document.createElement('span');details.textContent=`${latest.photos} posições · ${latest.width} × ${latest.height} px · ${latest.created_at}` + (latest.alignment?.method==='pontos_comuns_limitados_por_XY'?` · Ajustadas: ${latest.alignment.adjusted} · X/Y preservado em ${latest.alignment.fallback_xy}`:' · Coordenadas X/Y');
          target.append(a,details);
        }
      }
      mosaicMessage(label + (latest?' Último mosaico: '+latest.photos+' posições.':''),ses?.state==='error');
    }catch(err){mosaicMessage('Falha ao consultar mosaico: '+err.message,true);}
  }
  async function mosaicLoad(){
    try{
      const r=await fetch('/api/mosaico/config',{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);
      const cfg=await r.json();$('mosaicFootX').value=cfg.footprint_x;$('mosaicFootY').value=cfg.footprint_y;
      $('mosaicRotate').value=cfg.rotate;$('mosaicFlipX').checked=cfg.flip_x;$('mosaicFlipY').checked=cfg.flip_y;
      $('mosaicAutomatic').checked=cfg.automatico;$('mosaicFine').checked=cfg.encaixe_fino!==false;
    }catch(err){mosaicMessage('Não consegui carregar a calibração: '+err.message,true);}
    await mosaicRefresh();
  }
  async function mosaicGenerate(){
    if(mosaicBusy)return;
    mosaicBusy=true;$('mosaicGenerate').disabled=true;
    mosaicMessage('Montando mosaico com as fotos salvas. Pode levar alguns segundos...');
    try{
      await mosaicSave(true);
      const source=$('mosaicSource').value;
      const r=await fetch('/api/mosaico/gerar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source})});
      const obj=await r.json();if(!r.ok)throw new Error(obj.error||'Falha ao gerar mosaico');
      mosaicMessage(`Mosaico salvo! ${obj.photos} posições em ${obj.width} × ${obj.height} pixels.`);
      await mosaicRefresh();toast('Mosaico gerado e armazenado no notebook.','success');
    }catch(err){mosaicMessage(err.message,true);toast('Mosaico: '+err.message,'error');}
    finally{mosaicBusy=false;$('mosaicGenerate').disabled=false;}
  }
  async function refreshGallery(){
    try{
      const r=await fetch('/api/photos',{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);
      const files=await r.json();if(!Array.isArray(files))throw new Error('Lista inválida');
      if(JSON.stringify(files)===JSON.stringify(lastGallery))return;
      lastGallery=files;setText('photoCount',files.length+' fotos recentes');
      const gallery=$('photoGallery');gallery.replaceChildren();
      if(!files.length){const txt=document.createElement('p');txt.className='hint';txt.textContent='Ainda não há fotografias salvas.';gallery.append(txt);$('photoPreview').replaceChildren();const e=document.createElement('div');e.className='preview-empty';e.textContent='Nenhuma foto recebida';$('photoPreview').append(e);return;}
      const preview=$('photoPreview');preview.replaceChildren();const main=document.createElement('img');main.alt='Última fotografia salva';main.src='/fotos/'+encodeURIComponent(files[0]);main.title=files[0];preview.append(main);preview.onclick=()=>openPhoto(files[0]);preview.style.cursor='zoom-in';
      for(const name of files.slice(0,80)){
        const btn=document.createElement('button');btn.className='gallery-item';btn.title='Ampliar '+name;
        const pic=document.createElement('img');pic.src='/fotos/'+encodeURIComponent(name);pic.alt=name;pic.loading='lazy';
        const text=document.createElement('span');text.textContent=name;btn.append(pic,text);btn.onclick=()=>openPhoto(name);gallery.append(btn);
      }
    }catch(err){log('Falha ao atualizar galeria: '+err.message,'error');}
  }
  function openPhoto(name){$('modalImage').src='/fotos/'+encodeURIComponent(name);setText('modalCaption',name);$('photoModal').hidden=false;}
  function setSpeedHint(){const v=Number($('speedPps').value);setText('speedHint',Number.isFinite(v)&&v>0?`≈ ${(v*328/(state?.xmax||1640)).toFixed(2)} mm/s no eixo X (ESCALA TEÓRICA do firmware, não medida nas fotos). Velocidades maiores exigem calibração mecânica.`:'Valor de velocidade inválido.');}

  async function action(name,photoSource=''){
    switch(name){
      case 'stop':await send('/api/stop');break;
      case 'preview-max':{
        maxPreview=true;
        const three=document.querySelector('[data-map="3d"]');
        if(three){mapMode='3d';$$('[data-map]').forEach(b=>{const on=b===three;b.classList.toggle('selected',on);b.setAttribute('aria-pressed',String(on));});}
        $('mapCanvas').hidden=true;$('model3dCanvas').hidden=false;$('orbitControls').hidden=false;
        navigate('dashboard');updateScreen();
        toast('Prévia MAX no FUNDO: só o modelo 3D mudou. A máquina física NÃO se moveu.','info');
        break;
      }
      case 'preview-real':{
        maxPreview=false;updateScreen();drawMap();
        toast('Modelo 3D acompanhando novamente a posição reportada pelo Arduino.','info');
        break;
      }
      case 'confirm-physical-max':{
        invalidateCenterCheck();
        if(commandBusy || teachMotionPending || teachMarkPending || !isIdle()){
          toast('Confirme MAX somente com o Arduino conectado e a máquina parada, sem roteiro ou foto pendente.','error');return;
        }
        // Relê a telemetria imediatamente antes de qualquer registro lógico.
        let before;
        try{before=await freshPosition();}catch(err){fail(err,'Não foi possível verificar o Arduino');return;}
        if(!before.arduino || before.moving || before.active || before.photo_lock || before.stage!=='PARADO' ||
           !Number.isSafeInteger(before.xmax) || !Number.isSafeInteger(before.ymax) || before.xmax<=0 || before.ymax<=0){
          toast('Limites ou estado do Arduino inválidos. Registro MAX cancelado.','error');return;
        }
        if(before.enabled){
          toast('Desative os drivers antes do alinhamento físico. Depois confirme MAX.','error');return;
        }
        const mx=before.xmax,my=before.ymax;
        if(!confirm(`REFERÊNCIA MAX SEM SENSORES — NÃO MOVIMENTA MOTOR\n\nConfirma que alinhou FISICAMENTE e verificou X no extremo máximo e Y no extremo máximo, sem forçar os batentes?\n\nO Arduino passará a considerar X=${mx} e Y=${my} passos. HOME atual será redefinido.\n\nA confirmação errada poderá causar colisão na próxima centralização.`))return;
        const set=await command(`SETPOS X ${mx} Y ${my}`);
        if(set===false)return;
        try{
          await waitForState(s=>s.arduino && s.x===mx && s.y===my && !s.home_x && !s.home_y &&
            !s.moving && !s.photo_lock && !s.active, 'SETPOS MAX');
        }catch(err){fail(err,'Confirmação de MAX não recebida');return;}
        const homed=await command('HOME');
        if(homed===false)return;
        try{
          await waitForState(s=>s.arduino && s.home_x && s.home_y && s.x===mx && s.y===my &&
            !s.moving && !s.photo_lock && !s.active, 'HOME MAX');
        }catch(err){fail(err,'HOME MAX não confirmado');return;}
        maxPreview=false;updateScreen();
        log(`Referência MAX manual confirmada: X=${mx}, Y=${my} (sem movimentar).`,'ok');
        toast('MAX físico e HOME registrados. Agora você pode ativar os drivers e centralizar.','success');
        break;
      }
      case 'home':invalidateCenterCheck();if(confirm('HOME manual NÃO move a máquina. A posição física corresponde às coordenadas exibidas? Se usou SETPOS para 0, a estrutura deve estar no mínimo; se usou MAX, deve estar no máximo.'))await command('HOME');break;
      case 'define-zero':{
        invalidateCenterCheck();
        if(!requireReady())return;
        if(!confirm('ATENÇÃO: a máquina NÃO irá se mover. Confirma que alinhou FISICAMENTE os dois eixos na origem mínima (X0/Y0), sem forçar os batentes? As referências HOME anteriores serão invalidadas.'))return;
        const result=await command('SETPOS X 0 Y 0');
        if(result!==false)toast('Posição lógica enviada: confirme HOME manual ANTES de centralizar.','info');
        break;
      }
      case 'auto-center':{
        if(!requireReady(true))return;
        const midX=Math.floor(state.xmax/2),midY=Math.floor(state.ymax/2);
        if(!confirm(`CENTRO MECÂNICO DO CURSO (NÃO É CENTRO DO CANTEIRO)\nDestino X=${midX} e Y=${midY} passos.\n\nA referência física escolhida (X0/Y0 ou MAX) foi conferida, os limites/escala estão calibrados, os dois eixos estão livres e você pode parar a máquina se necessário?\n\nSem referência física correta, o movimento pode colidir com a estrutura.`))return;
        await command('CENTER');
        break;
      }
      case 'geom-mark-center':await teachPlotCenter();break;
      case 'geom-go-center':await goPlotCenter();break;
      case 'home-x':invalidateCenterCheck();if(confirm('Confirma referência física do eixo X? O HOME não move motor.'))await command('HOME X');break;
      case 'home-y':invalidateCenterCheck();if(confirm('Confirma referência física do eixo Y? O HOME não move motor.'))await command('HOME Y');break;
      case 'unhome':invalidateCenterCheck();await command('UNHOME',{confirmText:'Invalidar HOME de ambos os eixos?'});break;
      case 'enable':await command('ENABLE 1');break;
      case 'disable':await command('ENABLE 0',{confirmText:'Liberar drivers pode permitir movimento livre dos eixos. Confirmar?'});break;
      case 'set-speed':{
        const pps=int($('speedPps').value);if(pps<10||pps>2000){toast('Escolha entre 10 e 2000 passos/s.','error');return;}
        const delay=Math.max(500,Math.min(100000,Math.round(1000000/pps)));
        await command('SPEED '+delay);setSpeedHint();break;
      }
      case 'setpos':{
        invalidateCenterCheck();
        if(!requireReady())return;
        const x=int($('setX').value),y=int($('setY').value);
        if(!validatePoint(x,y)){toast('Coordenadas fora do limite.','error');return;}
        await command(`SETPOS X ${x} Y ${y}`,{confirmText:'Isso altera SOMENTE as coordenadas lógicas, SEM mover motores, e invalida o HOME. Confirma?'});break;
      }
      case 'goto-center':if(requireReady(true))await command('CENTER',{confirmText:'Mover até o meio do CURSO MECÂNICO? NÃO é necessariamente o centro das plantas. Área livre e HOME conferido?'});break;
      case 'goto-origin':if(requireReady(true))await command('MOVE X 0 Y 0',{confirmText:'Mover fisicamente até X=0,Y=0? Confira HOME e área livre.'});break;
      case 'add-current':await markCurrentPosition(photoSource ? $(photoSource).checked : true);break;
      case 'add-point':addPoint(int($('pointX').value),int($('pointY').value),$('pointPhoto').checked);break;
      case 'planner-preview':plannerPreview();break;
      case 'planner-apply':plannerApply();break;
      case 'save-route':await saveRoute();break;
      case 'load-route':await loadRoute();break;
      case 'export-route':downloadCSV();break;
      case 'import-route':$('routeFile').click();break;
      case 'start':{
        if(liveOn)stopLive('Pausado para o roteiro');
        if(!requireReady(true))return;
        if(!route.length){toast('Cadastre pelo menos um ponto.','error');return;}
        if(dirty){toast('Salve o roteiro antes de iniciar.','error');return;}
        await send('/api/start','',{confirmText:'Confirme HOME físico, área livre, alimentação segura e roteiro salvo. INICIAR percurso?'});break;
      }
      case 'flash-on':await setFlash('ON');break;
      case 'flash-off':await setFlash('OFF');break;
      case 'manual-photo':{
        if(liveOn)stopLive('Pausado para fotografar');
        if(!requireReady()||!state.home_x||!state.home_y){toast('Para foto manual, confirme o HOME e o Arduino parado.','error');return;}
        const result=await send('/api/manual-photo','',{timeout:18000});if(result!==false){await refreshGallery();navigate('camera');}break;
      }
      case 'retry':await send('/api/retry');break;
      case 'recover':{
        if(prompt('ATENÇÃO: isso descarta a foto pendente e NÃO comprova captura. Digite DESCARTAR para confirmar:')!=='DESCARTAR')return;
        await send('/api/recover');break;
      }
      case 'live-start':startLive();break;
      case 'live-stop':stopLive();break;
      case 'refresh-gallery':await refreshGallery();toast('Galeria atualizada.','success');break;
      case 'mosaic-save':try{await mosaicSave();}catch(err){mosaicMessage(err.message,true);toast(err.message,'error');}break;
      case 'mosaic-generate':await mosaicGenerate();break;
      case 'mosaic-refresh':await mosaicRefresh();break;
      case 'refresh':await updateStatus();break;
      case 'status-command':await command('STATUS');break;
      case 'copy-log':try{await navigator.clipboard.writeText(logRows.slice().reverse().map(x=>`[${x.time}] ${x.text}`).join('\n'));toast('Histórico copiado.','success');}catch(err){fail(err,'Não foi possível copiar');}break;
      case 'clear-log':logRows.length=0;$('logOutput').replaceChildren();log('Monitor limpo.');break;
    }
  }

  document.addEventListener('click', async (event)=>{
    const modeSwitch=event.target.closest('[data-ui-switch]');
    if(modeSwitch){setUiMode(modeSwitch.dataset.uiSwitch);return;}
    const plannerToggle=event.target.closest('#plannerExpand');
    if(plannerToggle){setPlannerExpanded($('plannerDetails').hidden);return;}
    const jump=event.target.closest('[data-view],[data-view-jump]');if(jump){navigate(jump.dataset.view||jump.dataset.viewJump);return;}
    const mode=event.target.closest('[data-map]');if(mode){
      mapMode=mode.dataset.map;
      $$('[data-map]').forEach(b=>{const on=b===mode;b.classList.toggle('selected',on);b.setAttribute('aria-pressed',String(on));});
      $('mapCanvas').hidden=mapMode==='3d';
      $('model3dCanvas').hidden=mapMode!=='3d';
      $('orbitControls').hidden=mapMode!=='3d';
      drawMap();return;
    }
    const orbit=event.target.closest('[data-3d]');if(orbit){
      if(window.Atlas3D) window.Atlas3D.control(orbit.dataset['3d']);return;
    }
    const stop=event.target.closest('[data-close-photo]');if(stop){$('photoModal').hidden=true;return;}
    const preset=event.target.closest('[data-step]');if(preset){$('moveDelta').value=preset.dataset.step;$('teachDelta').value=preset.dataset.step;$$('[data-step]').forEach(b=>b.classList.toggle('selected',b===preset));return;}
    const speed=event.target.closest('[data-speed]');if(speed){$('speedPps').value=speed.dataset.speed;$$('[data-speed]').forEach(b=>b.classList.toggle('selected',b===speed));setSpeedHint();return;}
    const jog=event.target.closest('[data-jog]');if(jog){
      if($('holdJogMode').checked)return; // Em modo segurar, click nao dispara JOG discreto.
      if(!requireReady(true))return;
      const [axis,directionText]=jog.dataset.jog.split(':');
      const selector=currentView==='route'?'teachDelta':'moveDelta';
      const delta=int($(selector).value);
      if(!Number.isSafeInteger(delta)||delta<1||delta>MAX_MANUAL_STEPS){toast('Escolha de 1 a 5000 passos.','error');return;}
      await jogTeach(axis,Number(directionText),delta);return;
    }
    const button=event.target.closest('[data-action]');if(button){await action(button.dataset.action,button.dataset.photoInput || '');return;}
  });
  try{uiMode=window.localStorage.getItem(uiModeKey)==='advanced'?'advanced':'simple';}catch(_){uiMode='simple';}
  setUiMode(uiMode);
  $('refreshBtn').onclick=()=>updateStatus();$('menuToggle').onclick=()=>$('sidebar').classList.toggle('open');
  $('routeFile').onchange=(e)=>importCSV(e.target.files[0]);
  for(const el of $$('.planner-form input,.planner-form select,.planner-options input'))el.addEventListener('change',plannerInvalidate);
  $('liveImage').addEventListener('load',liveFrameReceived);
  $('liveImage').addEventListener('error',liveFrameError);
  $('liveGrid').addEventListener('change',refreshLiveGrid);
  for(const check of $$('[data-flash-auto]')) {
    check.addEventListener('change',()=>setFlash(check.checked?'AUTO ON':'AUTO OFF'));
  }
  $('speedPps').oninput=setSpeedHint;
  // Pointer Events incluem mouse e toque. Soltar FORA do botao tambem para.
  document.addEventListener('pointerdown',event=>{
    if(!$('holdJogMode').checked || (event.pointerType==='mouse' && event.button!==0))return;
    const btn=event.target.closest('[data-jog]');
    if(!btn || btn.disabled)return;
    event.preventDefault();
    // Mantem os eventos de soltura mesmo quando o dedo/mouse sai da seta.
    try {btn.setPointerCapture(event.pointerId);} catch(_) {}
    beginHold(btn,event.pointerId);
  });
  window.addEventListener('pointerup',event=>{
    if(holdJog && event.pointerId===holdJog.pointerId)releaseHold();
  },true);
  window.addEventListener('pointercancel',event=>{
    if(holdJog && event.pointerId===holdJog.pointerId)releaseHold('Toque cancelado');
  },true);
  window.addEventListener('blur',()=>{if(holdJog)releaseHold('Janela sem foco');});
  document.addEventListener('visibilitychange',()=>{
    if(document.hidden && holdJog)releaseHold('Pagina em segundo plano');
  });
  $('holdJogMode').addEventListener('change',event=>{
    if(holdJog)releaseHold('Modo alterado');
    showHoldStatus(event.target.checked
      ? 'Ativado: segure a seta para mover e solte para parar. Limite do JOG continuo: 125 passos/s.'
      : 'Desativado: um clique movimenta a quantidade de passos selecionada.');
  });
  for(const id of ['moveDelta','teachDelta']) $(id).addEventListener('change',e=>{const n=int(e.target.value);if(n>=1&&n<=MAX_MANUAL_STEPS){for(const el of ['moveDelta','teachDelta'])$(el).value=n;$$('[data-step]').forEach(b=>b.classList.toggle('selected',Number(b.dataset.step)===n));}});
  window.addEventListener('resize',()=>{requestAnimationFrame(drawMap);if(currentView==='route')drawPlanner(plannerDraft);});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'){$('photoModal').hidden=true;if(holdJog)releaseHold('ESC');}});
  window.addEventListener('beforeunload',e=>{if(holdJog)releaseHold('Pagina fechada');if(liveOn)stopLive();if(dirty){e.preventDefault();e.returnValue='';}});
  $('geomReferenceCheck').addEventListener('change',updateGeometryPanel);
  loadGeometry();
  setInterval(()=>{setText('clock',now());},1000);setText('clock',now());
  log('Painel v4.2: medidas reais e centro do canteiro, interface Simples/Avançado; percursos, stream, mosaicos e PHOTOACK preservados.');
  updateScreen();setSpeedHint();drawPlanner(null);
  loadConfig();updateStatus();refreshGallery();mosaicLoad();
  setInterval(updateStatus,1200);
  setInterval(refreshGallery,9000);
  setInterval(mosaicRefresh,12000);
})();
