"""Suite de regresión de Hato. Uso: python3 tests/suite.py ruta/al/index.html
Sale con código 1 si alguna prueba falla."""
import sys
from playwright.sync_api import sync_playwright

ARCHIVO = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/hato/index.html'
URL = 'file://' + ARCHIVO
RES = []

def check(nombre, ok, detalle=''):
    RES.append((nombre, bool(ok), detalle))

LLENAR = """()=>{for(let i=0;i<60;i++)S.a.push({id:'z'+(7000+i),n:'Vaca'+i,s:'H',r:'Jersey',m:'Pura',f:add(TD,-900),p:'',q:'',e:'A',sl:'',w:0,reb:'R1',fi:'F1'});const a=S.a.filter(x=>x.e=='A');
for(let i=0;i<70;i++){const x=a[i%a.length];S.t.push({id:'tz'+i,a:x.id,f:add(TD,-100-i),tipo:'Vacuna',med:'Med'+(i%7),d:'2 ml',c:1000,rf:add(TD,(i*3)%90-20)})}
for(let i=0;i<60;i++){const x=a[i%a.length];S.g.push({f:add(TD,-i),cat:'Alimento',d:'Gasto '+i,m:1000+i});S.v.push({f:add(TD,-((i*7)%60)),a:x.id,kg:400,pk:2000,neto:800000,c:'Cliente'});S.m.push({a:x.id,f:add(TD,-i),reb:'R1',fi:'F1'});S.r.push({a:x.id,t:'Monta',f:add(TD,-i),p:'Toro'})}
save();render()}"""

def abrir(b, rol, llenar=False):
    ctx = b.new_context(viewport={'width': 390, 'height': 844})
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.route('**/*', lambda r: r.continue_() if r.request.url.startswith('file:') else r.abort())
    pg.goto(URL)
    pg.evaluate("r=>{localStorage.clear();localStorage.setItem('ses',JSON.stringify({token:'x',user:'u1',finca:'f1',rol:r,fnom:'C',usuario:'n'}));localStorage.setItem('cortijo1_u1',JSON.stringify(seed()))}", rol)
    pg.reload(); pg.wait_for_timeout(800)
    if llenar:
        pg.evaluate(LLENAR); pg.wait_for_timeout(200)
    return ctx, pg, errs

def filas(pg, sel):
    return max(pg.locator(sel + ' tr').count() - 1, 0)

def ir(pg, t):
    pg.evaluate(f"go('{t}')"); pg.wait_for_timeout(450)

