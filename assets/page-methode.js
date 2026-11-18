/* ============================================================================
   MÉTHODE — suivre une ancre collée dans la barre d'adresse.

   Le sommaire de la page est fait de liens « # » ordinaires : un clic fonctionne
   sans script, et c'est le cas courant. Mais une adresse collée depuis un courriel
   (/methode#poids) arrive avant que Dash n'ait rendu le document : la section
   n'existe pas encore et le navigateur n'a rien à viser. Ce fichier rattrape ce
   seul cas, puis se tait.

   Rien d'autre : pas de bibliothèque, pas de surlignage de section au défilement,
   pas de script en ligne (la CSP du produit est script-src 'self').
   ============================================================================ */
(function () {
  "use strict";

  function surMethode() {
    return document.location.pathname.replace(/\/+$/, "") === "/methode";
  }

  function cible() {
    var hash = document.location.hash || "";
    if (hash.length < 2 || !surMethode()) {
      return null;
    }
    return document.getElementById(decodeURIComponent(hash.slice(1)));
  }

  function viser() {
    var section = cible();
    if (section) {
      section.scrollIntoView();  // scroll-margin-top vient de assets/page-methode.css
    }
  }

  function demarrer() {
    if (!surMethode() || (document.location.hash || "").length < 2) {
      return;  // rien à viser : aucune surveillance, aucun coût sur les autres pages
    }
    var attente = null;
    // Le document se rend par morceaux : viser au premier morceau placerait la section
    // trop haut. On vise 200 ms après la dernière modification, donc une fois posé.
    var observateur = new MutationObserver(function () {
      window.clearTimeout(attente);
      attente = window.setTimeout(viser, 200);
    });

    function renoncer() {
      observateur.disconnect();
      window.clearTimeout(attente);
    }

    observateur.observe(document.body, { childList: true, subtree: true });
    // le lecteur reprend la main dès qu'il touche quoi que ce soit, et la surveillance
    // ne survit de toute façon pas au rendu de la page
    ["wheel", "touchstart", "keydown", "mousedown"].forEach(function (evenement) {
      window.addEventListener(evenement, renoncer, { once: true, passive: true });
    });
    window.setTimeout(renoncer, 8000);
    viser();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", demarrer);
  } else {
    demarrer();
  }
})();
