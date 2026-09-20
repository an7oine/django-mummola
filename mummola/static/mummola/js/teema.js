"use strict";

/**
 * Aseta Bootstrapin `data-bs-theme` selaimen prefers-color-scheme -kyselyn mukaan.
 */
(function () {
  const tumma = window.matchMedia("(prefers-color-scheme: dark)");

  /**
   * Päivitä juurielementin teema: dark tai light.
   */
  function asetaTeema () {
    document.documentElement.dataset.bsTheme = (
      tumma.matches ? "dark" : "light"
    );
  }

  tumma.addEventListener("change", asetaTeema);
  asetaTeema();
})();