with sync_playwright() as p:
    b = p.chromium.launch()
    for rol in ['admin', 'peon']:
        # Carga y recorrido general
        ctx, pg, errs = abrir(b, rol)
        check(f'{rol}: banner con 3 letreros', pg.locator('.fl').count() == 3)
        for t in ['animales', 'salud', 'pesos', 'repro', 'gen', 'reb', 'fin', 'inf', 'inicio']:
            ir(pg, t)
        check(f'{rol}: recorrer todas las secciones sin errores JS', not errs, errs)

        # Microcorte: una segunda pasada de render no reinicia la caída de letreros
        pg.reload(); pg.wait_for_timeout(450)
        antes = pg.evaluate("Math.max(0,...document.getAnimations().filter(a=>a.animationName=='clava').map(a=>a.currentTime))")
        pg.evaluate('render()'); pg.wait_for_timeout(20)
        an = pg.evaluate("document.getAnimations().filter(a=>a.animationName=='clava').map(a=>a.currentTime)")
        check(f'{rol}: re-render igual en Inicio ni reinicia ni corta la caída de letreros', len(an) == 3 and min(an) >= antes, (antes, an))
        ir(pg, 'salud'); pg.wait_for_timeout(1200); ir(pg, 'inicio')
        n = pg.evaluate("document.getAnimations().filter(a=>a.animationName=='clava').length")
        check(f'{rol}: volver a Inicio sí anima los letreros', n == 3, n)

        # Tema
        pg.evaluate('tema()'); pg.reload(); pg.wait_for_timeout(600)
        check(f'{rol}: modo oscuro persiste al recargar', pg.evaluate("document.documentElement.dataset.theme") == 'dark')
        ctx.close()

        # Paginación con muchos datos
        ctx, pg, errs = abrir(b, rol, llenar=True)
        ir(pg, 'animales')
        check(f'{rol}: animales arranca en 25', filas(pg, '#al') == 25, filas(pg, '#al'))

        listas = [('salud', 'sr'), ('salud', 'sh'), ('fin', 'fv'), ('fin', 'fg'), ('repro', 're'), ('reb', 'rm')]
        for tab, k in listas:
            ir(pg, tab)
            sel = '#pg_' + k
            f1 = filas(pg, sel)
            if pg.locator(sel + ' button.g').count() == 0:
                check(f'{rol}: {k} muestra 25 y Ver más suma 25', False, 'no existe la lista paginada'); continue
            pg.locator(sel + ' button.g').click(); pg.wait_for_timeout(120)
            f2 = filas(pg, sel)
            check(f'{rol}: {k} muestra 25 y Ver más suma 25', (f1, f2) == (25, 50), (f1, f2))

        # Orden Salud: menos días primero
        ir(pg, 'salud')
        dd = pg.evaluate("pend().map(t=>t.dd)")
        txt = pg.locator('#pg_sr tr td:nth-child(4)').all_inner_texts()
        num = [-int(t.split()[1]) if t.startswith('Vencido') else int(t.split()[1]) for t in txt]
        check(f'{rol}: refuerzos ordenados de menos a más días', bool(num) and num == sorted(num) and num[0] == min(dd), num[:5])

        # Orden Ventas: más reciente primero
        ir(pg, 'fin')
        fv = pg.evaluate("[...document.querySelectorAll('#pg_fv tr td:first-child')].map(td=>td.textContent)")
        crudo = pg.evaluate("[...S.v].sort((x,y)=>x.f<y.f?1:-1).slice(0,25).map(v=>fm(v.f))")
        check(f'{rol}: ventas con la más reciente primero', fv == crudo)

        # Ver más se conserva en re-render y se reinicia al cambiar de pestaña
        ir(pg, 'salud'); pg.locator('#pg_sh button.g').first.click(timeout=2000) if pg.locator('#pg_sh button.g').count() else None; pg.wait_for_timeout(100)
        pg.evaluate('render()'); pg.wait_for_timeout(100)
        a = filas(pg, '#pg_sh')
        ir(pg, 'fin'); ir(pg, 'salud')
        c = filas(pg, '#pg_sh')
        check(f'{rol}: Ver más se conserva al re-renderizar y vuelve a 25 al cambiar pestaña', (a, c) == (50, 25), (a, c))

        # Permisos: el peón no recibe botones de edición tras Ver más
        pg.locator('#pg_sr button.g').first.click(timeout=2000) if pg.locator('#pg_sr button.g').count() else None; pg.wait_for_timeout(100)
        ap = pg.locator('#pg_sr button[onclick^="ap("]').count()
        if rol == 'peon':
            check('peon: sin botones Aplicado hoy después de Ver más', ap == 0, ap)
        else:
            check('admin: con botones Aplicado hoy después de Ver más', ap == 50, ap)
        ir(pg, 'animales')
        reb = pg.evaluate("S.a.find(a=>a.e=='A').reb")
        pg.locator('#v input[aria-label="Buscar animal"]').fill(reb); pg.wait_for_timeout(150)
        check(f'{rol}: buscar por rebaño encuentra animales', filas(pg, '#al') > 0, reb)
        pg.locator('#v input[aria-label="Buscar animal"]').fill(''); pg.wait_for_timeout(150)
        pg.locator('#al button.g').first.click(timeout=2000) if pg.locator('#al button.g').count() else None; pg.wait_for_timeout(100)
        check(f'{rol}: foco queda en la lista tras Ver más de animales', pg.evaluate("!!document.activeElement.closest('#al')"))
        ir(pg, 'fin'); pg.locator('#pg_fg button.g').first.click(timeout=2000) if pg.locator('#pg_fg button.g').count() else None; pg.wait_for_timeout(100)
        check(f'{rol}: foco queda en la lista tras Ver más de gastos', pg.evaluate("!!document.activeElement.closest('#pg_fg')"))
        check(f'{rol}: paginación sin errores JS', not errs, errs)
        ctx.close()
        # Encabezado angosto con chip de pendientes (revisión #1)
        for w in (320, 360, 375):
            c2 = b.new_context(viewport={'width': w, 'height': 760}); q = c2.new_page()
            q.route('**/*', lambda r: r.continue_() if r.request.url.startswith('file:') else r.abort())
            q.goto(URL)
            q.evaluate("r=>{localStorage.clear();localStorage.setItem('ses',JSON.stringify({token:'x',user:'u1',finca:'f1',rol:r,fnom:'Cortijo Las Cumbres',usuario:'n'}));localStorage.setItem('cortijo1_u1',JSON.stringify(seed()))}", rol)
            q.reload(); q.wait_for_timeout(600); q.evaluate('setP(3);chip()'); q.wait_for_timeout(100)
            sw = q.evaluate('document.documentElement.scrollWidth')
            vis = q.evaluate("(()=>{const r=document.querySelector('#thb').getBoundingClientRect();return r.width>0&&r.right<=innerWidth})()")
            check(f'{rol}: encabezado cabe en {w}px con chip y botón de tema visible', sw <= w and vis, (sw, vis))
            sol = q.evaluate("(()=>{const h=[...document.querySelectorAll('header>*')].filter(e=>e.getBoundingClientRect().width>0).map(e=>{const r=e.getBoundingClientRect();return[r.left,r.right]});let m=0;for(let i=1;i<h.length;i++)m=Math.max(m,h[i-1][1]-h[i][0]);const d=document.querySelector('header>div');return Math.max(m,d.scrollWidth-d.clientWidth)})()")
            check(f'{rol}: en {w}px nada del encabezado se encima', sol <= 1, sol)
            c2.close()
    b.close()

fallas = [r for r in RES if not r[1]]
for n, ok, d in RES:
    print(('PASS ' if ok else 'FAIL ') + n + ('' if ok else f'  -> {d}'))
print(f'\n{len(RES) - len(fallas)}/{len(RES)} pasan')
sys.exit(1 if fallas else 0)
