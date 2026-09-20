/**
 * Yhteiset apurit kalenterin rullausta koettaville selainajureille.
 *
 * `avaa` käynnistää selaimen ja kirjautuu sisään, `mittari` kirjaa sivulla
 * tapahtuvat jaksonvaihdot ja liu'ut, ja `lue` palauttaa rullaimen tilan.
 */

"use strict";

const puppeteer = require("puppeteer-core");

const odota = ms => new Promise(r => setTimeout(r, ms));

/**
 * Kirjaa sivulla tapahtuvat jaksonvaihdot, liu'ut ja jäljennökset.
 * Ajetaan selaimessa kerran sivun latauduttua.
 */
function mittari () {
  const kehys = document.querySelector(".mummola-kehys");
  const nimike = document.querySelector("[data-mummola-nimike]");
  const mittaus = {nimikkeet: [nimike.textContent.trim()], liukuja: 0};
  window.mummolaMittaus = mittaus;

  window.mummolaNollaa = function () {
    mittaus.nimikkeet = [nimike.textContent.trim()];
    mittaus.liukuja = 0;
  };

  new MutationObserver(function () {
    const teksti = nimike.textContent.trim();
    if (teksti && teksti !== mittaus.nimikkeet[mittaus.nimikkeet.length - 1])
      mittaus.nimikkeet.push(teksti);
  }).observe(nimike, {childList: true, characterData: true, subtree: true});

  new MutationObserver(function (muutokset) {
    for (const muutos of muutokset)
      if (muutos.attributeName === "data-vaihtuu" && kehys.dataset.vaihtuu)
        mittaus.liukuja += 1;
  }).observe(kehys, {attributes: true});
}

/**
 * Lue rullaimen tila: geometria, lähtökohta ja kirjatut tapahtumat.
 * `lahtokohta` lasketaan tässä itsenäisesti, jotta testi vertaa
 * toteutusta odotukseen eikä itseensä.
 */
function lue () {
  const rullain = document.querySelector(".mummola-rullain");
  const kalenteri = document.querySelector("#mummola");
  const kehys = document.querySelector(".mummola-kehys");
  const mittaus = window.mummolaMittaus;

  const ylaraja = kalenteri.offsetTop;
  const alaraja = Math.max(
    ylaraja, ylaraja + kalenteri.offsetHeight - rullain.clientHeight
  );
  const otsake = kalenteri.querySelector(".fc-col-header");
  const solu = otsake && (otsake.closest("th, td") || otsake);
  const tarttuva = solu && getComputedStyle(solu).position === "sticky"
    ? otsake.offsetHeight
    : 0;
  const rivi = kalenteri.querySelector(
    '.fc-timegrid-slots [data-time="08:00:00"]'
  );
  const lahtokohta = rivi
    ? Math.min(alaraja, Math.max(ylaraja, ylaraja + Math.round(
      rivi.getBoundingClientRect().top
      - kalenteri.getBoundingClientRect().top
      - tarttuva
    )))
    : ylaraja;

  // Tuntiruudukon oma vieritys: työpöydällä rulla liikuttaa ensin sitä
  // ja vasta sen reunassa ulompaa rullainta.
  const ruudukko = kalenteri.querySelector(
    ".fc-timegrid-body"
  )?.closest(".fc-scroller");

  const kohta = Math.round(rullain.scrollTop);
  return {
    nimike: mittaus.nimikkeet[mittaus.nimikkeet.length - 1],
    nimikkeet: mittaus.nimikkeet.slice(),
    muutoksia: mittaus.nimikkeet.length - 1,
    liukuja: mittaus.liukuja,
    // Liu'usta jäänyt kuva vanhasta jaksosta; pitää siivoutua aina.
    jaljennoksia: document.querySelectorAll(".mummola-jaljennos").length,
    liukuKesken: !! kehys.dataset.vaihtuu,
    kohta,
    lahtokohta,
    poikkeama: kohta - lahtokohta,
    ylaraja,
    alaraja,
    ylapehmuste: ylaraja,
    alapehmuste: (rullain.scrollHeight - rullain.clientHeight) - alaraja,
    // Missä rullain lepää: sisällössä vai kumman pehmusteen puolella.
    paikka: kohta < ylaraja - 1
      ? "ylapehmuste"
      : kohta > alaraja + 1 ? "alapehmuste" : "sisalto",
    nuoliYlos: kehys.style.getPropertyValue("--mummola-ylos").trim(),
    nuoliAlas: kehys.style.getPropertyValue("--mummola-alas").trim(),
    ruudukonKohta: ruudukko ? Math.round(ruudukko.scrollTop) : null,
    ruudukonVara: ruudukko
      ? Math.round(ruudukko.scrollHeight - ruudukko.clientHeight)
      : null,
  };
}

/**
 * Avaa kalenterisivu kirjautuneena ja kytke mittari.
 *
 * Palauttaa selaimen, sivun, CDP-istunnon sekä listan sivulla sattuneista
 * JS-poikkeuksista.
 */
async function avaa ({osoite, tunnus, salasana, leveys, korkeus, kosketus}) {
  const selain = await puppeteer.launch({
    executablePath: process.env.MUMMOLA_SELAIN,
    headless: "new",
    args: ["--no-sandbox"],
  });
  const sivu = await selain.newPage();
  const virheet = [];
  sivu.on("pageerror", virhe => virheet.push(virhe.message));
  await sivu.setViewport({
    width: leveys, height: korkeus, deviceScaleFactor: 1,
    hasTouch: !! kosketus, isMobile: !! kosketus,
  });

  await sivu.goto(osoite + "/mummola/", {waitUntil: "networkidle0"});
  if (await sivu.$("input[name=password]")) {
    await sivu.type("input[name=username]", tunnus);
    await sivu.type("input[name=password]", salasana);
    await Promise.all([
      sivu.waitForNavigation({waitUntil: "networkidle0"}),
      sivu.click("button[type=submit]"),
    ]);
  }
  await sivu.waitForSelector("#mummola .fc-timegrid-slots");
  // Kalenteri asettuu lähtökohtaansa vasta tapahtumien piirryttyä.
  await odota(2000);
  await sivu.evaluate(mittari);

  const cdp = await sivu.createCDPSession();
  return {selain, sivu, cdp, virheet};
}

module.exports = {avaa, lue, mittari, odota};
