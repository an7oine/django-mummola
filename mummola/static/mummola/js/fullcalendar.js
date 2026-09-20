"use strict";

/**
 * Yleinen solmu-js-esitys FullCalendarille (`data-solmu-esitys="kalenteri"`).
 */
(function () {
  Object.assign(solmu.esitys, {
    /**
     * Näytä kalenteri annettujen asetusparametrien mukaisesti.
     */
    kalenteri: function (el, kalenteri) {
      if (! el.classList.contains("fc")) {
        el.kalenteri = new FullCalendar.Calendar(el, Object.assign({
          // Vakioarvot.
          locale: document.documentElement.lang,
          themeSystem: "bootstrap5",

          // Oletusarvoiset määritysparametrit.
          initialView: 'dayGridMonth',
          headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,dayGridWeek,list'
          },
          viewClassNames: "bg-body",

          // Avataan napsautettu päivä luettelonäkymässä.
          dateClick: function (info) {
            info.view.calendar.changeView("list", info.date);
          },

          // Tapahtuman oletusesitys.
          eventContent: function (arg) {
            let tapahtumaEl = document.createElement("div");
            tapahtumaEl.classList.toggle("text-wrap", true);

            let kuvausEl = document.createElement("span");
            kuvausEl.textContent = arg.event.title;

            tapahtumaEl.appendChild(kuvausEl);

            // Ks. https://github.com/fullcalendar/fullcalendar/issues/6133
            if (arg.view.type === "list" && arg.event.url) {
              let urlEl = document.createElement("a");
              urlEl.href = arg.event.url;
              urlEl.appendChild(tapahtumaEl);
              return {domNodes: [urlEl]};
            }

            return {domNodes: [tapahtumaEl]};
          },

          // Avataan napsautettu tapahtuma omalla välilehdellään.
          eventClick: function (info) {
            if (info.event.url) {
              info.jsEvent.preventDefault();
              window.open(info.event.url);
            }
          }
        }, kalenteri));
        el.kalenteri.render();
      }
      else
        el.kalenteri?.refetchEvents?.();
      return kalenteri;
    }
  });
})();
