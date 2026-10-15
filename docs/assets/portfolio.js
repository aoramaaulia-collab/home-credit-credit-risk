(function () {
  "use strict";

  /* Data kebijakan dari data uji (61.503 pemohon), LGD 45%. Nilai uang dalam miliar unit mata uang dataset. */
  var BASE = { approved: "100%", dr: "8,07%", el: 1.24, lm: 0, total: 1.24 };
  var POLICIES = {
    "9": {
      name: "F2 tertinggi, batas 9%",
      desc: "Batas yang memberi F2-score tertinggi. Paling banyak gagal bayar yang tertangkap, tetapi juga paling banyak nasabah baik yang ditolak (13.808 orang).",
      approved: "72,1%", dr: "3,61%", el: 0.44, lm: 1.01, total: 1.45,
      verdict: "Total biaya naik 16,8% dibanding tanpa model: margin yang hilang lebih besar daripada kerugian yang dicegah.",
      tone: "bad"
    },
    "12": {
      name: "Terpilih, batas 12%",
      desc: "F2 tertinggi yang masih lolos guardrail: total biaya tidak boleh lebih buruk daripada tanpa model.",
      approved: "79,8%", dr: "4,34%", el: 0.57, lm: 0.67, total: 1.24,
      verdict: "Impas secara total biaya (-0,2%), sementara expected loss turun 53,7%. Risiko portofolio jauh lebih rendah tanpa menambah biaya.",
      tone: "good"
    },
    "22": {
      name: "Biaya minimum, batas 22%",
      desc: "Batas dengan total biaya terendah. Hemat paling besar, tetapi hanya sekitar 32% gagal bayar yang tertangkap.",
      approved: "92,0%", dr: "5,85%", el: 0.87, lm: 0.20, total: 1.07,
      verdict: "Hemat 13,7% dibanding tanpa model, tetapi recall hanya sekitar 32%: sebagian besar gagal bayar tetap lolos. Dipakai sebagai batas zona Reject.",
      tone: "warn"
    }
  };
  var MAX = 1.45;

  function fmt(n) { return n.toFixed(2).replace(".", ",") + " M"; }
  function $(id) { return document.getElementById(id); }

  function render(key) {
    var p = POLICIES[key];
    if (!p) return;
    $("sim-name").textContent = p.name;
    $("sim-desc").textContent = p.desc;
    $("sim-approved").textContent = p.approved;
    $("sim-dr").textContent = p.dr;
    $("sim-el").textContent = fmt(p.el);
    $("sim-lm").textContent = fmt(p.lm);
    $("sim-total").textContent = fmt(p.total);
    var v = $("sim-verdict");
    v.textContent = p.verdict;
    v.className = "sim-verdict " + p.tone;
    $("simbar-el").style.width = (p.el / MAX * 100) + "%";
    $("simbar-lm").style.width = (p.lm / MAX * 100) + "%";
    $("simbar-val").textContent = fmt(p.total);
    var btns = document.querySelectorAll("[data-th]");
    for (var i = 0; i < btns.length; i++) {
      btns[i].setAttribute("aria-pressed", btns[i].getAttribute("data-th") === key ? "true" : "false");
    }
  }

  function initSim() {
    var btns = document.querySelectorAll("[data-th]");
    if (!btns.length) return;
    for (var i = 0; i < btns.length; i++) {
      btns[i].addEventListener("click", function () { render(this.getAttribute("data-th")); });
    }
    $("simbar-base-el").style.width = (BASE.el / MAX * 100) + "%";
    render("12");
  }

  function initNav() {
    var links = document.querySelectorAll(".nav-links a");
    var map = {};
    for (var i = 0; i < links.length; i++) {
      map[links[i].getAttribute("href").slice(1)] = links[i];
    }
    if (!("IntersectionObserver" in window)) return;
    var current = null;
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting && map[e.target.id]) {
          if (current) current.classList.remove("active");
          current = map[e.target.id];
          current.classList.add("active");
          if (current.parentNode.scrollWidth > current.parentNode.clientWidth) {
            var bar = current.parentNode;
            var left = current.offsetLeft - bar.clientWidth / 2 + current.clientWidth / 2;
            bar.scrollTo({ left: left, behavior: reduce ? "auto" : "smooth" });
          }
        }
      });
    }, { rootMargin: "-40% 0px -55% 0px" });
    Object.keys(map).forEach(function (id) {
      var el = document.getElementById(id);
      if (el) obs.observe(el);
    });
  }

  function initTop() {
    var b = $("to-top");
    if (!b) return;
    window.addEventListener("scroll", function () {
      if (window.scrollY > 900) b.classList.add("show"); else b.classList.remove("show");
    }, { passive: true });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initSim();
    initNav();
    initTop();
  });
})();
