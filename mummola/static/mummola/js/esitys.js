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
   * Lukitse tai avaa lomakekentät ja tallennus-/poistonapit.
   */
  function asetaKentatKaytossa (lomake, kaytossa) {
    for (let kentta of lomake.querySelectorAll(
      "input:not([type=hidden]), select, textarea"
    ))
      kentta.disabled = ! kaytossa;
    document.getElementById("varaus-tallenna").hidden = ! kaytossa;
    document.getElementById("varaus-poista").classList.toggle(
      "d-none",
      ! kaytossa
    );
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
   * Piirrä kuukausinäkymän päiväotsakkeisiin 👶 lasten yhteenlasketun määrän mukaan.
   */
  function paivitaLastenMerkinnat (kalenteri) {
    if (! kalenteri)
      return;
    let tapahtumat = kalenteri.getEvents();
    for (let solu of kalenteri.el.querySelectorAll(".fc-daygrid-day")) {
      let pvm = solu.dataset.date;
      let yla = solu.querySelector(".fc-daygrid-day-top");
      if (! pvm || ! yla)
        continue;

      let paivaAlku = new Date(pvm + "T00:00:00");
      let paivaLoppu = new Date(paivaAlku);
      paivaLoppu.setDate(paivaLoppu.getDate() + 1);

      let lapset = 0;
      for (let tapahtuma of tapahtumat) {
        let alku = tapahtuma.start;
        let loppu = tapahtuma.end ?? alku;
        if (alku < paivaLoppu && loppu > paivaAlku)
          lapset += Number(tapahtuma.extendedProps.lapset) || 0;
      }

      let merkit = yla.querySelector(".mummola-lapset");
      if (! merkit) {
        merkit = document.createElement("span");
        merkit.className = "mummola-lapset";
        yla.appendChild(merkit);
      }
      merkit.textContent = "👶".repeat(lapset);
      merkit.hidden = lapset === 0;
      merkit.title = lapset ? (lapset + " lasta") : "";
    }
  }

  /**
   * Palauta FullCalendar-asetukset mummolakalenterille.
   */
  function mummola () {
    return {
      initialView: "dayGridMonth",
      headerToolbar: {
        left: "prev,next today",
        center: "title",
        right: "paiva,timeGridWeek,dayGridMonth,listMonth"
      },
      views: {
        paiva: {
          type: "list",
          duration: { days: 1 },
          buttonText: "Päivä"
        }
      },
      businessHours: true,
      nowIndicator: true,
      selectable: true,
      selectMirror: true,
      unselectAuto: true,
      slotEventOverlap: false,
      eventDisplay: "block",

      eventSources: [
        {url: "?varaukset"}
      ],

      viewClassNames: "bg-body",

      /** Päivitä lasten merkit, kun tapahtumajoukko muuttuu. */
      eventsSet: function () {
        paivitaLastenMerkinnat(
          document.querySelector("#mummola")?.kalenteri
        );
      },
      /** Päivitä lasten merkit näkymän aikavälin vaihtuessa. */
      datesSet: function (info) {
        paivitaLastenMerkinnat(info.view.calendar);
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
      });
    });

    /** Poista oma varaus (`?poista&pk=`). */
    document.getElementById("varaus-poista").addEventListener(
      "click",
      function () {
        let pk = lomake.elements.pk.value;
        if (! pk)
          return;
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
        });
      }
    );
  });
})();
