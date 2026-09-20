/**
 * Selainajuri jaksonvaihdon rullaustestille (`test_rullaus.py`).
 *
 * Ajaa kalenterisivulla puhelimen kokoisella ruudulla sarjan kosketus-
 * eleitä ja mittaa kunkin jälkeen jakson nimikkeen muutokset, liuku-
 * animaatiot, niistä jääneet jäljennökset sekä rullaimen paikan suhteessa
 * lähtökohtaan ja pehmusteisiin.
 * Tulokset tulostetaan yhtenä JSON-rivinä: `TULOS {...}`.
 *
 * Käyttö: node rullaus.js <osoite> <tunnus> <salasana>
 */

"use strict";

const {avaa, lue, odota} = require("./mittari");

const [, , OSOITE, TUNNUS, SALASANA] = process.argv;
// Oletuksena puhelimen kokoinen ruutu; muun koon voi antaa
// ympäristömuuttujilla.
const LEVEYS = Number(process.env.MUMMOLA_LEVEYS) || 390;
const KORKEUS = Number(process.env.MUMMOLA_KORKEUS) || 700;

(async () => {
  const {selain, sivu, cdp, virheet} = await avaa({
    osoite: OSOITE, tunnus: TUNNUS, salasana: SALASANA,
    leveys: LEVEYS, korkeus: KORKEUS, kosketus: true,
  });

  /**
   * Pyyhkäise: matka < 0 alas (seuraava jakso), > 0 ylös (edellinen).
   * `esta` tekee eleestä hitaan vedon ilman heittoa.
   */
  const ele = (matka, nopeus, esta) => cdp.send(
    "Input.synthesizeScrollGesture",
    {
      x: Math.round(LEVEYS / 2), y: Math.round(KORKEUS / 2),
      yDistance: matka, speed: nopeus || 3000,
      gestureSourceType: "touch", preventFling: !! esta,
    }
  );
  const nollaa = async () => {
    await sivu.evaluate(() => window.mummolaNollaa());
  };

  const tulos = {};

  // 1. Lepo: sivu jätetään rauhaan. Jakso ei saa vaihtua itsestään.
  await odota(1500);
  tulos.lepo = await sivu.evaluate(lue);

  // 2. Pieni veto ilman heittoa: ei ylitä kynnystä, joten jakso pysyy.
  await nollaa();
  await ele(-24, 500, true);
  const pieniHeti = await sivu.evaluate(lue);
  await odota(1500);
  tulos.pieni = await sivu.evaluate(lue);
  // Mihin ele ehti ennen ratkaisua: kertoo kynnyksen ylittymisestä.
  tulos.pieni.heti = pieniHeti.kohta - pieniHeti.lahtokohta;

  // 3. Kynnyksen ylittävä veto ilman heittoa: jakso vaihtuu kerran.
  await nollaa();
  await ele(-160, 700, true);
  await odota(1500);
  tulos.kynnyksenYli = await sivu.evaluate(lue);

  // 4. Seuraava ja heti perään edellinen: takaisin lähtöviikkoon.
  await nollaa();
  await ele(-4000);
  await odota(1400);
  const valiSeuraava = await sivu.evaluate(lue);
  await ele(4000);
  await odota(1400);
  tulos.seuraavaEdellinen = await sivu.evaluate(lue);
  tulos.seuraavaEdellinen.valinimike = valiSeuraava.nimike;

  // 5. Sama toisin päin.
  await nollaa();
  await ele(4000);
  await odota(1400);
  const valiEdellinen = await sivu.evaluate(lue);
  await ele(-4000);
  await odota(1400);
  tulos.edellinenSeuraava = await sivu.evaluate(lue);
  tulos.edellinenSeuraava.valinimike = valiEdellinen.nimike;

  // 6. Nopea sarja: toinen ele alkaa kesken liu'un (animaatio 260 ms).
  await nollaa();
  await ele(-4000);
  await odota(120);
  await ele(4000);
  await odota(2000);
  tulos.nopea = await sivu.evaluate(lue);

  // 7. Nopea sarja toisin päin.
  await nollaa();
  await ele(4000);
  await odota(120);
  await ele(-4000);
  await odota(2000);
  tulos.nopeaToisinpain = await sivu.evaluate(lue);

  tulos.virheet = virheet;
  await selain.close();
  console.log("TULOS " + JSON.stringify(tulos));
})().catch(virhe => {
  console.error(virhe && virhe.stack || String(virhe));
  process.exit(1);
});
