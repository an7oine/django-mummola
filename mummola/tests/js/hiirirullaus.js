/**
 * Selainajuri työpöydän hiirirullalle (`test_rullaus.py`).
 *
 * Työpöytäleveydellä rulla liikuttaa ensin tuntiruudukon omaa vieritystä
 * ja vasta sen reunassa ulompaa rullainta, joka vaihtaa jakson. Ajuri
 * toistaa saman rullauksen monta kertaa peräkkäin ja kirjaa jokaisen
 * jälkeen, vaihtuiko jakso – näin paljastuu, jäikö siirtyminen jumiin
 * ensimmäisen vaihdon jälkeen.
 *
 * Käyttö: node hiirirullaus.js <osoite> <tunnus> <salasana>
 */

"use strict";

const {avaa, lue, odota} = require("./mittari");

const [, , OSOITE, TUNNUS, SALASANA] = process.argv;
const LEVEYS = Number(process.env.MUMMOLA_LEVEYS) || 1280;
const KORKEUS = Number(process.env.MUMMOLA_KORKEUS) || 900;

// Yhdellä rullauksella tehtävien pyöräytysten määrä ja matka. Yksi
// pyöräytys vastaa hiiren rullan yhtä loksahdusta.
const PYORAYTYKSIA = 8;
const PYORAYTYS = 120;

(async () => {
  const {selain, sivu, cdp, virheet} = await avaa({
    osoite: OSOITE, tunnus: TUNNUS, salasana: SALASANA,
    leveys: LEVEYS, korkeus: KORKEUS, kosketus: false,
  });

  const x = Math.round(LEVEYS / 2);
  const y = Math.round(KORKEUS / 2);

  /** Pyöräytä hiiren rullaa: suunta -1 ylös, 1 alas. */
  const rulla = async suunta => {
    for (let i = 0; i < PYORAYTYKSIA; i++) {
      await cdp.send("Input.dispatchMouseEvent", {
        type: "mouseWheel", x, y,
        deltaX: 0, deltaY: suunta * PYORAYTYS,
      });
      await odota(40);
    }
  };

  /** Rullaa annettuun suuntaan ja lue tila liikkeen asetuttua. */
  const vaihe = async (suunta, nimi) => {
    await sivu.evaluate(() => window.mummolaNollaa());
    await rulla(suunta);
    await odota(1400);
    const tila = await sivu.evaluate(lue);
    tila.suunta = suunta;
    tila.nimi = nimi;
    return tila;
  };

  // Ylös kunnes jakso vaihtuu kertaalleen, sitten vuorotellen molempiin
  // suuntiin: jokaisen rullauksen pitäisi vaihtaa jakso kertaalleen.
  const vaiheet = [];
  vaiheet.push(await vaihe(-1, "ylos-1"));
  vaiheet.push(await vaihe(-1, "ylos-2"));
  vaiheet.push(await vaihe(1, "alas-1"));
  vaiheet.push(await vaihe(1, "alas-2"));
  vaiheet.push(await vaihe(-1, "ylos-3"));

  // Yhtäjaksoinen rullaus ilman taukoja: jakson vaihduttua kerran
  // siirtymisen pitää yhä jatkua, ei jäädä vain keskittämään näkymää.
  await sivu.evaluate(() => window.mummolaNollaa());
  for (let i = 0; i < 40; i++) {
    await cdp.send("Input.dispatchMouseEvent", {
      type: "mouseWheel", x, y, deltaX: 0, deltaY: -PYORAYTYS,
    });
    await odota(60);
  }
  await odota(1400);
  const yhtajaksoinen = await sivu.evaluate(lue);
  yhtajaksoinen.suunta = -1;
  yhtajaksoinen.nimi = "yhtajaksoinen";

  await selain.close();
  console.log("TULOS " + JSON.stringify({vaiheet, yhtajaksoinen, virheet}));
})().catch(virhe => {
  console.error(virhe && virhe.stack || String(virhe));
  process.exit(1);
});
