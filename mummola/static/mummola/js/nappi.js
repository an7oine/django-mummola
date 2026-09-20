"use strict";

/**
 * Painikkeiden odotustila: estää toistuvat napsautukset ja näyttää
 * Bootstrap-spinnerin, kunnes palautettu vapautusfunktio kutsutaan.
 */
(function () {
  /**
   * Lukitse painike odotustilaan. Palauta vapautusfunktio, tai `null`
   * jos painike on jo odottamassa.
   *
   * `asetukset.spinner === false` jättää indikaattorin pois (ryhmän
   * muut painikkeet lukitaan ilman spinneriä).
   */
  function lukitse (nappi, asetukset) {
    if (! nappi || nappi.dataset.mummolaOdottaa)
      return null;
    nappi.dataset.mummolaOdottaa = "1";
    if (nappi.disabled)
      nappi.dataset.mummolaOliDisabled = "1";
    nappi.disabled = true;
    nappi.setAttribute("aria-busy", "true");

    let spinner = null;
    if (asetukset?.spinner !== false) {
      spinner = document.createElement("span");
      spinner.className = "spinner-border spinner-border-sm mummola-odotus";
      spinner.setAttribute("aria-hidden", "true");
      nappi.insertBefore(spinner, nappi.firstChild);
    }

    return function vapauta () {
      spinner?.remove();
      nappi.removeAttribute("aria-busy");
      delete nappi.dataset.mummolaOdottaa;
      nappi.disabled = nappi.dataset.mummolaOliDisabled === "1";
      delete nappi.dataset.mummolaOliDisabled;
    };
  }

  /**
   * Lukitse painikeryhmä; spinner vain `aktiivinen`-painikkeessa.
   */
  function lukitseRyhma (napit, aktiivinen) {
    let joukko = [...napit];
    if (joukko.some(function (nappi) {
      return nappi.dataset.mummolaOdottaa;
    }))
      return null;
    let vapautukset = joukko.map(function (nappi) {
      return lukitse(nappi, {spinner: nappi === aktiivinen});
    }).filter(Boolean);
    if (! vapautukset.length)
      return null;
    return function vapauta () {
      for (let fn of vapautukset)
        fn();
    };
  }

  window.mummolaNappi = {lukitse, lukitseRyhma};

  /**
   * Sivun vaihtavat lomakkeet (kirjautuminen, uloskirjautuminen):
   * lukitse lähetysnappi. Ajax-lomakkeet merkitään `data-mummola-ajax`.
   */
  document.addEventListener("submit", function (e) {
    if (e.target.hasAttribute("data-mummola-ajax"))
      return;
    let nappi = e.submitter || e.target.querySelector("[type=submit]");
    lukitse(nappi);
  }, true);
})();
