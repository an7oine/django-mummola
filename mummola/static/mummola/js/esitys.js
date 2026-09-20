"use strict";

/**
 * Mummolan FullCalendar-esitys: varaukset, päivänapsautus ja lomake.
 */
(function () {
  /**
   * Palauta merkkijono HTML-entiteeteiksi koodattuna.
   */
  function escapeHTML(str) {
    return new Option(str ?? "").innerHTML;
  }

  /**
   * Lue CSRF-avain evästeestä POST-pyyntöjä varten.
   */
  function poimiCsrf () {
    return document.cookie.split(";").map(function (c) {
      return c.trim();
    }).filter(function (c) {
      return c.startsWith("csrftoken=");
    }).reduce(function (__, c) {
      return decodeURIComponent(c.substring(10));
    }, "");
  }

  /**
   * Muotoile Date datetime-local-kentän arvoksi (paikallinen aika).
   */
  function paikalliseenKenttaan (aika) {
    if (! aika)
      return "";
    let pvm = new Date(aika.getTime() - aika.getTimezoneOffset() * 60000);
    return pvm.toISOString().slice(0, 16);
  }

  /**
   * Näytä tai piilota varauslomakkeen virheilmoitus.
   */
  function naytaVirhe (teksti) {
    let virheEl = document.getElementById("varaus-virhe");
    virheEl.textContent = teksti;
    virheEl.classList.toggle("d-none", ! teksti);
  }

  /**
   * Lukitse tai avaa lomakekentät ja tallennusnappi.
   */
  function asetaKentatKaytossa (lomake, kaytossa) {
    for (let kentta of lomake.querySelectorAll(
      "input:not([type=hidden]), select, textarea"
    ))
      kentta.disabled = ! kaytossa;
    document.getElementById("varaus-tallenna").hidden = ! kaytossa;
  }

  /**
   * Avaa varausmodaali uutena varauksena tai olemassa olevan muokkauksena.
   */
  function avaaVarauslomake (alku, loppu, varaus) {
    let lomake = document.getElementById("varaus-lomake");
    lomake.reset();
    naytaVirhe("");
    lomake.elements.pk.value = varaus?.id ?? "";
    document.getElementById("varaus-lomake-otsikko").textContent = (
      varaus ? "Muokkaa varausta" : "Uusi varaus"
    );
    document.getElementById("varaus-tallenna").textContent = (
      varaus ? "Tallenna" : "Varaa"
    );

    let tekijaRyhma = document.getElementById("varaus-tekija-ryhma");
    tekijaRyhma.classList.toggle("d-none", ! varaus);

    // Poistaa voi vain oman, jo tallennetun varauksen.
    document.getElementById("varaus-poista").classList.toggle(
      "d-none", ! varaus?.extendedProps?.oma
    );

    if (varaus) {
      let tiedot = varaus.extendedProps ?? {};
      lomake.elements.alku.value = tiedot.alku ?? paikalliseenKenttaan(
        varaus.start
      );
      lomake.elements.loppu.value = tiedot.loppu ?? paikalliseenKenttaan(
        varaus.end
      );
      lomake.elements.sijainti.value = tiedot.sijainti ?? "";
      lomake.elements.tarkeys.value = tiedot.tarkeys ?? "";
      lomake.elements.lapset.value = tiedot.lapset ?? 0;
      lomake.elements.aikuiset.value = tiedot.aikuiset ?? 0;
      lomake.elements.koirat.value = tiedot.koirat ?? 0;
      lomake.elements.kuvaus.value = tiedot.kuvaus ?? "";
      lomake.elements.tekija.value = tiedot.tekija_id ?? "";
      asetaKentatKaytossa(lomake, !! tiedot.oma);
    }
    else {
      lomake.elements.alku.value = paikalliseenKenttaan(alku);
      lomake.elements.loppu.value = paikalliseenKenttaan(loppu);
      asetaKentatKaytossa(lomake, true);
      lomake.elements.tekija.disabled = true;
    }

    bootstrap.Modal.getOrCreateInstance(
      document.getElementById("varaus-modaali")
    ).show();
    if (! lomake.elements.sijainti.disabled)
      lomake.elements.sijainti.focus();
  }

  /**
   * Rakenna yksi osallistujamerkki: symboli ja kpl-määrä.
   *
   * Asemointi (päällekkäin tai allekkain) hoidetaan CSS:llä näytön
   * leveyden mukaan.
   */
  function osallistujamerkki (symboli, maara) {
    let merkki = document.createElement("span");
    merkki.className = "mummola-osallistuja";

    let symboliEl = document.createElement("span");
    symboliEl.className = "mummola-symboli";
    symboliEl.textContent = symboli;

    let maaraEl = document.createElement("span");
    maaraEl.className = "mummola-maara";
    maaraEl.textContent = maara;

    merkki.append(symboliEl, maaraEl);
    return merkki;
  }

  /**
   * Piirrä päiväotsakkeisiin osallistujamäärät: 👶/🧑/🐶 + kpl, jos ≥ 1.
   */
  function paivitaOsallistujamerkinnat (kalenteri) {
    if (! kalenteri)
      return;
    let tapahtumat = kalenteri.getEvents();
    // Viikko-/päivänäkymässä vain sarakeotsake (pvm); kuukausinäkymässä
    // päiväsolu. Koko päivä -rivin `.fc-daygrid-day` jätetään pois.
    for (let solu of kalenteri.el.querySelectorAll(
      ".fc-col-header-cell[data-date], "
      + ".fc-dayGridMonth-view .fc-daygrid-day"
    )) {
      let pvm = solu.dataset.date;
      let yla = solu.querySelector(
        ".fc-daygrid-day-top, .fc-col-header-cell-cushion"
      ) || solu;
      if (! pvm || ! yla)
        continue;

      let paivaAlku = new Date(pvm + "T00:00:00");
      let paivaLoppu = new Date(paivaAlku);
      paivaLoppu.setDate(paivaLoppu.getDate() + 1);

      let lapset = 0, aikuiset = 0, koirat = 0;
      for (let tapahtuma of tapahtumat) {
        let alku = tapahtuma.start;
        let loppu = tapahtuma.end ?? alku;
        if (alku < paivaLoppu && loppu > paivaAlku) {
          lapset += Number(tapahtuma.extendedProps.lapset) || 0;
          aikuiset += Number(tapahtuma.extendedProps.aikuiset) || 0;
          koirat += Number(tapahtuma.extendedProps.koirat) || 0;
        }
      }

      let merkit = yla.querySelector(".mummola-osallistujat");
      if (! merkit) {
        merkit = document.createElement("span");
        merkit.className = "mummola-osallistujat";
        yla.appendChild(merkit);
      }
      merkit.replaceChildren();
      let otsikko = [];
      for (let [symboli, maara, sana] of [
        ["👶", lapset, "lasta"],
        ["🧑", aikuiset, "aikuista"],
        ["🐶", koirat, "koiraa"]
      ]) {
        if (maara < 1)
          continue;
        otsikko.push(maara + " " + sana);
        merkit.appendChild(osallistujamerkki(symboli, maara));
      }
      merkit.hidden = otsikko.length === 0;
      merkit.title = otsikko.join(", ");
    }
  }

  /**
   * Kytke rullaimen ulkopuolinen työkalupalkki: jakson nimike, Tänään-
   * painike ja näkymävalitsin. Palkki pysyy paikallaan rullattaessa.
   */
  function kytkePalkki (kalenteri) {
    let kehys = kalenteri?.el?.closest(".mummola-kehys");
    if (! kehys)
      return;

    kehys.mummolaVapautaPalkki?.();
    kehys.mummolaVapautaPalkki = null;

    let nimike = kehys.querySelector("[data-mummola-nimike]");
    if (nimike)
      nimike.textContent = kalenteri.view.title;
    for (let nappi of kehys.querySelectorAll("[data-mummola-nakyma]"))
      nappi.classList.toggle(
        "active",
        nappi.dataset.mummolaNakyma === kalenteri.view.type
      );

    if (kehys.dataset.palkki)
      return;
    kehys.dataset.palkki = "1";

    /** Lukitse palkin painikkeet, kunnes `datesSet` vapauttaa ne. */
    let odotaPalkkia = function (nappi) {
      if (kehys.mummolaVapautaPalkki)
        return false;
      let vapauta = window.mummolaNappi.lukitseRyhma(
        kehys.querySelectorAll(".mummola-palkki button"),
        nappi
      );
      if (! vapauta)
        return false;
      let valmis = false;
      let lopeta = function () {
        if (valmis)
          return;
        valmis = true;
        clearTimeout(ajastin);
        vapauta();
        kehys.mummolaVapautaPalkki = null;
      };
      let ajastin = setTimeout(lopeta, 800);
      kehys.mummolaVapautaPalkki = lopeta;
      return true;
    };

    kehys.querySelector("[data-mummola-toiminto=today]")?.addEventListener(
      "click",
      function () {
        if (! odotaPalkkia(this))
          return;
        kalenteri.today();
      }
    );
    for (let nappi of kehys.querySelectorAll("[data-mummola-nakyma]"))
      nappi.addEventListener("click", function () {
        if (this.dataset.mummolaNakyma === kalenteri.view.type)
          return;
        if (! odotaPalkkia(this))
          return;
        kalenteri.changeView(this.dataset.mummolaNakyma);
      });
  }

  /**
   * Kerro reunanuolille, miten pitkälle pehmusteeseen on rullattu (0…1).
   */
  function paivitaNuolet (kehys, rullain, keskella) {
    let alaosa = rullain.scrollHeight - rullain.clientHeight - keskella;
    let osuus = function (matka, pituus) {
      return pituus > 0
        ? Math.min(1, Math.max(0, matka / pituus)).toFixed(3)
        : "0";
    };
    kehys.style.setProperty(
      "--mummola-ylos", osuus(keskella - rullain.scrollTop, keskella)
    );
    kehys.style.setProperty(
      "--mummola-alas", osuus(rullain.scrollTop - keskella, alaosa)
    );
  }

  /**
   * Jäljennä kalenterin nykyinen sisältö liukuvaksi kuvaksi rullaimen päälle.
   *
   * Jäljennös asetetaan siihen kohtaan, jossa sisältö juuri näkyy, ja se
   * saa kalenterin oman tuntivierityksen, jottei kuva hyppää alkuun.
   */
  function jaljenna (el, rullain, ylos, korkeus) {
    let jaljennos = el.cloneNode(true);
    jaljennos.removeAttribute("id");
    jaljennos.removeAttribute("data-solmu");
    jaljennos.removeAttribute("data-solmu-esitys");
    jaljennos.classList.add("mummola-jaljennos");
    jaljennos.setAttribute("aria-hidden", "true");
    jaljennos.style.top = (rullain.offsetTop + ylos) + "px";
    jaljennos.style.height = korkeus + "px";
    rullain.parentElement.appendChild(jaljennos);

    let lahteet = el.querySelectorAll(".fc-scroller");
    let kopiot = jaljennos.querySelectorAll(".fc-scroller");
    for (let i = 0; i < kopiot.length && i < lahteet.length; i++)
      kopiot[i].scrollTop = lahteet[i].scrollTop;

    return jaljennos;
  }

  /**
   * Vaihda näkymän jaksoa (päivä/viikko/kuukausi) rullaamalla ylös tai alas.
   *
   * Rullain tarttuu CSS:n scroll-snapilla joko kalenteriin tai sen ylä-
   * ja alapuoliseen pehmusteeseen: pieni rullan liike palautuu takaisin
   * kalenteriin, ja jakso vaihtuu vasta, kun rullaus jää pehmusteeseen.
   * Tuntiruudukko vierii ensin omaan reunaansa asti. Rullauksen suunnasta
   * ja etenemisestä kertoo reunassa venyvä nuoli.
   */
  function kytkeRullaus (kalenteri) {
    let rullain = kalenteri?.el?.closest(".mummola-rullain");
    let kehys = rullain?.closest(".mummola-kehys");
    if (! rullain || ! kehys)
      return;

    // Kytkennät ja rullauksen tila tehdään kertaalleen; myöhemmät
    // jaksonvaihdot vain siirtävät rullaimen lähtökohtaan.
    if (rullain.dataset.rullaus) {
      rullain.mummolaLahtoon();
      return;
    }
    rullain.dataset.rullaus = "1";

    /**
     * Pehmusteen korkeus eli kynnys, jonka yli rullaamalla jakso vaihtuu.
     * Kalenteri seuraa pehmustetta, joten sen paikka kertoo korkeuden.
     */
    let pehmuste = function () {
      return kalenteri.el.offsetTop;
    };

    /** Rullauskohta, jossa kalenterisisällön yläreuna on näkyvissä. */
    let ylaraja = pehmuste;

    /** Rullauskohta, jossa kalenterisisällön alareuna on näkyvissä. */
    let alaraja = function () {
      return Math.max(
        ylaraja(),
        ylaraja() + kalenteri.el.offsetHeight - rullain.clientHeight
      );
    };

    /**
     * Ylälaitaan tarttuvan sarakeotsakkeen korkeus. Kalenteri pitää
     * otsakkeen paikallaan rullattaessa, joten se peittää ylälaidan.
     */
    let tarttuva = function () {
      let otsake = kalenteri.el.querySelector(".fc-col-header");
      let solu = otsake?.closest("th, td") ?? otsake;
      return solu && getComputedStyle(solu).position === "sticky"
        ? otsake.offsetHeight
        : 0;
    };

    /**
     * Rullauskohta, josta jakso alkaa: tuntiruudukossa kello 8 heti
     * otsakkeen alla, muissa näkymissä sisällön yläreuna.
     */
    let lahtokohta = function () {
      let rivi = kalenteri.el.querySelector(
        '.fc-timegrid-slots [data-time="08:00:00"]'
      );
      if (! rivi)
        return ylaraja();
      let siirto = (
        rivi.getBoundingClientRect().top
        - kalenteri.el.getBoundingClientRect().top
        - tarttuva()
      );
      return Math.min(
        alaraja(),
        Math.max(ylaraja(), ylaraja() + Math.round(siirto))
      );
    };

    // Onko käyttäjän oma rullausele kesken? Jakso vaihtuu vain eleestä,
    // ei jaksonvaihdon jälkeen jääneestä loppuvauhdista, joka ei enää
    // tuota syötetapahtumia.
    let eleKaynnissa = false;

    // Viimeksi asetettu lähtökohta; null ennen ensimmäistä jaksoa.
    let asetettu = null;

    /**
     * Kynnys: näin pitkälle pehmusteeseen on rullattava, ennen kuin
     * jakso vaihtuu. Pienempi liike palautuu lähtökohtaan.
     */
    let kynnys = function () {
      return Math.max(24, pehmuste() / 3);
    };

    /**
     * Onko käynnissä oleva ele vienyt rullauksen kynnyksen yli:
     * -1 edelliseen jaksoon, 1 seuraavaan, 0 ei kumpaankaan.
     */
    let ylitys = function () {
      if (! eleKaynnissa || asetettu === null)
        return 0;
      if (rullain.scrollTop <= asetettu - kynnys())
        return -1;
      if (rullain.scrollTop >= asetettu + kynnys())
        return 1;
      return 0;
    };

    /** Siirrä rullain jakson lähtökohtaan jakson vaihduttua. */
    let keskita = function () {
      eleKaynnissa = false;
      asetettu = lahtokohta();
      rullain.scrollTo({top: asetettu, behavior: "instant"});
      paivitaNuolet(kehys, rullain, pehmuste());
    };

    /**
     * Tarkista lähtökohta uudelleen tapahtumien piirtymisen jälkeen:
     * koko päivä -rivin korkeus ja siten kello 8:n paikka selviää vasta
     * silloin, toisinaan vasta parin piirroksen päästä. Käyttäjän oma
     * rullaus jätetään rauhaan.
     */
    let lahtoAjastin = null;
    let tarkistaLahto = function (kertoja) {
      clearTimeout(lahtoAjastin);
      if (kehys.dataset.vaihtuu || asetettu === null)
        return;
      // Käyttäjän oma rullaus jätetään rauhaan; eleettä liikkeellä on
      // enää vaihtaneen eleen loppuvauhti, joka saa vaimentua.
      if (! eleKaynnissa) {
        asetettu = lahtokohta();
        if (rullain.scrollTop !== asetettu)
          rullain.scrollTo({top: asetettu, behavior: "instant"});
      }
      if (kertoja > 0)
        lahtoAjastin = setTimeout(function () {
          tarkistaLahto(kertoja - 1);
        }, 200);
    };

    rullain.mummolaLahtoon = keskita;
    rullain.mummolaTarkistaLahto = tarkistaLahto;
    keskita();

    // Mitoituksen hetki: heti sen jälkeen rullaimen paikka on asetettu
    // ohjelmallisesti, eikä sitä tule tulkita jaksonvaihdoksi.
    let mitoitettu = 0;

    /**
     * Mitoita kalenteri uudelleen ikkunan muuttuessa. Kännykän selaimessa
     * osoitepalkki piiloutuu ja paljastuu kesken käytön, jolloin vanha
     * rivikorkeus jättäisi ruudukolle oman vierityksen.
     */
    let mitoita = function () {
      mitoitettu = Date.now();
      kalenteri.updateSize();
      sovitaRuudukko(kalenteri);
      keskita();
    };

    /**
     * Merkitse käyttäjän ele käynnissä olevaksi.
     *
     * Merkintä uusitaan jokaisesta syötetapahtumasta, jotta tauoton
     * rullaus jatkuu jaksonvaihdon jälkeenkin. Kaappausvaiheessa,
     * jottei kalenterin oma käsittely estä kirjaamista.
     */
    let merkitseEle = function (tapahtuma) {
      // Pelkkä osoittimen liike ei ole ele; napin painaminen on
      // (esim. vierityspalkin raahaus).
      if (tapahtuma.type === "pointermove" && ! tapahtuma.buttons)
        return;
      eleKaynnissa = true;
    };
    for (let laji of [
      "pointerdown", "pointermove", "touchstart", "touchmove",
      "wheel", "keydown",
    ])
      rullain.addEventListener(
        laji, merkitseEle, {passive: true, capture: true}
      );

    let ajastin = null;
    let mitoitaPian = function () {
      clearTimeout(ajastin);
      ajastin = setTimeout(mitoita, 120);
    };
    window.addEventListener("resize", mitoitaPian);
    window.addEventListener("orientationchange", mitoitaPian);
    window.visualViewport?.addEventListener("resize", mitoitaPian);

    /**
     * Siirry edelliseen (-1) tai seuraavaan (+1) jaksoon.
     *
     * Rullattaessa alaspäin vanha sisältö liukuu ulos yläreunasta ja uusi
     * sisään alareunasta, ylöspäin rullattaessa toisin päin. Vanhasta
     * jätetään jäljennös liukumaan, koska kalenteri piirtää uuden jakson
     * samaan elementtiin; näin molemmat liikkuvat yhtä matkaa vierekkäin.
     */
    let jono = 0;
    let vaihdaJakso = function (suunta) {
      let vaihda = function () {
        // Jakson vaihto laukaisee `datesSet`-tapahtuman, joka keskittää.
        if (suunta > 0)
          kalenteri.next();
        else
          kalenteri.prev();
      };

      // Kesken liu'un tullut ele jää jonoon ja ajetaan liu'un päätyttyä.
      // Näin nopeasti peräkkäin tehdyt eleet eivät katoa, vaan esim.
      // eteen ja heti takaisin päätyy lähtöjaksoon.
      if (kehys.dataset.vaihtuu) {
        jono = suunta;
        return;
      }

      if (
        ! kalenteri.el.animate
        || window.matchMedia("(prefers-reduced-motion: reduce)").matches
      ) {
        vaihda();
        return;
      }

      // Rullain jäädytetään vaihdon ajaksi (ks. kalenteri.css), jottei
      // scroll-snap taistele animaation kanssa.
      kehys.dataset.vaihtuu = "1";
      let matka = kalenteri.el.offsetHeight;
      let alkuun = (
        kalenteri.el.getBoundingClientRect().top
        - rullain.getBoundingClientRect().top
      );
      let jaljennos = jaljenna(kalenteri.el, rullain, alkuun, matka);
      vaihda();

      // Uusi jakso aloittaa vanhan reunasta ja liukuu lähtökohtaansa;
      // matka on sama molemmille, joten sisällöt liikkuvat vierekkäin.
      let reuna = suunta > 0
        ? alkuun + matka
        : alkuun - kalenteri.el.offsetHeight;
      let tulo = reuna - (
        kalenteri.el.getBoundingClientRect().top
        - rullain.getBoundingClientRect().top
      );
      let liuku = {
        duration: 260,
        easing: "cubic-bezier(0.4, 0, 0.2, 1)",
        fill: "forwards"
      };
      let ulos = jaljennos.animate(
        [
          {transform: "translateY(0)"},
          {transform: `translateY(${-tulo}px)`}
        ],
        liuku
      );
      let sisaan = kalenteri.el.animate(
        [
          {transform: `translateY(${tulo}px)`},
          {transform: "translateY(0)"}
        ],
        liuku
      );
      Promise.allSettled([ulos.finished, sisaan.finished]).then(function () {
        jaljennos.remove();
        sisaan.cancel();
        delete kehys.dataset.vaihtuu;
        tarkistaLahto(2);
        if (jono) {
          let seuraava = jono;
          jono = 0;
          vaihdaJakso(seuraava);
        }
      });
    };

    /**
     * Ratkaise pehmusteeseen päättynyt rullaus: joko jakso vaihtuu tai
     * rullain palaa lähtökohtaansa. Rullaus ei jää lepäämään puolitiehen.
     */
    let tarkista = function () {
      // Mitoituksen jälkeen rullaimen paikka on asetettu ohjelmallisesti;
      // tarkistus siirtyy mitoituksen asetuttua.
      let mitoituksesta = Date.now() - mitoitettu;
      if (mitoituksesta < 500) {
        tarkistaPian(500 - mitoituksesta);
        return;
      }
      if (kehys.dataset.vaihtuu || asetettu === null)
        return;
      let suunta = ylitys();
      if (suunta)
        vaihdaJakso(suunta);
      else if (Math.abs(rullain.scrollTop - asetettu) > 1)
        rullain.scrollTo({top: asetettu, behavior: "smooth"});
    };

    // Rullauksen päättymisen tarkistus: ajastin nollautuu jokaisesta
    // rullauksesta, joten tarkistus osuu vasta liikkeen tauottua.
    let tarkistusAjastin = null;
    let tarkistaPian = function (viive) {
      clearTimeout(tarkistusAjastin);
      tarkistusAjastin = setTimeout(tarkista, viive);
    };

    rullain.addEventListener("scroll", function () {
      // Jakso vaihtuu heti kynnyksen ylityttyä: heiton päättymistä ei voi
      // jäädä odottamaan, sillä seuraava ele voi alkaa jo ennen sitä.
      let suunta = kehys.dataset.vaihtuu ? 0 : ylitys();
      if (suunta)
        vaihdaJakso(suunta);
      paivitaNuolet(kehys, rullain, asetettu ?? kalenteri.el.offsetTop);
      tarkistaPian(200);
    }, {passive: true});

    // `scrollend` puuttuu osasta selaimia eikä kaikissa laukea heiton
    // päätyttyä, joten ajastin on aina rinnalla.
    rullain.addEventListener("scrollend", tarkista);
  }

  /**
   * Onko näyttö kapea (kännykkä)? Tällöin koko vuorokausi mahtuu kerralla
   * ruutuun, jottei sormi osuisi kalenterin omaan tuntivieritykseen vaan
   * pyyhkäisy vaihtaisi suoraan jaksoa.
   */
  function kapeaNaytto () {
    return window.matchMedia("(max-width: 767.98px)").matches;
  }

  /**
   * Mitoita tuntiruudukon rivit kapealla näytöllä tarkalleen näkyvään
   * tilaan (`--mummola-slot`, ks. kalenteri.css).
   *
   * Ilman tätä ruudukolle jää oma vieritys, joka nappaa pyyhkäisyn eikä
   * jakso vaihdu. Korkeus lasketaan mitatusta tilasta, koska kalenterin
   * oma rivivenytys ei aina osu (esim. Safarin osoitepalkin liikkuessa).
   */
  function sovitaRuudukko (kalenteri) {
    let el = kalenteri?.el;
    if (! el)
      return;
    el.style.removeProperty("--mummola-slot");
    let taulu = el.querySelector(".fc-timegrid-slots table");
    let vieritin = taulu?.closest(".fc-scroller");
    let rivit = el.querySelectorAll(".fc-timegrid-slots tr").length;
    if (! kapeaNaytto() || ! vieritin || ! rivit)
      return;

    // Tuntitaulu alkaa vierittimen ylälaidasta, joten rivit jaetaan
    // tasan näkyvään korkeuteen (viimeinen reunaviiva pois lukien).
    el.style.setProperty(
      "--mummola-slot",
      Math.floor((vieritin.clientHeight - 1) / rivit) + "px"
    );
    // Kalenteri laskee tapahtumien ja taustojen paikat rivikorkeudesta,
    // joten se mitoitetaan muutoksen jälkeen uudelleen.
    kalenteri.updateSize();

    // Jos rivit eivät enää kutistu (tekstin vähimmäiskorkeus), ruudukko
    // saa poikkeuksellisesti oman vierityksensä – mieluummin niin kuin
    // että osa vuorokaudesta jäisi rajauksen alle piiloon.
    el.classList.toggle(
      "mummola-ruudukko-vierii",
      vieritin.scrollHeight > vieritin.clientHeight + 1
    );
  }

  /**
   * Palauta FullCalendar-asetukset mummolakalenterille.
   */
  function mummola () {
    return {
      initialView: "timeGridWeek",
      // Työkalupalkki on omana, kiinteänä osanaan rullaimen ulkopuolella.
      headerToolbar: false,
      views: {
        paiva: {
          type: "list",
          duration: { days: 1 },
          buttonText: "Päivä"
        }
      },
      // Kalenteri täyttää rullaimen yhden ruudullisen, jotta scroll-snap
      // osuu tarkalleen kalenteriin ja pehmusteisiin.
      height: "100%",
      // Leveällä näytöllä rivit venytetään täyttämään korkeus. Kapealla
      // ruudukko on harvempi ja rivit mitoitetaan itse (sovitaRuudukko),
      // jotta vuorokausi mahtuu kerralla eikä jää omaa vieritystä
      // pyyhkäisyn tielle.
      expandRows: ! kapeaNaytto(),
      slotDuration: kapeaNaytto() ? "03:00:00" : "00:30:00",
      // Kapealla näytöllä kuukausiruudut ja koko päivä -rivi rajaavat
      // merkintöjen määrän: "+2 lisää" oman vierityksen sijaan.
      dayMaxEvents: kapeaNaytto() ? 2 : false,
      businessHours: true,
      nowIndicator: true,
      // Hiirellä vetäminen valitsee aikavälin uudelle varaukselle.
      selectable: true,
      selectMirror: true,
      unselectAuto: true,
      // Kosketusnäytöllä sormella vetäminen on rullausta. Hetken
      // paikallaan pidetty sormi aloittaa sen sijaan valinnan, kuten
      // hiirellä raahaaminen työpöydällä.
      selectLongPressDelay: 500,
      slotEventOverlap: false,
      eventDisplay: "block",

      eventSources: [
        {url: "?varaukset"}
      ],

      viewClassNames: "bg-body",

      /** Vapauta työkalupalkki, kun tapahtumien lataus päättyy. */
      loading: function (ladataan) {
        if (ladataan)
          return;
        document.querySelector(".mummola-kehys")?.mummolaVapautaPalkki?.();
      },

      /** Mitoita uudelleen, kun sivun runko on tullut näkyviin. */
      viewDidMount: function (info) {
        requestAnimationFrame(function () {
          info.view.calendar.updateSize();
          sovitaRuudukko(info.view.calendar);
        });
      },
      /**
       * Päivitä osallistujamerkit ja lähtökohta, kun tapahtumat on
       * piirretty: vasta silloin koko päivä -rivin korkeus on selvillä.
       */
      eventsSet: function () {
        paivitaOsallistujamerkinnat(
          document.querySelector("#mummola")?.kalenteri
        );
        document.querySelector(".mummola-rullain")
          ?.mummolaTarkistaLahto?.(2);
      },
      /** Päivitä palkki, mitoitus ja osallistujamerkit näkymän vaihtuessa. */
      datesSet: function (info) {
        kytkePalkki(info.view.calendar);
        kytkeRullaus(info.view.calendar);
        sovitaRuudukko(info.view.calendar);
        paivitaOsallistujamerkinnat(info.view.calendar);
      },

      /** Päivänapsautus avaa uuden varauksen lomakkeen, ei päivänäkymää. */
      dateClick: function (info) {
        let loppu = new Date(info.date);
        if (info.allDay)
          loppu.setDate(loppu.getDate() + 1);
        else
          loppu.setHours(loppu.getHours() + 1);
        avaaVarauslomake(info.date, loppu);
      },

      /** Aikavälin valinta täyttää alku- ja loppukentät. */
      select: function (info) {
        avaaVarauslomake(info.start, info.end);
        info.view.calendar.unselect();
      },

      /**
       * Merkitse vähintään tunnin mittaiset varaukset: tuntiruudukossa
       * niille jää pystysuuntaa tekstille (ks. kalenteri.css).
       */
      eventClassNames: function (arg) {
        let kesto = arg.event.end - arg.event.start;
        return ! arg.event.allDay && kesto >= 3600000
          ? ["mummola-tunnin"]
          : [];
      },

      /** Piirrä tapahtuman otsikko ja päivänäkymässä lisätiedot. */
      eventContent: function (arg) {
        let varausEl = document.createElement("div");
        let nimiEl = document.createElement("span");
        nimiEl.classList.toggle("text-wrap", true);
        nimiEl.style.lineBreak = "anywhere";
        nimiEl.textContent = arg.event.title;
        varausEl.appendChild(nimiEl);

        if (arg.view.type === "paiva") {
          varausEl.insertAdjacentHTML(
            "beforeend",
            `<ul>
              <li>${escapeHTML(arg.event.extendedProps.tekija)}</li>
              <li>Tärkeys: ${escapeHTML(arg.event.extendedProps.tarkeys)}</li>
              <li>Lapsia: ${escapeHTML(arg.event.extendedProps.lapset)}</li>
              <li>Aikuisia: ${escapeHTML(arg.event.extendedProps.aikuiset)}</li>
              <li>Koiria: ${escapeHTML(arg.event.extendedProps.koirat)}</li>
              ${
                arg.event.extendedProps.kuvaus
                ? `<li>${escapeHTML(arg.event.extendedProps.kuvaus)}</li>`
                : ""
              }
            </ul>`
          );
        }
        else {
          let kellonaika = arg.event.allDay ? "" : new Date(
            arg.event.start
          ).toLocaleTimeString("fi", {
            hour: "numeric", minute: "numeric"
          });
          varausEl.title = kellonaika
            ? `${arg.event.title} klo ${kellonaika}`
            : arg.event.title;
        }

        return {domNodes: [varausEl]};
      },

      /** Tapahtuman napsautus avaa muokkauslomakkeen. */
      eventClick: function (info) {
        info.jsEvent.preventDefault();
        avaaVarauslomake(null, null, info.event);
      }
    };
  }

  /**
   * Luo ja piirrä kalenteri annettuun elementtiin (ilman solmu-js:ää).
   */
  window.Mummola = function (el, asetukset) {
    return new FullCalendar.Calendar(el, Object.assign({
      locale: document.documentElement.lang,
      themeSystem: "bootstrap5",
    }, mummola(), asetukset ?? {})).render();
  };

  if (window?.solmu?.esitys !== undefined)
    Object.assign(solmu.esitys, {
      /**
       * solmu-js-esitys `#mummola[data-solmu-esitys="mummola, kalenteri"]`.
       */
      "mummola": function (el, asetukset) {
        return Object.assign(
          {},
          mummola(),
          asetukset ?? {}
        );
      }
    });

  document.addEventListener("DOMContentLoaded", function () {
    let lomake = document.getElementById("varaus-lomake");
    if (! lomake)
      return;

    /** Luo (`?varaa`) tai päivitä (`?muokkaa`) varaus ja päivitä kalenteri. */
    lomake.addEventListener("submit", function (e) {
      e.preventDefault();
      let nappi = e.submitter || document.getElementById("varaus-tallenna");
      let vapauta = window.mummolaNappi.lukitse(nappi);
      if (! vapauta)
        return;
      naytaVirhe("");
      let pk = lomake.elements.pk.value;
      let osoite = pk
        ? "?muokkaa&pk=" + encodeURIComponent(pk)
        : "?varaa";
      fetch(osoite, {
        method: "POST",
        headers: {
          "X-CSRFToken": poimiCsrf()
        },
        body: new FormData(lomake)
      }).then(function (vastaus) {
        return vastaus.json().then(function (data) {
          if (! vastaus.ok)
            throw new Error(data.virhe || vastaus.statusText);
          return data;
        });
      }).then(function () {
        bootstrap.Modal.getOrCreateInstance(
          document.getElementById("varaus-modaali")
        ).hide();
        document.querySelector("#mummola")?.kalenteri?.refetchEvents?.();
      }).catch(function (virhe) {
        naytaVirhe(virhe.message);
      }).finally(vapauta);
    });

    /** Poista oma varaus (`?poista&pk=`). */
    document.getElementById("varaus-poista").addEventListener(
      "click",
      function () {
        let pk = lomake.elements.pk.value;
        if (! pk)
          return;
        let vapauta = window.mummolaNappi.lukitse(this);
        if (! vapauta)
          return;
        naytaVirhe("");
        fetch("?poista&pk=" + encodeURIComponent(pk), {
          method: "POST",
          headers: {
            "X-CSRFToken": poimiCsrf()
          }
        }).then(function (vastaus) {
          return vastaus.json().then(function (data) {
            if (! vastaus.ok)
              throw new Error(data.virhe || vastaus.statusText);
            return data;
          });
        }).then(function () {
          bootstrap.Modal.getOrCreateInstance(
            document.getElementById("varaus-modaali")
          ).hide();
          document.querySelector("#mummola")?.kalenteri?.refetchEvents?.();
        }).catch(function (virhe) {
          naytaVirhe(virhe.message);
        }).finally(vapauta);
      }
    );
  });
})();
