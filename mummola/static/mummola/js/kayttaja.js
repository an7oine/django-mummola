"use strict";

/**
 * Käyttäjävalikon toiminnot: salasanan vaihto ja uuden käyttäjän luonti.
 */
(function () {
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
   * Näytä lomakevirheet annetussa hälytys-elementissä.
   */
  function naytaLomakevirheet (virheEl, virheet) {
    let rivit = [];
    if (typeof virheet === "string") {
      if (virheet)
        rivit = [virheet];
    }
    else if (virheet && typeof virheet === "object") {
      for (let kentta of Object.keys(virheet)) {
        for (let virhe of virheet[kentta]) {
          let teksti = typeof virhe === "string" ? virhe : virhe.message;
          if (teksti)
            rivit.push(teksti);
        }
      }
    }
    virheEl.replaceChildren();
    for (let teksti of rivit) {
      let rivi = document.createElement("div");
      rivi.textContent = teksti;
      virheEl.appendChild(rivi);
    }
    virheEl.classList.toggle("d-none", rivit.length === 0);
  }

  /**
   * Kytke modaalin lomake JSON-POST-osoitteeseen.
   */
  function kytkeJsonLomake (lomake, modaali, osoite, virheEl, onnistui) {
    if (! lomake || ! modaali || ! virheEl)
      return;

    modaali.addEventListener("show.bs.modal", function () {
      lomake.reset();
      naytaLomakevirheet(virheEl, "");
    });

    lomake.addEventListener("submit", function (e) {
      e.preventDefault();
      naytaLomakevirheet(virheEl, "");
      fetch(osoite, {
        method: "POST",
        headers: {
          "X-CSRFToken": poimiCsrf()
        },
        body: new FormData(lomake)
      }).then(function (vastaus) {
        return vastaus.json().then(function (data) {
          if (! vastaus.ok)
            throw data.virheet || data.virhe || vastaus.statusText;
          return data;
        });
      }).then(function (data) {
        bootstrap.Modal.getOrCreateInstance(modaali).hide();
        onnistui?.(data);
      }).catch(function (virhe) {
        naytaLomakevirheet(
          virheEl,
          virhe instanceof Error ? virhe.message : virhe
        );
      });
    });
  }

  /**
   * Lisää uusi tekijä varauslomakkeen pudotusvalikkoon.
   */
  function lisaaTekijaValikkoon (data) {
    let valinta = document.getElementById("id_tekija");
    if (! valinta || ! data?.pk)
      return;
    if (valinta.querySelector(`option[value="${data.pk}"]`))
      return;
    let vaihtoehto = document.createElement("option");
    vaihtoehto.value = data.pk;
    vaihtoehto.textContent = data.nimi ?? data.pk;
    valinta.appendChild(vaihtoehto);
  }

  document.addEventListener("DOMContentLoaded", function () {
    let salasanaModaali = document.getElementById("salasana-modaali");
    kytkeJsonLomake(
      document.getElementById("salasana-lomake"),
      salasanaModaali,
      "?vaihda_salasana",
      document.getElementById("salasana-virhe")
    );
    kytkeJsonLomake(
      document.getElementById("kayttaja-lomake"),
      document.getElementById("kayttaja-modaali"),
      "?lisaa_kayttaja",
      document.getElementById("kayttaja-virhe"),
      lisaaTekijaValikkoon
    );

    /** Ensimmäinen kirjautuminen: ei CHANGE-merkintää käyttäjän muutoslokissa. */
    if (salasanaModaali?.hasAttribute("data-avaa-salasana"))
      bootstrap.Modal.getOrCreateInstance(salasanaModaali).show();
  });
})();
