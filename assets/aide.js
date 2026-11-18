/* Infobulles d'aide ([data-aide] : icône .aide, carte KPI .kpi-info, libellé .terme-aide) : survol sur ordinateur, toucher sur mobile, clavier (Tab, Entrée, Échap).
   Une seule bulle, positionnée en fixed sur la page (jamais coupée par un bloc), texte inséré par textContent. */
(function () {
  var bulle = null, cible = null, epinglee = false;
  var META = /^(Unité|Sens|Source|Lecture) : ([\s\S]*)$/;
  function creer() {
    bulle = document.createElement('div');
    bulle.id = 'bulle-aide';
    bulle.setAttribute('role', 'tooltip');
    document.body.appendChild(bulle);
  }
  function remplir(t) {
    bulle.textContent = '';
    t.split('\n').forEach(function (l, i) {
      var d = document.createElement('div'), m = l.match(META);
      if (m) {
        var b = document.createElement('span');
        b.className = 'b-lib';
        b.textContent = m[1] + ' : ';
        d.appendChild(b);
        d.appendChild(document.createTextNode(m[2]));
        d.className = 'b-meta';
      } else {
        d.textContent = l;
        d.className = i === 0 ? 'b-def' : 'b-meta';
      }
      bulle.appendChild(d);
    });
  }
  function placer(el) {
    if (!document.body.contains(el)) { cacher(); return; }
    var r = el.getBoundingClientRect(), vw = window.innerWidth, vh = window.innerHeight;
    bulle.style.maxWidth = Math.min(330, vw - 16) + 'px';
    bulle.style.left = '0px'; bulle.style.top = '0px';
    var bw = bulle.offsetWidth, bh = bulle.offsetHeight;
    var x = Math.max(8, Math.min(r.left + r.width / 2 - bw / 2, vw - bw - 8));
    var y = r.bottom + 6;
    if (y + bh > vh - 8) { y = r.top - bh - 6; }
    if (y < 8) { y = Math.max(8, Math.min(r.bottom + 6, vh - bh - 8)); }
    bulle.style.left = Math.round(x) + 'px'; bulle.style.top = Math.round(y) + 'px';
  }
  /* L'état n'est posé que sur un élément qui s'est déclaré commande (role + aria-expanded dans le
     HTML) : aria-expanded sur un <div> ou un <span> nu ne veut rien dire pour un lecteur d'écran.
     Quand la bulle est ouverte, la commande la désigne par aria-describedby — c'est ce qui fait
     lire le texte de la bulle au clavier. */
  function ouvrir(el, ouverte) {
    if (!el.hasAttribute('aria-expanded')) { return; }
    el.setAttribute('aria-expanded', ouverte ? 'true' : 'false');
    if (ouverte) { el.setAttribute('aria-describedby', 'bulle-aide'); }
    else { el.removeAttribute('aria-describedby'); }
  }
  function montrer(el, epingler) {
    if (!bulle) { creer(); }
    if (cible && cible !== el) { ouvrir(cible, false); }
    remplir(el.getAttribute('data-aide') || '');
    bulle.classList.add('visible');
    cible = el; epinglee = !!epingler;
    ouvrir(el, true);
    placer(el);
  }
  function cacher() {
    if (bulle) { bulle.classList.remove('visible'); }
    if (cible) { ouvrir(cible, false); }
    cible = null; epinglee = false;
  }
  function aideDe(e) { return e.target && e.target.closest ? e.target.closest('[data-aide]') : null; }
  document.addEventListener('mouseover', function (e) { var el = aideDe(e); if (el && !epinglee) { montrer(el, false); } });
  document.addEventListener('mouseout', function (e) {
    var el = aideDe(e);
    if (el && !epinglee && el === cible && !(e.relatedTarget && el.contains(e.relatedTarget))) { cacher(); }
  });
  /* toucher ou clic : épingle la bulle ; second toucher sur la même icône ou ailleurs : la ferme */
  document.addEventListener('click', function (e) {
    var el = aideDe(e);
    if (el) {
      e.preventDefault(); e.stopPropagation();
      if (cible === el && epinglee) { cacher(); } else { montrer(el, true); }
      return;
    }
    if (epinglee) { cacher(); }
  }, true);
  document.addEventListener('focusin', function (e) { var el = aideDe(e); if (el && !epinglee) { montrer(el, false); } });
  document.addEventListener('focusout', function (e) { var el = aideDe(e); if (el && el === cible && !epinglee) { cacher(); } });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { cacher(); return; }
    var el = aideDe(e);
    if (el && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); montrer(el, !epinglee || cible !== el); }
  });
  window.addEventListener('scroll', function () { if (cible) { placer(cible); } }, true);
  window.addEventListener('resize', function () { if (cible) { placer(cible); } });
})();

/* Feuille de navigation mobile (sous 992 px) : la bascule 44×44 ouvre les onglets sous l'entête.
   Contrat de focus : l'ouverture porte le focus sur le premier élément,
   Échap et un clic à l'extérieur referment et rendent le focus à la bascule. L'état ouvert/fermé
   appartient à Dash (callback « bascule ») : on le lit sur la classe, on ne le duplique pas. */
(function () {
  var observateur = null, surveille = null, etait = false;
  function bascule() { return document.getElementById('nav-bascule'); }
  function menu() { return document.getElementById('nav-menu'); }
  function ouvert() { var m = menu(); return !!(m && m.classList.contains('show')); }
  function fermer() {
    var t = bascule();
    if (t && ouvert()) { t.click(); t.focus(); }
  }
  function synchroniser() {
    var t = bascule(), o = ouvert();
    if (!t) { return; }
    t.setAttribute('aria-expanded', o ? 'true' : 'false');
    t.setAttribute('aria-controls', 'nav-menu');
    t.setAttribute('aria-label', o ? 'Fermer le menu' : 'Ouvrir le menu');
    if (o && !etait) {
      var premier = menu().querySelector('a, button');
      if (premier) { premier.focus(); }
    }
    etait = o;
  }
  function brancher() {
    var m = menu();
    if (!m || m === surveille) { return; }
    surveille = m;
    if (observateur) { observateur.disconnect(); }
    observateur = new MutationObserver(synchroniser);
    observateur.observe(m, { attributes: true, attributeFilter: ['class'] });
    synchroniser();
  }
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') { fermer(); } });
  document.addEventListener('click', function (e) {
    if (!ouvert()) { return; }
    var m = menu(), t = bascule();
    if (!m || !t) { return; }
    if (!m.contains(e.target) && !t.contains(e.target)) { t.click(); return; }
    /* Un onglet choisi referme la feuille : elle ne doit pas rester posée sur la page suivante.
       Une commande qui ouvre quelque chose DANS la feuille (un sous-menu) n'est pas un onglet :
       la refermer rendrait son contenu inatteignable au doigt. */
    var lien = m.contains(e.target) && e.target.closest ? e.target.closest('a, button') : null;
    if (lien && !lien.hasAttribute('aria-expanded') && !lien.classList.contains('dropdown-toggle')) { t.click(); }
  });
  var attente = setInterval(function () { brancher(); if (surveille) { clearInterval(attente); } }, 300);
  document.addEventListener('DOMContentLoaded', brancher);
})();
